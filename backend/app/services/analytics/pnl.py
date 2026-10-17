"""Book cost, realized PnL and historical positions from a trade history.

Ported from the pure-computation methods of the legacy `src/PnL_Computation.py`
`PnL` class (Risk Management project). The conversion of trade prices to USDT
(`get_trade_in_usdt`), which calls Binance, is not part of this module.

`trades` is a Binance trade-history frame with the columns
'Date(UTC)', 'Market', 'Type' (BUY/SELL), 'Amount', 'Price in USDT',
'Total in USDT' and 'Pair Price'.
"""
import numpy as np
import pandas as pd


def get_crypto_traded(trades):
    """Every asset appearing in a traded market, as base or quote."""
    crypto_list = set()
    for market in set(trades['Market']):
        if market.endswith('USDT'):
            crypto_list.add(market[:-4])
            crypto_list.add('USDT')
        else:
            crypto_list.add(market[:-3])
            crypto_list.add(market[-3:])

    return crypto_list


def get_book_cost(trades):
    """Average book cost per asset in USDT, weighted-average cost method:

        new_cost_price = (old_cost_price * old_balance + purchase_cost) / new_balance

    Cost price only changes on acquisitions (buys of the base asset, or
    receiving the quote asset). Disposals reduce the balance only; a fully
    closed position resets the cost basis.
    """
    book_costs = {}

    for crypto in get_crypto_traded(trades):

        dataset = trades[(trades['Market'].str[:len(crypto)] == crypto) |
                         (trades['Market'].str[-len(crypto):] == crypto)]

        events = []  # (date, amount_delta, total_usdt_delta)

        # --- BASE asset (e.g., ETH in ETHBTC) ---
        base_dataset = dataset[dataset['Market'].str[:len(crypto)] == crypto]
        for _, row in base_dataset.iterrows():
            amount = float(row['Amount'])
            total_usdt = float(row['Total in USDT'])
            if row['Type'] == 'BUY':
                events.append((row['Date(UTC)'], amount, total_usdt))
            elif row['Type'] == 'SELL':
                events.append((row['Date(UTC)'], -amount, -total_usdt))

        # --- QUOTE asset (e.g., BTC in ETHBTC) ---
        quote_dataset = dataset[dataset['Market'].str[-len(crypto):] == crypto]
        for _, row in quote_dataset.iterrows():
            total_usdt = float(row['Total in USDT'])
            amount_in_quote = total_usdt / float(row['Pair Price'])

            if row['Type'] == 'BUY':
                # buying base with quote -> disposing quote
                events.append((row['Date(UTC)'], -amount_in_quote, -total_usdt))
            elif row['Type'] == 'SELL':
                # selling base for quote -> acquiring quote
                events.append((row['Date(UTC)'], amount_in_quote, total_usdt))

        if not events:
            continue

        # Aggregate multiple trades on the same date
        events_df = (pd.DataFrame(events, columns=['Date', 'Amount', 'Total'])
                     .groupby('Date').sum().sort_index())

        balance = 0.0
        cost_price = 0.0
        dates, cost_prices = [], []

        for date, row in events_df.iterrows():
            amount_delta = row['Amount']

            if amount_delta > 0:
                new_balance = balance + amount_delta
                if new_balance != 0:
                    cost_price = (cost_price * balance + row['Total']) / new_balance
                balance = new_balance
            else:
                balance += amount_delta
                if balance <= 1e-12:
                    balance = 0.0
                    cost_price = 0.0  # position fully closed, reset cost basis

            dates.append(date)
            cost_prices.append(cost_price)

        book_costs[crypto + 'USDT'] = pd.Series(cost_prices, index=dates)

    return pd.DataFrame(book_costs).sort_index().ffill().fillna(0)


def get_pnl(book_cost, trades):
    """Realized PnL per asset: (sell price - book cost) x quantity sold.

    Returns (realized PnL table, {asset: PnL per trade date}).
    """
    profit_and_loss = {}
    pnl_per_crypto = {}

    for crypto in get_crypto_traded(trades):
        if crypto + 'USDT' not in book_cost.columns:
            continue

        temp = trades[trades['Market'].str[:len(crypto)] == crypto].copy()
        temp['Flows'] = np.where(temp['Type'] == 'SELL', -temp['Amount'], temp['Amount'])
        temp = temp.set_index('Date(UTC)').sort_index()
        temp['Cost'] = book_cost[crypto + 'USDT']
        temp['Cost'] = temp['Cost'].ffill()
        temp[crypto] = np.where(temp['Type'] == 'SELL', (temp['Cost'] - temp['Price in USDT']) * temp['Flows'], 0)

        profit_and_loss[crypto] = temp[crypto]
        pnl_per_crypto[crypto + 'USDT'] = profit_and_loss[crypto].sum()

    realized_pnl = pd.DataFrame(pnl_per_crypto.values(), index=pnl_per_crypto.keys(), columns=['Realized PnL'])

    return realized_pnl, profit_and_loss


def get_historical_positions(trades):
    """Cumulative units held per base asset at the end of each day."""
    dataframe_total = {}

    for crypto in get_crypto_traded(trades):
        dataset = trades[trades['Market'].str[:len(crypto)] == crypto].copy()
        dataset['Quantities'] = np.where(dataset['Type'] == "SELL",
                                         -dataset['Amount'].astype(float),
                                         dataset['Amount'].astype(float))

        temp = dataset[['Date(UTC)', 'Quantities']].rename(columns={'Date(UTC)': 'Date'}).groupby(by='Date').sum()
        dataframe_total[crypto] = dict(zip(temp.index, temp['Quantities']))

    historical_positions = pd.DataFrame(dataframe_total).sort_index()
    historical_positions = historical_positions.groupby(historical_positions.index).sum()
    historical_positions.index = historical_positions.index.round('d')
    return historical_positions.groupby(historical_positions.index).sum().cumsum()
