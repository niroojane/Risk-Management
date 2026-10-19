"""Real Binance portfolio: holdings, trade history, position history"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .base import AccountHistory, PortfolioAccount
from .github_storage import POSITIONS_FILE, QUANTITIES_FILE, TRADES_FILE, GitHubStorage
from src import Account as account_analytics
from src import Binance_API as binance_api
from ..binance import BinanceClient, PriceService, QuantityService
from ..cache import CacheService
from ...core.config import CACHE_INVENTORY_TTL
from ...core.exceptions import DataValidationError

logger = logging.getLogger(__name__)

HISTORY_TTL = 600
SNAPSHOT_DAYS = 30
STABLECOINS = ('USDTUSDT', 'USDCUSDT')


class AccountService(PortfolioAccount):
    """Reads the account through Binance and the saved history through GitHub"""

    def __init__(self, client: BinanceClient, price_service: PriceService, quantity_service: QuantityService,
                 storage: GitHubStorage, cache: Optional[CacheService] = None):
        self._client = client
        self._prices = price_service
        self._quantities = quantity_service
        self._storage = storage
        self._cache = cache

    async def _cached(self, key: str, ttl: int, use_cache: bool, factory):
        if use_cache and self._cache:
            cached = await self._cache.get(key)
            if cached is not None:
                return cached
        value = await factory()
        if self._cache:
            await self._cache.set(key, value, ttl=ttl)
        return value

    # ------------------------------------------------------------------ holdings

    async def get_balances(self, use_cache: bool = True) -> pd.DataFrame:
        """Free / locked units per ticker ('<asset>USDT')"""
        async def fetch():
            assets = await self._client._run_in_executor(self._client.spot.user_asset)
            balances = pd.DataFrame(assets)
            if balances.empty:
                return pd.DataFrame(columns=['free', 'locked'])
            balances.index = balances['asset'] + 'USDT'
            return balances[['free', 'locked']].astype(float)

        return await self._cached('account:balances', CACHE_INVENTORY_TTL, use_cache, fetch)

    async def get_last_prices(self, tickers: List[str], use_cache: bool = True) -> pd.Series:
        """Latest price in USDT of each ticker (USDT itself = 1)"""
        async def fetch():
            all_prices = await self._client._run_in_executor(self._client.spot.ticker_price)
            return pd.Series({p['symbol']: float(p['price']) for p in all_prices})

        prices = await self._cached('account:last_prices', CACHE_INVENTORY_TTL, use_cache, fetch)
        prices = prices.reindex(tickers)
        if 'USDTUSDT' in prices.index:
            prices['USDTUSDT'] = 1.0
        return prices

    async def get_holdings(self, use_cache: bool = True):
        """(holdings table with 'Total', balances)"""
        balances = await self.get_balances(use_cache)
        prices = await self.get_last_prices(list(balances.index), use_cache)
        return account_analytics.holdings_table(balances, prices), balances

    async def holdings_view(self, use_cache: bool = True) -> Dict[str, Any]:
        holdings, _ = await self.get_holdings(use_cache)
        tickers = [t for t in holdings.index if t != account_analytics.TOTAL]
        weights = holdings[account_analytics.WEIGHT]
        return {
            'holdings': holdings,
            'tickers': tickers,
            'weights': {t: float(weights[t]) for t in tickers if t not in STABLECOINS},
        }

    async def positioning(self, model_weights: pd.Series, use_cache: bool = True) -> Dict[str, Any]:
        holdings, _ = await self.get_holdings(use_cache)
        table = await asyncio.to_thread(account_analytics.positioning_table, holdings, model_weights)
        return {'positioning': table, 'holdings': holdings}

    async def pnl(self, use_cache: bool = True) -> Dict[str, Any]:
        (holdings, balances), (book_cost, realized, trades) = await asyncio.gather(
            self.get_holdings(use_cache), self.get_book_cost(use_cache)
        )
        table = await asyncio.to_thread(account_analytics.pnl_table, book_cost, realized, holdings, balances['free'])
        return {'pnl': table, 'trades': trades.set_index('Date(UTC)').sort_index(ascending=False), 'warnings': []}

    async def pnl_history(self, history: AccountHistory, prices: pd.DataFrame,
                          use_cache: bool = True) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        book_cost, _, _ = await self.get_book_cost(use_cache)
        pnl_history, daily = await asyncio.to_thread(
            account_analytics.pnl_history, history.quantities, book_cost, prices
        )
        return pnl_history, daily, []

    # ------------------------------------------------------------------ trades / P&L

    async def _pair_price(self, market: str, time: pd.Timestamp) -> float:
        """USDT price of the quote asset of `market` at `time`, interpolated on 1-minute klines"""
        return await self._client._run_in_executor(binance_api.pair_price, self._client.spot, market, time)

    async def get_trades(self, use_cache: bool = True) -> pd.DataFrame:
        """Trade history with prices and totals converted to USDT"""
        async def fetch():
            trades = await asyncio.to_thread(self._storage.read_excel, TRADES_FILE)
            trades['Date(UTC)'] = pd.to_datetime(trades['Date(UTC)'])
            if 'Pair Price' not in trades.columns:
                trades['Pair Price'] = float('nan')
            if 'Pair Quantity' not in trades.columns:
                trades['Pair Quantity'] = float('nan')

            missing = trades.index[trades['Pair Quantity'].isna()]
            if len(missing):
                logger.info(f"Converting {len(missing)} trades to USDT with 1-minute klines")
                prices = await asyncio.gather(*[
                    self._pair_price(trades.at[i, 'Market'], trades.at[i, 'Date(UTC)']) for i in missing
                ])
                trades.loc[missing, 'Pair Price'] = prices
            return account_analytics.trades_in_usdt(trades)

        return await self._cached('account:trades', HISTORY_TTL, use_cache, fetch)

    async def get_book_cost(self, use_cache: bool = True):
        """(average book cost history, realized P&L per asset, trades)"""
        trades = await self.get_trades(use_cache)
        book_cost, realized = await asyncio.to_thread(account_analytics.book_cost_and_pnl, trades)
        return book_cost, realized, trades

    # ------------------------------------------------------------------ history

    async def get_history(self, use_cache: bool = True) -> AccountHistory:
        """Saved Positions / Quantities files + the last 30 days of account snapshots"""
        async def fetch():
            saved_positions, saved_quantities = await asyncio.gather(
                asyncio.to_thread(self._storage.read_excel, POSITIONS_FILE, 0),
                asyncio.to_thread(self._storage.read_excel, QUANTITIES_FILE, 0),
            )

            recent_positions = recent_quantities = None
            try:
                snapshots = await self._quantities.get_historical_quantities(
                    end_date=datetime.today(), limit=SNAPSHOT_DAYS, use_cache=use_cache
                )
                tickers = sorted({b['asset'] + 'USDT' for s in snapshots['data'] for b in s['balances']})
                prices = await self._prices.get_price_frame(
                    tickers, datetime.today() - timedelta(days=SNAPSHOT_DAYS + 1), datetime.today(), use_cache
                )
                recent_positions, recent_quantities = account_analytics.snapshot_positions(snapshots['data'], prices)
            except Exception as exc:  # the saved history is still usable without the latest snapshots
                logger.warning(f"Account snapshots unavailable: {exc}")

            positions = account_analytics.merge_history(saved_positions, recent_positions, with_total=True)
            quantities = account_analytics.merge_history(saved_quantities, recent_quantities, prefer_recent=False)
            if positions.empty:
                raise DataValidationError("No position history available")
            return AccountHistory(positions=positions, quantities=quantities.fillna(0.0))

        return await self._cached('account:history', HISTORY_TTL, use_cache, fetch)

    async def get_history_prices(self, history: AccountHistory, use_cache: bool = True) -> pd.DataFrame:
        """Daily closes of every asset ever held, from the first saved day"""
        tickers = sorted(set(history.quantities.columns) | set(history.positions.columns) - {'Total'})
        start = history.positions.index[0].to_pydatetime()
        return await self._prices.get_price_frame(tickers, start, datetime.today(), use_cache)

    # ------------------------------------------------------------------ upload

    async def upload(self) -> Dict[str, str]:
        """Push the merged Positions / Quantities and the converted trade history to GitHub"""
        history = await self.get_history(use_cache=True)
        trades = await self.get_trades(use_cache=True)
        files = {
            POSITIONS_FILE: history.positions,
            QUANTITIES_FILE: history.quantities,
            TRADES_FILE: trades.set_index('Date(UTC)'),
        }
        results = {}
        for name, frame in files.items():
            results[name] = await asyncio.to_thread(self._storage.write_excel, frame, name)
        return {'files': results, 'messages': []}
