# Copyright (c) 2025 Niroojane Selvam
# Licensed under the MIT License. See LICENSE file in the project root for full license information.


#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import requests
import datetime
import numpy as np
from .Binance_API import BinanceAPI, pair_price


# =============================================================================
# P&L maths on a trade history (shared by the notebooks, Streamlit and the web app)
# =============================================================================
# `trades`: Binance trade history with the columns Date(UTC), Market, Type (BUY/SELL),
# Amount, Price in USDT, Total in USDT and Pair Price (see PnL.get_trade_in_usdt).

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


# In[2]:


class PnL:

    def __init__(self,binance_api_key,binance_api_secret):
    
        self.binance_api_key=binance_api_key
        self.binance_api_secret=binance_api_secret
        
        self.binance=BinanceAPI(binance_api_key,binance_api_secret)
        
    def get_trade_in_usdt(self,trade_history):

        trade_history['Date(UTC)']=pd.to_datetime(trade_history['Date(UTC)'])
        
        new_cols=['Pair Price','Price in USDT','Total in USDT','Pair Quantity']
        
        missing_cols = [col for col in new_cols if col not in trade_history.columns]
        
        for col in missing_cols:
            
            trade_history[col] = None    
            trade_history['Pair Price']=np.nan
            trade_history['Price in USDT']=np.nan
            trade_history['Total in USDT']=np.nan
            trade_history['Pair Quantity']=np.nan
        
        trade_price = {}
        
        for index in trade_history.index:
            
            if pd.isna(trade_history.iloc[index]['Pair Quantity']):
                
                market = trade_history.iloc[index]['Market']
                time_of_trade = trade_history.iloc[index]['Date(UTC)']

                trade_price[index] = (time_of_trade, market,
                                      pair_price(self.binance.binance_api, market, time_of_trade))

                print(index,trade_price[index][0],trade_price[index][1],trade_price[index][2])
            else:
                continue
                
        # Merge with trade_history
        price = pd.DataFrame(trade_price.values(),index=trade_price.keys(),columns=['Time','Market','Pair Price'])
        
        trade_history.iloc[price.index,8]=price['Pair Price']
        
        # Convert to USDT
        trade_history['Price in USDT'] = np.where(
            trade_history['Market'].str[-4:] == 'USDT',
            trade_history['Price'].astype(float),
            trade_history['Price'].astype(float) * trade_history['Pair Price'].astype(float)
        )
        
        # Compute total and pair quantity
        trade_history['Total in USDT'] = trade_history['Price in USDT'] * trade_history['Amount'].astype(float)
        trade_history['Pair Quantity'] = trade_history['Total in USDT'] / trade_history['Price in USDT']
        trade_history.set_index('Date(UTC)')
        
        return trade_history

        
    def get_crypto_traded(self, price):
        return get_crypto_traded(price)

    # def get_book_cost(self, price):
    #     """
    #     Compute average book cost per asset in USDT terms,
    #     correctly handling trades like ETHBTC (cross pairs).
    #     """
    
    #     crypto_list = self.get_crypto_traded(price)
    
    #     dynamic_average_total = {}
    #     dynamic_average_amount = {}
    
    #     dataframe_amount = {}
    #     dataframe_total = {}
    
    #     for crypto in crypto_list:
    
    #         # Select rows where this crypto is base OR quote
    #         dataset = price[(price['Market'].str[:len(crypto)] == crypto) | 
    #                         (price['Market'].str[-len(crypto):] == crypto)].copy()
    
    #         # --- BASE asset logic (e.g., ETH in ETHBTC) ---
    #         base_dataset = dataset[dataset['Market'].str[:len(crypto)] == crypto]
    
    #         if not base_dataset.empty:
    #             index = base_dataset[base_dataset['Type'] == 'BUY'].index
    #             results_amount = list(zip(price.iloc[index]['Date(UTC)'], price.iloc[index]['Amount']))
    #             results_total = list(zip(price.iloc[index]['Date(UTC)'], price.iloc[index]['Total in USDT']))
    #             dynamic_average_total[crypto] = results_total
    #             dynamic_average_amount[crypto] = results_amount
    
    #         # --- QUOTE asset logic (e.g., BTC in ETHBTC) ---
    #         quote_dataset = dataset[dataset['Market'].str[-len(crypto):] == crypto]
    
    #         if not quote_dataset.empty:
    #             for idx, row in quote_dataset.iterrows():
    #                 trade_date = row['Date(UTC)']
    #                 total_usdt = float(row['Total in USDT'])
    #                 pair_price = float(row['Pair Price'])
    #                 amount_in_quote = total_usdt / pair_price  # amount of quote asset spent/received
    
    #                 if row['Type'] == 'BUY':
    #                     # buying base → spending quote
    #                     dynamic_average_total.setdefault(crypto, []).append((trade_date, -total_usdt))
    #                     dynamic_average_amount.setdefault(crypto, []).append((trade_date, -amount_in_quote))
    #                 elif row['Type'] == 'SELL':
    #                     # selling base → receiving quote
    #                     dynamic_average_total.setdefault(crypto, []).append((trade_date, total_usdt))
    #                     dynamic_average_amount.setdefault(crypto, []).append((trade_date, amount_in_quote))
    
    #         # Convert to DataFrames
    #         if crypto in dynamic_average_total:
    #             temp = pd.DataFrame(dynamic_average_total[crypto], columns=['Date', 'Total']).groupby(by='Date').sum()
    #             temp_amount = pd.DataFrame(dynamic_average_amount[crypto], columns=['Date', 'Quantities']).groupby(by='Date').sum()
    #             dataframe_total[crypto + 'USDT'] = dict(zip(temp.index, temp['Total']))
    #             dataframe_amount[crypto + 'USDT'] = dict(zip(temp_amount.index, temp_amount['Quantities']))
    
    #     # Cumulative sums
    #     quantities = pd.DataFrame(dataframe_amount).sort_index().cumsum().ffill().fillna(0)
    #     total = pd.DataFrame(dataframe_total).sort_index().cumsum().ffill().fillna(0)
    
    #     # Average book cost
    #     book_cost = (total.shift(-1) + total) / (quantities.shift(-1) + quantities)
    #     book_cost = book_cost.fillna(0)
    #     book_cost.iloc[-1] = total.iloc[-1] / quantities.iloc[-1]
    
    #     return book_cost
        
    def get_book_cost(self, price):
        """Average book cost per asset in USDT (weighted-average cost method)"""
        return get_book_cost(price)

    def get_pnl(self,book_cost,price):
        return get_pnl(book_cost, price)

    def get_historical_positions(self,price):
        return get_historical_positions(price)

