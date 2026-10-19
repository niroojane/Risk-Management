"""Real multi-asset portfolio from Excel files on GitHub, priced with Yahoo Finance.

Port of the Multi Asset App notebook's portfolio side: Current Portfolio,
Trade History, Positions and Quantities files (ETF folder), holdings valued in
the base currency, average-cost P&L from the trades (fees and trading
currencies included), P&L history and 'Update Files'.
"""
import asyncio
import datetime
import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from .base import AccountHistory, PortfolioAccount
from .github_storage import GitHubStorage
from src import Account as crypto_account
from src import MultiAsset as ma
from ..cache import CacheService
from ..yahoo import YahooMarketData
from src import PositionHandler as position_handler
from src import Yahoo_API as yahoo_api
from ...core.exceptions import DataValidationError, ExternalAPIError
from ...core.market import CurrencySettings, MarketProfile

logger = logging.getLogger(__name__)

FILES_TTL = 600
FILES_KEY = 'excel:files'
RECENT_DAYS = 20


def _clean_dated(frame: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Dated sheet: datetime index, numeric values, sorted, one row per date (notebook's load_excel)"""
    if frame is None or frame.empty:
        return pd.DataFrame()
    df = frame.copy()
    df.index = pd.to_datetime(df.index, errors='coerce')
    df = df[df.index.notna()]
    df = df.apply(pd.to_numeric, errors='coerce').sort_index()
    return df[~df.index.duplicated(keep='last')]


class ExcelAccountService(PortfolioAccount):
    """Portfolio files from the profile's GitHub folder, prices and FX from Yahoo"""

    def __init__(self, storage: GitHubStorage, market: YahooMarketData, currency: CurrencySettings,
                 profile: MarketProfile, cache: Optional[CacheService] = None):
        self._storage = storage
        self._market = market
        self._currency = currency
        self._profile = profile
        self._cache = cache

    @property
    def _base(self) -> str:
        return self._currency.base_currency

    # ------------------------------------------------------------------ files

    def _read(self, name: str, index_col=None) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        try:
            return self._storage.read_excel(name, index_col=index_col), None
        except ExternalAPIError as exc:
            return None, f"{name}.xlsx could not be loaded ({exc.detail or exc.message})"

    def _load_files(self) -> Dict[str, Any]:
        p = self._profile
        positions, w1 = self._read(p.positions_file, 0)
        quantities, w2 = self._read(p.quantities_file, 0)
        current, w3 = self._read(p.current_portfolio_file)
        trades_raw, w4 = self._read(p.trades_file)
        warnings = [w for w in (w1, w2, w3, w4) if w]

        positions = _clean_dated(positions)
        if not positions.empty:
            positions = positions.drop(columns=ma.TOTAL, errors='ignore')
            positions[ma.TOTAL] = positions.sum(axis=1)

        units = pd.Series(dtype=float)
        if current is not None:
            try:
                units = ma.current_portfolio_units(current)
            except ValueError as exc:
                warnings.append(str(exc))

        trades = pd.DataFrame()
        if trades_raw is not None:
            trades, trade_warnings = ma.parse_trades(trades_raw)
            warnings += trade_warnings

        return {
            'positions_raw': positions,
            'quantities': _clean_dated(quantities),
            'units': units,
            'trades': trades,
            'ledger': ma.build_ledger(trades),
            'warnings': warnings,
        }

    async def _files(self, use_cache: bool = True) -> Dict[str, Any]:
        if use_cache and self._cache:
            cached = await self._cache.get(FILES_KEY)
            if cached is not None:
                return cached
        files = await asyncio.to_thread(self._load_files)
        if self._cache:
            await self._cache.set(FILES_KEY, files, ttl=FILES_TTL)
        return files

    async def _quote_ccy(self, tickers: Iterable[str], trades: pd.DataFrame, use_cache: bool = True) -> pd.Series:
        tickers = list(tickers)
        yahoo = await self._market.currencies([t for t in tickers if t not in ma.CASH_COLUMNS], use_cache)
        return ma.quote_currencies(tickers, yahoo, trades, base=self._base)

    async def _to_base(self, local: pd.DataFrame, trades: pd.DataFrame, start, use_cache: bool = True):
        """Quote-currency prices -> base currency (no-op when conversion is off)"""
        if local.empty or not self._currency.convert_to_base:
            return local, []
        quote = await self._quote_ccy(local.columns, trades, use_cache)
        fx, warnings = await self._market.fx_or_one(quote.values, self._base, start, use_cache)
        return yahoo_api.to_base_currency(local, quote, fx), warnings

    # ------------------------------------------------------------------ holdings

    async def _positions_base(self, positions_raw: pd.DataFrame, use_cache: bool = True) -> pd.DataFrame:
        """Positions values converted from the positions currency to the base currency"""
        ccy = self._currency.positions_currency
        if positions_raw.empty or ccy == self._base:
            return positions_raw.copy()
        fx, _ = await self._market.fx_or_one([ccy], self._base, positions_raw.index[0], use_cache)
        rate = ma.ffill_align(fx[[ccy]], positions_raw.index)[ccy].bfill().fillna(1.0)
        return ma.positions_to_base(positions_raw, rate)

    async def _latest_prices(self, assets: List[str], rates: pd.Series, files: Dict[str, Any],
                             use_cache: bool = True) -> pd.Series:
        """Last price per asset in its quote currency: Yahoo, else implied by the history files"""
        out = pd.Series(np.nan, index=assets, dtype=float)
        if assets:
            recent = await self._market.close(assets, datetime.date.today() - datetime.timedelta(days=RECENT_DAYS),
                                              None, use_cache)
            if not recent.empty:
                out = out.fillna(recent.ffill().iloc[-1].reindex(assets))
        missing = list(out[out.isna()].index)
        if missing:
            positions = await self._positions_base(files['positions_raw'], use_cache)
            implied = ma.implied_prices(positions, files['quantities'])
            if not implied.empty:
                out = out.fillna(implied.iloc[-1].reindex(assets) / rates.reindex(assets))
        return out

    async def _holdings_context(self, use_cache: bool = True) -> Dict[str, Any]:
        files = await self._files(use_cache)
        units = files['units']
        if units.empty:
            raise DataValidationError("Current portfolio not loaded",
                                      detail=f"Check {self._profile.current_portfolio_file}.xlsx in the "
                                             f"{self._profile.data_folder} folder")
        trades = files['trades']
        quote = await self._quote_ccy(units.index, trades, use_cache)
        trade_ccy = ma.ticker_currencies(trades, units.index, quote=quote, base=self._base)
        fx, warnings = await self._market.fx_or_one(
            set(quote.values) | set(trade_ccy.values), self._base,
            datetime.date.today() - datetime.timedelta(days=RECENT_DAYS), use_cache)
        rates = ma.spot_rates(fx, quote)
        assets = [a for a in units.index if a not in ma.CASH_COLUMNS]
        prices = await self._latest_prices(assets, rates, files, use_cache)
        holdings = ma.holdings_table(units, quote, prices, rates)
        return {
            'files': files, 'holdings': holdings, 'trade_ccy': trade_ccy,
            'cost_rates': ma.spot_rates(fx, trade_ccy), 'warnings': files['warnings'] + warnings,
        }

    async def holdings_view(self, use_cache: bool = True) -> Dict[str, Any]:
        ctx = await self._holdings_context(use_cache)
        holdings = ctx['holdings']
        tickers = [t for t in holdings.index if t not in ma.CASH_COLUMNS]
        return {
            'holdings': holdings,
            'tickers': tickers,
            'weights': {t: float(holdings.loc[t, 'Weights']) for t in tickers},
            'base_currency': self._base,
            'warnings': ctx['warnings'],
        }

    async def positioning(self, model_weights: pd.Series, use_cache: bool = True) -> Dict[str, Any]:
        ctx = await self._holdings_context(use_cache)
        current = ctx['holdings'][['Market Value', 'Weights']].rename(
            columns={'Market Value': 'Current Portfolio', 'Weights': 'Current Weights'})
        current.loc[ma.TOTAL] = current.sum()
        table = await asyncio.to_thread(crypto_account.positioning_table, current, model_weights,
                                        'Current Portfolio')
        return {'positioning': table, 'holdings': ctx['holdings'], 'warnings': ctx['warnings']}

    async def pnl(self, use_cache: bool = True) -> Dict[str, Any]:
        ctx = await self._holdings_context(use_cache)
        files, holdings = ctx['files'], ctx['holdings']
        trades, ledger = files['trades'], files['ledger']
        warnings = list(ctx['warnings'])
        if trades.empty:
            warnings.append("Trade history not loaded -- P&L not computed.")
            return {'pnl': holdings, 'trades': pd.DataFrame(), 'warnings': warnings}

        realized = ledger['realized_pnl']
        closed = realized.index.difference(holdings.index) if not realized.empty else pd.Index([])
        closed_ccy = closed_rates = None
        if len(closed):
            closed_ccy = ma.ticker_currencies(trades, closed, base=self._base)
            fx, _ = await self._market.fx_or_one(
                closed_ccy.values, self._base, datetime.date.today() - datetime.timedelta(days=RECENT_DAYS), use_cache)
            closed_rates = ma.spot_rates(fx, closed_ccy)

        table = await asyncio.to_thread(ma.pnl_table, holdings, ctx['trade_ccy'], ctx['cost_rates'], ledger,
                                        closed_ccy, closed_rates)
        gap = ma.unexplained_units(files['units'], ledger)
        if not gap.empty:
            warnings.append("Units in the Current Portfolio that the trade history doesn't explain "
                            "(transfers? missing trades?): "
                            + ', '.join(f"{t} {v:+.6g}" for t, v in gap.items()))
        return {
            'pnl': table,
            'trades': trades.sort_values('Date', ascending=False).set_index('Date'),
            'warnings': warnings,
        }

    # ------------------------------------------------------------------ history

    async def get_history(self, use_cache: bool = True) -> AccountHistory:
        files = await self._files(use_cache)
        if files['positions_raw'].empty:
            raise DataValidationError("Positions file could not be loaded",
                                      detail='; '.join(files['warnings']) or None)
        positions = await self._positions_base(files['positions_raw'], use_cache)
        return AccountHistory(positions=positions, quantities=files['quantities'])

    async def get_history_prices(self, history: AccountHistory, use_cache: bool = True) -> pd.DataFrame:
        """Base-currency prices of every held asset since the first saved day; assets
        Yahoo can't price fall back to the prices implied by the history files"""
        files = await self._files(use_cache)
        held = ma.drop_cash(history.positions.columns)
        start = history.positions.index[0]
        local = await self._market.close(held, start, None, use_cache)
        prices, _ = await self._to_base(local, files['trades'], start, use_cache)

        implied = ma.implied_prices(history.positions, history.quantities)
        gaps = [c for c in held if c not in prices.columns and c in implied.columns]
        if gaps:
            days = prices.index if not prices.empty else pd.bdate_range(implied.index[0], implied.index[-1])
            fill = ma.ffill_align(implied[gaps], days)
            prices = pd.concat([prices, fill], axis=1) if not prices.empty else fill
        return prices

    async def pnl_history(self, history: AccountHistory, prices: pd.DataFrame,
                          use_cache: bool = True) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """P&L from the trades only: units, cost, realized and fees come from the ledger"""
        files = await self._files(use_cache)
        trades, ledger = files['trades'], files['ledger']
        if trades.empty or ledger['units_daily'].empty:
            return pd.DataFrame(), pd.Series(dtype=float), ["P&L not computed: no trades loaded (trade history)"]

        units_daily = ledger['units_daily']
        last_day = max(prices.index.max() if not prices.empty else units_daily.index.max(), units_daily.index.max())
        calendar = pd.date_range(units_daily.index.min(), last_day, freq='D')
        trade_units = ma.asof_frame(units_daily, calendar, list(units_daily.columns), fill=0.0)
        quote = await self._quote_ccy(trade_units.columns, trades, use_cache)
        trade_ccy = ma.ticker_currencies(trades, trade_units.columns, quote=quote, base=self._base)
        fx, warnings = await self._market.fx_or_one(set(trade_ccy.values) | set(quote.values), self._base,
                                                    calendar[0], use_cache)

        prices_base = prices
        missing = [t for t in trade_units.columns if t not in prices.columns and t not in ma.CASH_COLUMNS]
        if missing:
            extra = await self._market.close(missing, calendar[0], None, use_cache)
            if not extra.empty:
                extra_base, _ = await self._to_base(extra, trades, calendar[0], use_cache)
                prices_base = pd.concat([prices, extra_base], axis=1)

        pnl = await asyncio.to_thread(
            ma.pnl_history_from_ledger, trade_units, prices_base, ledger['book_cost_daily'],
            ledger['realized_daily'], fx, trade_ccy, ledger['fees_daily'], self._base)
        daily = pnl[ma.TOTAL].diff()
        warnings += ma.pnl_coverage_report(trade_units, prices_base, ledger)
        return pnl, daily, warnings

    # ------------------------------------------------------------------ update files

    async def upload(self) -> Dict[str, Any]:
        """'Update Files': today's holdings (and missed days) into the Quantities /
        Positions files, pushed to the GitHub folder"""
        files = await asyncio.to_thread(self._load_files)   # never update from a stale cache
        units_today = files['units']
        if units_today.empty:
            raise DataValidationError(f"Nothing read from {self._profile.current_portfolio_file}.xlsx")
        q_hist, p_hist = files['quantities'], files['positions_raw']
        if q_hist.empty or p_hist.empty:
            # don't overwrite a history that couldn't be downloaded
            raise DataValidationError("Couldn't read the Quantities / Positions files",
                                      detail='; '.join(files['warnings']) or None)

        positions_ccy = self._currency.positions_currency
        q_new, p_new, summary, info = await asyncio.to_thread(
            # the saved Positions keep their 'Total' column, as the notebook passes the file as it is
            position_handler.update_files, units_today, q_hist, p_hist, None, positions_ccy, files['trades'])

        results = {}
        for frame, name in ((q_new, self._profile.quantities_file), (p_new, self._profile.positions_file)):
            results[name] = await asyncio.to_thread(self._storage.write_excel, frame, name)
        if self._cache:
            await self._cache.delete(FILES_KEY)
        return {'files': results, 'messages': position_handler.describe(summary, info, positions_ccy)}
