"""
Daily save-down of the current portfolio -- the Excel/yfinance counterpart of
the old Binance positions history.

Reads   Current Portfolio.xlsx   (asset, free, locked, ...; cash lines = 'USD', 'EUR', ...)
        Trade History.xlsx       (optional, to fill days that were never saved)
Writes one row per day to
        Quantities.xlsx          units held per ticker (+ cash)
        Positions.xlsx           market value per ticker (+ cash) and 'Total',
                                 in BASE_CURRENCY = units x close x FX

* Today's row comes from the current portfolio. Running twice on the same day
  replaces that row (no duplicates).
* Days missed since the last save are filled: holdings on a missed day are
  today's holdings with every later trade undone (units and cash), valued at
  that day's close and FX. Days already saved are never rewritten.
* Check: the same roll-back is done for the last saved day and compared with
  the file. A difference means the trades don't explain the gap (deposit,
  withdrawal, missing trade, split) -- it's reported, and the filled days may
  be off by that amount.
* A ticker bought for the first time gets a new column (earlier days = 0).
* Files are written to a temporary file first and then swapped in.

Usage (file names are passed explicitly, so they can be anything):
    python update_positions.py --portfolio "Current Portfolio.xlsx" \
        --quantities "Quantities.xlsx" --positions "Positions.xlsx" --trades "Trade History.xlsx"
    python update_positions.py ... --date 2026-09-25 --base EUR --no-fill

From Python / the app:
    main(current_portfolio_path, quantities_path, positions_path, trades_path=...)
"""
import argparse
import datetime
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

try:                                   # inside your src package
    from .Yahoo_API import get_close, get_currencies, get_fx_rates
except ImportError:
    try:
        from src.Yahoo_API import get_close, get_currencies, get_fx_rates
    except ImportError:                # plain script next to Yahoo_API.py
        from Yahoo_API import get_close, get_currencies, get_fx_rates

BASE_CURRENCY = 'USD'
CASH_ASSETS = {'USD', 'EUR', 'GBP', 'CHF', 'JPY', 'CAD', 'AUD', 'HKD', 'SEK', 'NOK',
               'DKK', 'SGD', 'HUF', 'PLN', 'CZK', 'NZD', 'ZAR', 'ILS', 'CNY', 'INR', 'Cash'}
FIAT_SUFFIXES = sorted(CASH_ASSETS - {'Cash'}, key=len, reverse=True)
# asset code in Current Portfolio.xlsx / Market -> yfinance ticker (keep in sync with the app)
TICKER_MAP = {}
UNIT_TOL = 1e-6          # units
CASH_TOL = 0.01          # currency units


# -----------------------------------------------------------------------------
# Inputs
# -----------------------------------------------------------------------------
def read_current_portfolio(path):
    """Units per ticker = free + locked (cash lines keep their currency code)."""
    df = pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]
    units = sum(pd.to_numeric(df[c], errors='coerce').fillna(0) for c in ('free', 'locked') if c in df.columns)
    assets = df['asset'].astype(str).str.strip()
    tick = [a if a in CASH_ASSETS else TICKER_MAP.get(a, a) for a in assets]
    out = pd.Series(np.asarray(units, dtype=float), index=tick).groupby(level=0).sum()
    return out[out.abs() > 1e-12]


def read_trades(path):
    """Trade History.xlsx (Date(UTC), Market, Type, Price, Amount, Total, Fee, Fee Coin)
    -> Date, Ticker, Currency, Side, Quantity, Notional, Fee (fee in the trade currency)."""
    raw = pd.read_excel(path)
    raw.columns = [str(c).strip() for c in raw.columns]
    rows = []
    for r in raw.to_dict('records'):
        market = str(r.get('Market', '')).strip()
        ccy = next((c for c in FIAT_SUFFIXES if market.endswith(c) and len(market) > len(c)), None)
        if ccy is None:
            continue
        asset = market[:-len(ccy)]
        side = str(r.get('Type', '')).strip().upper()
        qty = float(pd.to_numeric(r.get('Amount'), errors='coerce'))
        price = float(pd.to_numeric(r.get('Price'), errors='coerce'))
        notional = pd.to_numeric(r.get('Total'), errors='coerce')
        notional = qty * price if pd.isna(notional) else float(notional)
        fee = pd.to_numeric(r.get('Fee', 0), errors='coerce')
        fee = 0.0 if pd.isna(fee) else float(fee)
        coin = str(r.get('Fee Coin', '') or '').strip()
        coin = '' if coin.lower() == 'nan' else coin
        fee_cash = 0.0
        if coin in ('', ccy):
            fee_cash = fee
        elif coin == asset:
            if side == 'BUY':
                qty -= fee
            else:
                fee_cash = fee * price
        rows.append({'Date': pd.to_datetime(r.get('Date(UTC)'), errors='coerce'),
                     'Ticker': TICKER_MAP.get(asset, asset), 'Currency': ccy, 'Side': side,
                     'Quantity': qty, 'Notional': notional, 'Fee': fee_cash})
    return pd.DataFrame(rows).dropna(subset=['Date', 'Quantity'])


def load_history(path):
    if Path(path).exists():
        hist = pd.read_excel(path, index_col=0)
        hist.index = pd.to_datetime(hist.index).normalize()
        return hist.sort_index()
    return pd.DataFrame()


# -----------------------------------------------------------------------------
# Rolling holdings back through the trades
# -----------------------------------------------------------------------------
def roll_back(units_today, trades, days, today):
    """Holdings at the end of each day in `days`: today's holdings with every
    trade dated after that day (up to today) undone, units and cash."""
    if trades is None or trades.empty:
        return pd.DataFrame({d: units_today for d in days}).T
    t = trades.copy()
    t['Day'] = pd.to_datetime(t['Date']).dt.normalize()
    t = t[t['Day'] <= today]
    sign = np.where(t['Side'] == 'SELL', -1.0, 1.0)
    t['dUnits'] = sign * t['Quantity']
    t['dCash'] = -sign * t['Notional'] - t['Fee']
    rows = {}
    for d in days:
        after = t[t['Day'] > d]
        u = units_today.copy()
        u = u.sub(after.groupby('Ticker')['dUnits'].sum(), fill_value=0.0)
        u = u.sub(after.groupby('Currency')['dCash'].sum(), fill_value=0.0)
        rows[d] = u.where(u.abs() > 1e-9, 0.0)
    return pd.DataFrame(rows).T.fillna(0.0)


# -----------------------------------------------------------------------------
# Valuation
# -----------------------------------------------------------------------------
def value_history(units, base):
    """Market value in `base` for each day (row) of `units`: units x last close
    on/before that day x FX. Returns (values, prices, rates, missing)."""
    days = units.index
    etfs = [c for c in units.columns if c not in CASH_ASSETS]
    cash = [c for c in units.columns if c in CASH_ASSETS]
    start = (days.min() - pd.Timedelta(days=15)).date()
    end = days.max().date()

    def as_of(frame):
        return frame.reindex(frame.index.union(days)).sort_index().ffill().reindex(days)

    closes = get_close(etfs, start=start, end=end) if etfs else pd.DataFrame(index=days)
    prices = as_of(closes).reindex(columns=etfs) if not closes.empty else pd.DataFrame(np.nan, index=days, columns=etfs)
    for c in cash:
        prices[c] = 1.0

    quote = get_currencies(etfs) if etfs else pd.Series(dtype=object)
    ccys = {t: (quote.get(t) or base) for t in etfs}
    ccys.update({c: (base if c == 'Cash' else c) for c in cash})
    fx = get_fx_rates(set(ccys.values()), base=base, start=start, end=end)
    fx_days = as_of(fx)
    rates = pd.DataFrame({t: fx_days[ccys[t]] if ccys[t] in fx_days.columns else 1.0 for t in units.columns},
                         index=days)
    no_fx = sorted({ccys[t] for t in units.columns if ccys[t] not in fx_days.columns})
    if no_fx:
        print(f"⚠️ No FX rate {', '.join(no_fx)} -> {base}; treated as 1.0")

    held = units.abs() > 1e-12
    missing = sorted(c for c in etfs if (prices[c].isna() & held[c]).any())
    values = (units * prices[units.columns].fillna(0.0) * rates).where(held, 0.0)
    return values, prices[units.columns], rates, missing


# -----------------------------------------------------------------------------
# Files
# -----------------------------------------------------------------------------
def merge_rows(hist, new_rows, replace):
    """Add `new_rows` (index = dates); dates in `replace` overwrite existing
    rows, other dates are only added if absent. New columns start at 0."""
    keep_new = [d for d in new_rows.index if d in replace or d not in hist.index]
    hist = hist.drop(index=[d for d in replace if d in hist.index], errors='ignore')
    out = pd.concat([hist, new_rows.loc[keep_new]])
    cols = [c for c in out.columns if c != 'Total'] + (['Total'] if 'Total' in out.columns else [])
    out = out[cols].sort_index().fillna(0.0)
    out.index.name = 'Date'
    return out


def atomic_write_excel(df, path):
    """Write to a temp file in the same folder, then swap it in."""
    folder = Path(path).resolve().parent
    fd, tmp = tempfile.mkstemp(suffix='.xlsx', dir=folder)
    os.close(fd)
    try:
        df.to_excel(tmp)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def update_files(current_portfolio_path, quantities_path, positions_path, date=None, base=BASE_CURRENCY,
                 trades=None, fill_gaps=True):
    """Save `date`'s holdings (default today) and fill the days missed since the
    last save. `trades`: a DataFrame (Date, Ticker, Currency, Side, Quantity,
    Notional, Fee) or a path to Trade History.xlsx; without it missed days are
    filled with today's holdings (only right if nothing was traded meanwhile).

    Returns (quantities, positions, summary, info) -- info has 'filled' (dates),
    'missing' (tickers without prices) and 'check' (reconciliation of the last
    saved day, or None).
    """
    for path in (quantities_path, positions_path):
        if str(path).lower().startswith(('http://', 'https://')):
            raise ValueError(f"Can't write to a URL: {path} -- point the app at local files to update them.")
    date = pd.Timestamp(date or datetime.date.today()).normalize()
    if isinstance(trades, (str, Path)):
        trades = read_trades(trades) if Path(trades).exists() else None

    units_today = read_current_portfolio(current_portfolio_path)
    q_hist, p_hist = load_history(quantities_path), load_history(positions_path)
    saved_before = q_hist.index[q_hist.index < date]
    last_saved = saved_before.max() if len(saved_before) else None

    gap = []
    if fill_gaps and last_saved is not None:
        gap = [d for d in pd.date_range(last_saved + pd.Timedelta(days=1), date - pd.Timedelta(days=1), freq='D')
               if d not in q_hist.index]
    days = pd.DatetimeIndex(gap + [date])
    units = roll_back(units_today, trades, days, date)

    # reconciliation: roll back to the last saved day and compare with the file
    check = None
    if last_saved is not None and trades is not None:
        rebuilt = roll_back(units_today, trades, [last_saved], date).iloc[0]
        saved = q_hist.loc[last_saved]
        cols = rebuilt.index.union(saved.index)
        diff = rebuilt.reindex(cols, fill_value=0.0) - saved.reindex(cols, fill_value=0.0)
        tol = pd.Series([CASH_TOL if c in CASH_ASSETS else UNIT_TOL for c in cols], index=cols)
        check = {'date': last_saved, 'differences': diff[diff.abs() > tol]}

    values, prices, rates, missing = value_history(units, base)
    positions_rows = values.copy()
    positions_rows['Total'] = values.sum(axis=1)

    quantities = merge_rows(q_hist, units, replace=[date])
    positions = merge_rows(p_hist, positions_rows, replace=[date])
    atomic_write_excel(quantities, quantities_path)
    atomic_write_excel(positions, positions_path)

    summary = pd.DataFrame({'Units': units.loc[date], 'Price': prices.loc[date], 'FX': rates.loc[date],
                            f'Value ({base})': values.loc[date]})
    summary = summary[summary['Units'].abs() > 1e-12]
    summary.loc['Total', f'Value ({base})'] = positions_rows.loc[date, 'Total']
    summary.attrs.update(date=date, base=base)
    info = {'filled': list(gap), 'missing': missing, 'check': check,
            'used_trades': trades is not None and not trades.empty}
    return quantities, positions, summary, info


def describe(summary, info, base):
    """Human-readable result lines (used by the CLI and the app)."""
    lines = [f"✅ {summary.attrs['date'].date()} saved: {len(summary) - 1} lines, "
             f"total {summary.iloc[-1, -1]:,.2f} {base}"]
    filled = info['filled']
    if filled:
        span = f"{filled[0].date()}" if len(filled) == 1 else f"{filled[0].date()} → {filled[-1].date()}"
        lines.append(f"🧩 Filled {len(filled)} missed day(s): {span}")
        if not info.get('used_trades'):
            lines.append("⚠️ No trade history available -- missed days were filled with today's holdings, "
                         "which is only right if nothing was traded in between.")
    check = info['check']
    if check is not None and not check['differences'].empty:
        d = check['differences'].round(6).to_dict()
        lines.append(f"⚠️ Trades don't explain the change since {check['date'].date()} "
                     f"(deposit, withdrawal, missing trade or split?): {d} -- filled days may be off by this.")
    if info['missing']:
        lines.append(f"⚠️ No price for {', '.join(info['missing'])} -- valued at 0 where missing.")
    return lines


def main(current_portfolio_path, quantities_path, positions_path, trades_path=None,
         date=None, base=BASE_CURRENCY, fill_gaps=True):
    """Save `date` (default today) and fill missed days, using the files you name.

    Example:
        main('Portfolio 2026-09.xlsx', 'My Quantities.xlsx', 'My Positions.xlsx',
             trades_path='Trades Q3.xlsx')
    """
    q, p, summary, info = update_files(current_portfolio_path, quantities_path, positions_path, date, base,
                                       trades=trades_path, fill_gaps=fill_gaps)
    print('\n'.join(describe(summary, info, base)))
    print(summary.round(4).to_string())
    return q, p


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description="Save today's holdings to the quantities and positions files, "
                                             "filling days missed since the last save")
    ap.add_argument('--portfolio', required=True, help='current portfolio file, e.g. "Current Portfolio.xlsx"')
    ap.add_argument('--quantities', required=True, help='quantities history file to update')
    ap.add_argument('--positions', required=True, help='positions history file to update')
    ap.add_argument('--trades', default=None, help='trade history file (needed to fill missed days correctly)')
    ap.add_argument('--date', default=None, help='valuation date (default: today)')
    ap.add_argument('--base', default=BASE_CURRENCY, help='currency for the positions file')
    ap.add_argument('--no-fill', action='store_true', help="don't fill days missed since the last save")
    args = ap.parse_args()
    main(args.portfolio, args.quantities, args.positions, args.trades, args.date, args.base,
         fill_gaps=not args.no_fill)