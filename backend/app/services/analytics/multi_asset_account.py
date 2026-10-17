"""Real multi-asset portfolio from Excel files: trades, ledger, holdings and P&L.

Port of the Multi Asset App notebook's helpers (read_current_portfolio,
read_trade_history, get_book_cost / get_pnl / build_ledger,
pnl_history_from_ledger, and the P&L table of get_holdings). Pure functions on
DataFrames: reading the files and fetching prices / FX live in
`app.services.account.excel_account`.

Money columns of trades, book cost, realized P&L and fees are in each asset's
trading currency; they are translated to the base currency with the day's FX.
"""
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from ...core.market import FIAT_CURRENCIES

# Asset code (the 'asset' column / the Market without its currency) -> Yahoo ticker.
# Anything not listed maps to itself (XLK -> XLK), e.g. {'GOLD': 'GOLD.PA'}.
TICKER_MAP: Dict[str, str] = {}
# Trading currency of tickers held but never traded (otherwise from the trades).
CURRENCY_MAP: Dict[str, str] = {}
# Capitalise buy commissions into the cost price instead of reporting them as fees
INCLUDE_FEES_IN_BOOK_COST = False
CASH_COLUMNS = frozenset(FIAT_CURRENCIES) | {'Cash'}
MINOR_TO_MAJOR = {'GBp': 'GBP', 'GBX': 'GBP', 'ZAc': 'ZAR', 'ILA': 'ILS'}
TOTAL = 'Total'


def asset_to_ticker(asset) -> str:
    asset = str(asset).strip()
    return TICKER_MAP.get(asset, asset)


def market_to_asset(market) -> Tuple[str, str]:
    """'XLKUSD' -> ('XLK', 'USD'); 'GOLD.PAEUR' -> ('GOLD.PA', 'EUR'); unknown suffix -> (market, '')"""
    market = str(market).strip()
    for ccy in FIAT_CURRENCIES:
        if market.endswith(ccy) and len(market) > len(ccy):
            return market[:-len(ccy)], ccy
    return market, ''


_AMOUNT_RE = re.compile(r'^\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(.*?)\s*$')


def split_amount(value) -> Tuple[float, str]:
    """'12.5000XLK' -> (12.5, 'XLK'); plain numbers -> (x, '')"""
    if isinstance(value, (int, float, np.number)) and not pd.isna(value):
        return float(value), ''
    m = _AMOUNT_RE.match(str(value).replace(',', ''))
    if not m:
        return np.nan, ''
    return float(m.group(1)), m.group(2)


def current_portfolio_units(frame: pd.DataFrame) -> pd.Series:
    """Current Portfolio sheet (Binance user_asset layout) -> units per ticker (free + locked).

    Cash lines keep their currency code; other assets are mapped through TICKER_MAP.
    """
    df = frame.copy()
    df.columns = [str(c).strip() for c in df.columns]
    if 'asset' not in df.columns:
        raise ValueError("Current portfolio file: no 'asset' column")
    units = sum(pd.to_numeric(df[c], errors='coerce').fillna(0) for c in ('free', 'locked') if c in df.columns)
    assets = df['asset'].astype(str).str.strip()
    tickers = [a if a in CASH_COLUMNS else asset_to_ticker(a) for a in assets]
    out = pd.Series(np.asarray(units, dtype=float), index=tickers).groupby(level=0).sum()
    return out[out.abs() > 1e-12]


def parse_trades(raw: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Trade history sheet -> (tidy trades oldest first, warnings).

    Columns Date(UTC), Market, Type, Price, Amount, Total, Fee, Fee Coin (or the
    newer layout Pair, Side, Executed "12.5XLK", Amount "3.1USD", Fee "0.01USD").
    Output: Date, Market, Asset, Ticker, Currency, Side, Price, Quantity,
    Notional, Fee -- money in the trade's own Currency.
      * A fee in the trading currency (or without Fee Coin) is a cash fee; a fee
        in units of the asset reduces the units bought / is valued at the trade
        price on a sale; a fee in another currency needs 'Fee FX', otherwise 0.
    """
    raw = raw.copy()
    raw.columns = [str(c).strip() for c in raw.columns]
    legacy = 'Market' in raw.columns
    rows, unvalued_fees, skipped = [], 0, set()

    for r in raw.to_dict('records'):
        market = str(r.get('Market') if legacy else r.get('Pair', '')).strip()
        asset, ccy = market_to_asset(market)
        if not ccy:
            skipped.add(market)
            continue
        side = str(r.get('Type') if legacy else r.get('Side', '')).strip().upper()
        price = float(pd.to_numeric(r.get('Price'), errors='coerce'))

        if legacy:
            qty = float(pd.to_numeric(r.get('Amount'), errors='coerce'))
            notional = float(pd.to_numeric(r.get('Total'), errors='coerce'))
            fee = float(pd.to_numeric(r.get('Fee', 0), errors='coerce'))
            fee_coin = str(r.get('Fee Coin', '') or '').strip()
        else:
            qty, unit = split_amount(r.get('Executed'))
            notional, _ = split_amount(r.get('Amount'))
            fee, fee_coin = split_amount(r.get('Fee', 0))
            asset = unit or asset
        if pd.isna(notional):
            notional = qty * price
        fee = 0.0 if pd.isna(fee) else fee
        if fee_coin.lower() == 'nan':
            fee_coin = ''

        fee_cash = 0.0
        if fee_coin in ('', ccy):
            fee_cash = fee
        elif fee_coin == asset:
            if side == 'BUY':
                qty -= fee                          # fee taken out of the units bought
            else:
                fee_cash = fee * price
        elif fee:
            rate = pd.to_numeric(r.get('Fee FX'), errors='coerce')
            if pd.isna(rate):
                unvalued_fees += 1
            else:
                fee_cash = fee * float(rate)

        rows.append({'Date': pd.to_datetime(r.get('Date(UTC)'), errors='coerce'),
                     'Market': market, 'Asset': asset, 'Ticker': asset_to_ticker(asset),
                     'Currency': ccy, 'Side': side, 'Price': price, 'Quantity': qty,
                     'Notional': notional, 'Fee': fee_cash})

    warnings = []
    if skipped:
        warnings.append(f"Skipped markets without a known currency suffix: {', '.join(sorted(skipped))}")
    if unvalued_fees:
        warnings.append(f"{unvalued_fees} fee(s) paid in another currency without 'Fee FX' were counted as 0.")
    trades = pd.DataFrame(rows)
    if trades.empty:
        return trades, warnings
    trades = trades.dropna(subset=['Date', 'Quantity', 'Price'])
    return trades.sort_values('Date', kind='stable').reset_index(drop=True), warnings


def ticker_currencies(trades: Optional[pd.DataFrame], tickers: Iterable[str],
                      quote: Optional[pd.Series] = None, base: str = 'USD') -> pd.Series:
    """Trade (cost) currency per ticker: CURRENCY_MAP, then the trades, then the
    quote currency (minor units -> major), then the base currency."""
    from_trades = {} if trades is None or trades.empty else trades.groupby('Ticker')['Currency'].last().to_dict()
    quote = quote if quote is not None else pd.Series(dtype=object)
    out = {}
    for t in tickers:
        if t in CASH_COLUMNS:
            out[t] = t
            continue
        q = quote.get(t)
        q = MINOR_TO_MAJOR.get(q, q)
        out[t] = CURRENCY_MAP.get(t) or from_trades.get(t) or q or base
    return pd.Series(out, dtype=object)


def quote_currencies(tickers: Iterable[str], yahoo: pd.Series, trades: Optional[pd.DataFrame],
                     base: str = 'USD') -> pd.Series:
    """Currency each ticker is quoted in (Yahoo, may be a minor unit such as 'GBp'),
    else its trade currency, else the base currency. Cash lines are their own currency."""
    tickers = list(tickers)
    trade_ccy = ticker_currencies(trades, tickers, base=base)
    return pd.Series({t: t if t in CASH_COLUMNS else (yahoo.get(t) or trade_ccy.get(t) or base)
                      for t in tickers}, dtype=object)


def get_book_cost(trades: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Weighted-average book cost per ticker (trading currency).

        new_cost_price = (old_cost_price * old_balance + purchase_cost) / new_balance

    Trades with the same timestamp are netted. A net acquisition re-weights the
    cost price; a disposal lowers the balance (closing resets the cost to 0) and
    realizes its net proceeds minus the cost before the event.

    Returns (book_cost by trade timestamp, events per ticker and timestamp).
    """
    if trades.empty:
        return pd.DataFrame(), pd.DataFrame()
    t = trades.copy()
    sign = np.where(t['Side'] == 'SELL', -1.0, 1.0)
    t['Amount'] = sign * t['Quantity']
    capitalised = (t['Side'] == 'BUY') & INCLUDE_FEES_IN_BOOK_COST
    t['Total'] = sign * t['Notional'] + np.where(capitalised, t['Fee'], 0.0)
    t['Fee Charged'] = np.where(capitalised, 0.0, t['Fee'])

    grouped = t.groupby(['Ticker', 'Date'])[['Amount', 'Total', 'Fee Charged']].sum().sort_index()

    series, rows = {}, []
    for ticker, ev in grouped.groupby(level=0):
        balance, cost_price, cost_by_date = 0.0, 0.0, {}
        for (_, date), r in ev.iterrows():
            cost_before = cost_price
            if r['Amount'] > 0:
                new_balance = balance + r['Amount']
                if new_balance != 0:
                    cost_price = (cost_price * balance + r['Total']) / new_balance
                balance = new_balance
            else:
                balance += r['Amount']
                if balance <= 1e-12:
                    balance, cost_price = 0.0, 0.0
            realized = 0.0 if r['Amount'] > 0 else (-r['Total']) + r['Amount'] * cost_before
            cost_by_date[date] = cost_price
            rows.append({'Date': date, 'Ticker': ticker, 'Cost Before': cost_before,
                         'Cost Price': cost_price, 'Balance': balance,
                         'Realized P&L': realized, 'Fees': r['Fee Charged']})
        series[ticker] = pd.Series(cost_by_date)

    book_cost = pd.DataFrame(series).sort_index().ffill().fillna(0)
    return book_cost, pd.DataFrame(rows)


def get_pnl(events: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """(realized P&L per ticker, per-event detail)"""
    if events.empty:
        return pd.DataFrame(columns=['Realized PnL']), pd.DataFrame()
    detail = events.pivot_table(index='Date', columns='Ticker', values='Realized P&L', aggfunc='sum').fillna(0)
    return detail.sum().to_frame('Realized PnL'), detail


def build_ledger(trades: pd.DataFrame) -> dict:
    """End-of-day frames from the trades: units, cost price, cumulative realized
    P&L and fees per ticker, realized P&L table and net units."""
    book_cost, events = get_book_cost(trades)
    if events.empty:
        empty = pd.DataFrame()
        return dict(book_cost=empty, book_cost_daily=empty, realized_daily=empty, fees_daily=empty,
                    realized_pnl=pd.DataFrame(columns=['Realized PnL']), net_quantities=pd.Series(dtype=float),
                    units_daily=empty)
    ev = events.assign(Day=events['Date'].dt.normalize())
    cost_daily = ev.pivot_table(index='Day', columns='Ticker', values='Cost Price', aggfunc='last').ffill().fillna(0)
    realized_daily = ev.pivot_table(index='Day', columns='Ticker', values='Realized P&L', aggfunc='sum') \
        .fillna(0).cumsum()
    fees_daily = ev.pivot_table(index='Day', columns='Ticker', values='Fees', aggfunc='sum').fillna(0).cumsum()
    realized_pnl, _ = get_pnl(events)
    net_q = ev.sort_values('Date').groupby('Ticker')['Balance'].last()
    units_daily = ev.pivot_table(index='Day', columns='Ticker', values='Balance', aggfunc='last').ffill().fillna(0)
    return dict(book_cost=book_cost, book_cost_daily=cost_daily, realized_daily=realized_daily,
                fees_daily=fees_daily, realized_pnl=realized_pnl, net_quantities=net_q,
                units_daily=units_daily)


def ffill_align(frame: pd.DataFrame, index) -> pd.DataFrame:
    """Rows of `frame` as of each date in `index` (last known value carried forward)"""
    f = frame.sort_index()
    f = f[~f.index.duplicated(keep='last')]
    return f.reindex(f.index.union(index)).ffill().reindex(index)


def asof_frame(frame: Optional[pd.DataFrame], index, columns, fill=np.nan) -> pd.DataFrame:
    """Value of `frame` as of each date in `index` (last known row, ffilled)"""
    if frame is None or frame.empty:
        return pd.DataFrame(fill, index=index, columns=columns)
    f = frame.reindex(columns=columns)
    f = f.reindex(f.index.union(index)).sort_index().ffill().reindex(index)
    return f.fillna(fill) if not pd.isna(fill) else f


def pnl_coverage_report(quantities: pd.DataFrame, prices: pd.DataFrame, ledger: dict) -> List[str]:
    """Explain P&L lines that can't be computed (they would otherwise show as 0)"""
    held = [c for c in quantities.columns
            if c not in CASH_COLUMNS and (quantities[c].abs() > 1e-12).any()]
    traded = set(ledger['book_cost_daily'].columns) if not ledger['book_cost_daily'].empty else set()
    msgs = []
    no_price = [t for t in held if t not in prices.columns or prices[t].isna().all()]
    no_trades = [t for t in held if t not in traded]
    not_held = sorted(traded - set(quantities.columns))
    if no_price:
        msgs.append(f"No price series for {', '.join(no_price)} -- their unrealized P&L is 0.")
    if no_trades:
        msgs.append(f"Held but no trades mapped to {', '.join(no_trades)} -- no book cost, unrealized P&L is 0. "
                    f"Check the Market names / TICKER_MAP.")
    if not_held:
        msgs.append(f"Traded but not in the holdings: {', '.join(not_held)} "
                    f"(realized P&L on these isn't in the P&L history).")
    if held and len(no_price) + len(no_trades) >= len(held):
        msgs.append("No held asset has both a price and a book cost, so the P&L charts are flat at 0.")
    return msgs


def pnl_history_from_ledger(quantities: pd.DataFrame, prices_base: pd.DataFrame, avg_cost: pd.DataFrame,
                            realized: pd.DataFrame, fx: Optional[pd.DataFrame] = None,
                            trade_ccy: Optional[pd.Series] = None, fees: Optional[pd.DataFrame] = None,
                            base: str = 'USD') -> pd.DataFrame:
    """Daily total P&L per asset in the base currency:
    units x (price in base - book cost x FX of the trade currency) + realized - fees."""
    tick = [c for c in quantities.columns if c not in CASH_COLUMNS and c in prices_base.columns]
    idx = quantities.index
    px_ = asof_frame(prices_base, idx, tick)
    ac = asof_frame(avg_cost, idx, tick)
    rl = asof_frame(realized, idx, tick, fill=0.0)
    fe = asof_frame(fees, idx, tick, fill=0.0) if fees is not None and not fees.empty else 0.0
    rate = pd.DataFrame(1.0, index=idx, columns=tick)
    if fx is not None and trade_ccy is not None:
        rates = asof_frame(fx, idx, list(fx.columns)).bfill()
        for t in tick:
            ccy = trade_ccy.get(t, base)
            if ccy in rates.columns:
                rate[t] = rates[ccy].fillna(1.0)
    unrealized = (quantities[tick] * (px_ - ac * rate)).where(quantities[tick].abs() > 1e-12, 0.0).fillna(0.0)
    pnl = unrealized + (rl - fe) * rate
    pnl[TOTAL] = pnl.sum(axis=1)
    return pnl


def spot_rates(fx: pd.DataFrame, currencies: pd.Series) -> pd.Series:
    """Latest rate for each ticker's currency (1.0 when unknown)"""
    last = fx.ffill().iloc[-1]
    return currencies.map(lambda c: last.get(c, np.nan)).astype(float).fillna(1.0)


def implied_prices(positions: pd.DataFrame, quantities: pd.DataFrame) -> pd.DataFrame:
    """Prices implied by the history files (value / units, in the positions' currency)"""
    if positions.empty or quantities.empty:
        return pd.DataFrame()
    cols = [c for c in quantities.columns if c in positions.columns and c not in CASH_COLUMNS]
    q = quantities[cols].reindex(positions.index)
    return (positions[cols] / q.where(q.abs() > 1e-12)).ffill()


def holdings_table(units: pd.Series, quote_ccy: pd.Series, prices: pd.Series, rates: pd.Series) -> pd.DataFrame:
    """Current holdings valued in the base currency (price in the quote currency x FX).

    Columns: Currency, Quantity, Price, FX Rate, Market Value, Weights, plus
    'Current Portfolio' / 'Current Weights' (aliases used by the positioning table).
    """
    holdings = pd.DataFrame({'Currency': quote_ccy.reindex(units.index), 'Quantity': units})
    holdings['Price'] = prices.reindex(holdings.index)
    holdings.loc[holdings.index.isin(CASH_COLUMNS), 'Price'] = 1.0
    holdings['FX Rate'] = rates.reindex(holdings.index)
    holdings['Market Value'] = holdings['Quantity'] * holdings['Price'] * holdings['FX Rate']
    amount = holdings['Market Value'].sum()
    holdings['Weights'] = holdings['Market Value'] / amount if amount else 0.0
    return holdings.sort_values(by='Weights', ascending=False)


def pnl_table(holdings: pd.DataFrame, trade_ccy: pd.Series, cost_rates: pd.Series, ledger: dict,
              closed_ccy: Optional[pd.Series] = None, closed_rates: Optional[pd.Series] = None) -> pd.DataFrame:
    """Holdings with average cost, book cost, unrealized / realized P&L and fees
    (from the trades only), all money columns from 'Market Value' on in base currency."""
    book_cost = ledger['book_cost']
    realized_pnl = ledger['realized_pnl']
    avg_now = book_cost.iloc[-1] if not book_cost.empty else pd.Series(dtype=float)
    real_now = realized_pnl['Realized PnL'] if not realized_pnl.empty else pd.Series(dtype=float)
    fees_now = ledger['fees_daily'].iloc[-1] if not ledger['fees_daily'].empty else pd.Series(dtype=float)
    real_now = real_now.reindex(real_now.index.union(fees_now.index)).fillna(0)

    pnl = holdings.copy()
    pnl.insert(pnl.columns.get_loc('Market Value') + 2, 'Cost Currency', trade_ccy.reindex(pnl.index))
    pnl['Average Cost'] = avg_now.reindex(pnl.index)
    pnl['Cost FX Rate'] = cost_rates.reindex(pnl.index)
    pnl['Units (trades)'] = ledger['net_quantities'].reindex(pnl.index)
    pnl['Book Cost'] = pnl['Average Cost'] * pnl['Units (trades)'] * pnl['Cost FX Rate']
    pnl['Unrealized P&L'] = pnl['Units (trades)'] * pnl['Price'] * pnl['FX Rate'] - pnl['Book Cost']

    # closed positions still carry realized P&L
    closed = real_now.index.difference(pnl.index)
    for t in closed:
        pnl.loc[t] = np.nan
        if closed_ccy is not None:
            pnl.loc[t, 'Cost Currency'] = closed_ccy.get(t)
        if closed_rates is not None:
            pnl.loc[t, 'Cost FX Rate'] = closed_rates.get(t, 1.0)

    pnl['Realized P&L'] = (real_now.reindex(pnl.index) * pnl['Cost FX Rate']).fillna(0.0)
    pnl['Fees'] = (-fees_now.reindex(pnl.index) * pnl['Cost FX Rate']).fillna(0.0)
    pnl.loc[pnl.index.isin(CASH_COLUMNS), ['Average Cost', 'Book Cost', 'Unrealized P&L']] = np.nan
    pnl['Total P&L'] = pnl['Unrealized P&L'].fillna(0) + pnl['Realized P&L'] + pnl['Fees']
    pnl = pnl.sort_values(by='Weights', ascending=False)

    total = pnl.sum(numeric_only=True, min_count=1)
    for col in ('Quantity', 'Units (trades)', 'Price', 'Average Cost', 'FX Rate', 'Cost FX Rate'):
        if col in total.index:
            total[col] = np.nan
    invested = pnl['Book Cost'].sum()
    pnl['Total P&L %'] = pnl['Total P&L'] / invested * 100 if invested else 0.0
    total['Total P&L %'] = total['Total P&L'] / invested * 100 if invested else 0.0
    pnl.loc[TOTAL] = total
    return pnl


def unexplained_units(units: pd.Series, ledger: dict) -> pd.Series:
    """Units held that the trade history doesn't explain (transfers? missing trades?)"""
    assets = [a for a in units.index if a not in CASH_COLUMNS]
    gap = units.reindex(assets).fillna(0) - ledger['net_quantities'].reindex(assets).fillna(0)
    return gap[gap.abs() > 1e-6]


def historical_returns(weights: pd.DataFrame, prices_base: pd.DataFrame) -> pd.DataFrame:
    """Per-asset daily contributions of the real portfolio: yesterday's weights
    (carried over non-trading days) x today's returns in base currency."""
    simple_returns = prices_base.pct_change(fill_method=None)
    common = simple_returns.columns.intersection(weights.columns)
    w = ffill_align(weights[common], simple_returns.index).shift(1)
    valid = w.notna().any(axis=1)
    return (simple_returns[common] * w)[valid]


def positions_to_base(positions: pd.DataFrame, rate: pd.Series) -> pd.DataFrame:
    """Positions values (positions currency) x daily rate to the base currency"""
    return positions.mul(rate.reindex(positions.index).ffill().bfill().fillna(1.0), axis=0)


def drop_cash(columns: Sequence[str]) -> List[str]:
    return [c for c in columns if c not in CASH_COLUMNS and c != TOTAL]
