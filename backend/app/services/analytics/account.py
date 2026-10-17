"""Real-portfolio computations: holdings, positioning vs. the model, P&L.

Port of the Crypto App notebook's `get_holdings`, `get_pnl_on_click`,
`check_connection` and `get_ex_post_returns`. Pure functions: the Binance /
GitHub I/O lives in `app.services.account`.
"""
from typing import Dict, Optional

import numpy as np
import pandas as pd

from .pnl import get_book_cost, get_pnl

VALUE = 'Current Portfolio in USDT'
WEIGHT = 'Current Weights'
TOTAL = 'Total'
# Rebrands with a share conversion: the new ticker's book cost derives from the old one
TICKER_ALIASES = {'MANTRAUSDT': ('OMUSDT', 1 / 4)}
EXCLUDED_FROM_PNL = ('USDCUSDT',)


def holdings_table(balances: pd.DataFrame, prices: pd.Series) -> pd.DataFrame:
    """Value and weight of each held asset + 'Total' (balances: ticker x free / locked)"""
    units = balances['free'].astype(float) + balances['locked'].astype(float)
    value = (units * prices.reindex(units.index)).fillna(0.0)
    table = pd.DataFrame({VALUE: value, WEIGHT: value / value.sum()})
    table.loc[TOTAL] = table.sum()
    return table.sort_values(by=WEIGHT, ascending=False).round(4)


def positioning_table(holdings: pd.DataFrame, model_weights: pd.Series, value_col: str = VALUE) -> pd.DataFrame:
    """Current holdings vs. the model allocation scaled to the portfolio value

    `holdings`: value (`value_col`) and weight of each held asset + a 'Total' row.
    """
    amount = holdings.loc[TOTAL, value_col]
    current = holdings.loc[holdings.index != TOTAL]

    model_weights = model_weights.fillna(0.0)
    weights = model_weights / model_weights.sum() if model_weights.sum() else model_weights
    out_of_model = current.loc[~current.index.isin(weights.index), value_col].sum()

    model = pd.DataFrame({
        'Model': weights * amount,
        'Model (without out of Model Positions)': weights * (amount - out_of_model),
        'Weights Model': weights,
    })
    table = pd.concat([model, current], axis=1).fillna(0)
    table['Spread'] = table[value_col] - table['Model']
    table.loc[TOTAL] = table.sum(axis=0)
    table = table.loc[~(table == 0).all(axis=1)]
    return table.sort_values(by='Weights Model', ascending=False).round(4)


def trades_in_usdt(trades: pd.DataFrame) -> pd.DataFrame:
    """Price / total / quantity in USDT of each trade, given its 'Pair Price'
    (price of the quote asset in USDT; 1 for USDT markets)"""
    trades = trades.copy()
    trades['Date(UTC)'] = pd.to_datetime(trades['Date(UTC)'])
    price = trades['Price'].astype(float)
    trades['Price in USDT'] = np.where(trades['Market'].str[-4:] == 'USDT', price,
                                       price * trades['Pair Price'].astype(float))
    trades['Total in USDT'] = trades['Price in USDT'] * trades['Amount'].astype(float)
    trades['Pair Quantity'] = trades['Total in USDT'] / trades['Price in USDT']
    return trades


def book_cost_and_pnl(trades: pd.DataFrame):
    """(average book cost history, realized P&L per asset)"""
    book_cost = get_book_cost(trades)
    for ticker, (source, ratio) in TICKER_ALIASES.items():
        if source in book_cost.columns:
            book_cost[ticker] = book_cost[source] * ratio
    realized, _ = get_pnl(book_cost, trades)
    return book_cost, realized


def pnl_table(book_cost: pd.DataFrame, realized: pd.DataFrame, holdings: pd.DataFrame,
              free_units: pd.Series) -> pd.DataFrame:
    """Average cost, book cost, value, realized and unrealized P&L per held asset"""
    last_cost = book_cost.iloc[-1] if not book_cost.empty else pd.Series(dtype=float)
    current = holdings.loc[holdings.index != TOTAL]

    pnl = pd.concat([last_cost, last_cost, current[VALUE], current[WEIGHT], realized['Realized PnL']], axis=1)
    pnl.columns = ['Average Cost', 'Book Cost', 'Price in USDT', 'Weights', 'Realized P&L']
    pnl['Book Cost'] = (pnl['Book Cost'] * free_units.astype(float)).fillna(0)
    pnl['Unrealized P&L'] = (pnl['Price in USDT'] - pnl['Book Cost']).round(2)
    pnl = pnl.fillna(0)
    pnl['Weights'] = pnl['Weights'].round(4)
    pnl['Total P&L'] = pnl['Unrealized P&L']  # realized P&L intentionally excluded

    pnl.loc[TOTAL] = pnl.sum()
    pnl.loc[TOTAL, 'Average Cost'] = np.nan
    pnl.loc[TOTAL, 'Book Cost'] = pnl.loc[TOTAL, 'Price in USDT'] - pnl.loc[TOTAL, 'Total P&L']
    total_cost = pnl.loc[TOTAL, 'Book Cost']
    pnl['Total P&L %'] = pnl['Total P&L'] / total_cost * 100 if total_cost else 0
    return pnl.sort_values(by='Weights', ascending=False).round(4)


def merge_history(saved: Optional[pd.DataFrame], recent: Optional[pd.DataFrame], prefer_recent: bool = True,
                  with_total: bool = False) -> pd.DataFrame:
    """Saved history (GitHub files) + recent Binance snapshots, one row per day"""
    frames = [f.copy() for f in (saved, recent) if f is not None and not f.empty]
    if not frames:
        return pd.DataFrame()
    for frame in frames:
        frame.index = pd.to_datetime(frame.index)
    merged = pd.concat(frames).sort_index()
    merged = merged.loc[~merged.index.duplicated(keep='last' if prefer_recent else 'first')]
    if with_total:
        merged[TOTAL] = merged.loc[:, merged.columns != TOTAL].sum(axis=1)
    return merged


def snapshot_positions(snapshots: list, prices: pd.DataFrame):
    """(positions, quantities) per day from Binance account snapshots"""
    holdings: Dict[str, Dict[str, float]] = {}
    for snapshot in snapshots:
        day = pd.Timestamp(snapshot['date']).strftime('%Y-%m-%d')
        holdings[day] = {b['asset'] + 'USDT': float(b['total']) for b in snapshot['balances']}
    quantities = pd.DataFrame(holdings).T
    if quantities.empty:
        return pd.DataFrame(), pd.DataFrame()
    quantities.index = pd.to_datetime(quantities.index)
    prices = prices.loc[~prices.index.duplicated(keep='last')]
    positions = (quantities * prices.reindex(index=quantities.index, columns=quantities.columns))
    return positions.groupby(level=0).sum(), quantities


def pnl_history(quantities: pd.DataFrame, book_cost: pd.DataFrame, prices: pd.DataFrame):
    """(unrealized P&L per asset + 'Total' each day, daily change of the total)"""
    daily_cost = book_cost.resample('D').last().dropna(how='all').sort_index()
    cols = [c for c in quantities.columns if c not in EXCLUDED_FROM_PNL]

    cost_history = daily_cost.reindex(daily_cost.index.union(quantities.index)).sort_index().ffill()
    cost_history = cost_history.reindex(index=quantities.index, columns=cols)
    prices = prices.reindex(index=quantities.index, columns=cols)

    history = (quantities[cols] * (prices - cost_history)).sort_index()
    history[TOTAL] = history.sum(axis=1)
    daily = history[TOTAL] - history[TOTAL].shift(1)
    return history, daily


def pnl_analysis(positions: pd.DataFrame, history: pd.DataFrame, daily: pd.Series, start, end) -> dict:
    """Portfolio value, cumulative P&L and P&L contribution over the window (P&L > P&L Analysis)"""
    cumulative = daily.loc[start:end].copy()
    if cumulative.empty:
        raise ValueError("No P&L data in the selected date range")
    cumulative.iloc[0] = 0
    summary = pd.concat([cumulative.cumsum(), history[TOTAL].loc[start:end]], axis=1)
    summary.columns = ['Cumulative P&L', 'Total P&L']

    contribution = (history - history.shift(1)).loc[start:end]
    cumulative_contribution = pd.concat(
        [contribution.loc[:, contribution.columns != TOTAL].cumsum(), summary], axis=1
    )
    return {
        'positions': positions.loc[start:end],
        'cumulative_contribution': cumulative_contribution,
        'daily_pnl': contribution,
    }
