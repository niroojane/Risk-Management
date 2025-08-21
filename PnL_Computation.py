# Copyright (c) 2025 Niroojane Selvam
# Licensed under the MIT License. See LICENSE file in the project root for full license information.


#!/usr/bin/env python
# coding: utf-8

# In[1]:


from binance.spot import Spot
import pandas as pd
import requests
import datetime
import numpy as np
from Binance_API import BinanceAPI


# In[2]:


class PnL:

    def __init__(self,binance_api_key,binance_api_secret):
    
        self.binance_api_key=binance_api_key
        self.binance_api_secret=binance_api_secret
        
        self.binance=BinanceAPI(binance_api_key,binance_api_secret)
        
    def get_trade_in_usdt(self,trade_history):
    
        trade_history['Date(UTC)']=pd.to_datetime(trade_history['Date(UTC)'])
        trade_history=trade_history.set_index('Date(UTC)')
    
        trade_info=zip(trade_history['Market'],trade_history.index)
        trade_info=dict(enumerate(trade_info))
    
        trade_price={}
        for index in trade_info:
    
            if trade_info[index][0][-4:]=='USDT':
                ticker=trade_info[index][0]
            else:
                ticker=trade_info[index][0][-3:]+'USDT'

            time_of_trade=trade_info[index][1]
            time_of_trade_stamp=int(trade_info[index][1].round(freq='min').timestamp()-60)*1000
            
            price_data_api=self.binance.binance_api.klines(ticker,interval='1m',startTime=time_of_trade_stamp,limit=2)
            price_data=pd.DataFrame(price_data_api)
            numeric_columns =  ['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time', 'Quote Asset Volume', 
                                            'Number of Trades', 'TB Base Volume', 'TB Quote Volume', 'Ignore']
            price_data.columns=numeric_columns
            price_data['Close Time']=pd.to_datetime(price_data['Close Time'], unit='ms')
            
            close_prev = price_data.iloc[0]["Close"]
            close_next = price_data.iloc[1]["Close"]
            t_prev = price_data.iloc[0]["Close Time"]
            t_next = price_data.iloc[1]["Close Time"]
            
            weight_prev = (t_next - time_of_trade) / pd.Timedelta(minutes=1)
            weight_next = (time_of_trade - t_prev) / pd.Timedelta(minutes=1)
            
            pair_price = float(close_prev)* weight_prev + float(close_next) * weight_next
            trade_price[index]=(trade_info[index][1],trade_info[index][0],pair_price)
    
        price=pd.DataFrame(trade_price.values(),columns=['Time','Market','Pair Price'])
        price=pd.concat([trade_history.reset_index(),price['Pair Price']],axis=1)
        price['Price in USDT']=np.where(price['Market'].str[-4:]=='USDT',price['Price'],price['Price'].astype(float)*price['Pair Price'].astype(float))
        price['Total in USDT']=(price['Price in USDT'].astype(float))*(price['Amount'].astype(float))
        price['Pair Quantity']=price['Total in USDT']/price['Price in USDT']
        
        return price

    def get_crypto_traded(self, price):
    
        traded_crypto = set(price['Market'])  # include all trades, BUY and SELL
    
        crypto_list = set()
        for key in traded_crypto:
            if key.endswith('USDT'):
                base = key[:-4]
                crypto_list.add(base)
                crypto_list.add('USDT')  # include USDT explicitly
            else:
                base = key[:-3]
                quote = key[-3:]
                crypto_list.add(base)
                crypto_list.add(quote)
    
        return crypto_list
        

    def get_book_cost(self, price):
        """
        Compute average book cost per asset in USDT terms,
        correctly handling trades like ETHBTC (cross pairs).
        """
    
        crypto_list = self.get_crypto_traded(price)
    
        dynamic_average_total = {}
        dynamic_average_amount = {}
    
        dataframe_amount = {}
        dataframe_total = {}
    
        for crypto in crypto_list:
    
            # Select rows where this crypto is base OR quote
            dataset = price[(price['Market'].str[:len(crypto)] == crypto) | 
                            (price['Market'].str[-len(crypto):] == crypto)].copy()
    
            # --- BASE asset logic (e.g., ETH in ETHBTC) ---
            base_dataset = dataset[dataset['Market'].str[:len(crypto)] == crypto]
    
            if not base_dataset.empty:
                index = base_dataset[base_dataset['Type'] == 'BUY'].index
                results_amount = list(zip(price.iloc[index]['Date(UTC)'], price.iloc[index]['Amount']))
                results_total = list(zip(price.iloc[index]['Date(UTC)'], price.iloc[index]['Total in USDT']))
                dynamic_average_total[crypto] = results_total
                dynamic_average_amount[crypto] = results_amount
    
            # --- QUOTE asset logic (e.g., BTC in ETHBTC) ---
            quote_dataset = dataset[dataset['Market'].str[-len(crypto):] == crypto]
    
            if not quote_dataset.empty:
                for idx, row in quote_dataset.iterrows():
                    trade_date = row['Date(UTC)']
                    total_usdt = float(row['Total in USDT'])
                    pair_price = float(row['Pair Price'])
                    amount_in_quote = total_usdt / pair_price  # amount of quote asset spent/received
    
                    if row['Type'] == 'BUY':
                        # buying base → spending quote
                        dynamic_average_total.setdefault(crypto, []).append((trade_date, -total_usdt))
                        dynamic_average_amount.setdefault(crypto, []).append((trade_date, -amount_in_quote))
                    elif row['Type'] == 'SELL':
                        # selling base → receiving quote
                        dynamic_average_total.setdefault(crypto, []).append((trade_date, total_usdt))
                        dynamic_average_amount.setdefault(crypto, []).append((trade_date, amount_in_quote))
    
            # Convert to DataFrames
            if crypto in dynamic_average_total:
                temp = pd.DataFrame(dynamic_average_total[crypto], columns=['Date', 'Total']).groupby(by='Date').sum()
                temp_amount = pd.DataFrame(dynamic_average_amount[crypto], columns=['Date', 'Quantities']).groupby(by='Date').sum()
                dataframe_total[crypto + 'USDT'] = dict(zip(temp.index, temp['Total']))
                dataframe_amount[crypto + 'USDT'] = dict(zip(temp_amount.index, temp_amount['Quantities']))
    
        # Cumulative sums
        quantities = pd.DataFrame(dataframe_amount).sort_index().cumsum().ffill().fillna(0)
        total = pd.DataFrame(dataframe_total).sort_index().cumsum().ffill().fillna(0)
    
        # Average book cost
        book_cost = (total.shift(-1) + total) / (quantities.shift(-1) + quantities)
        book_cost = book_cost.fillna(0)
        book_cost.iloc[-1] = total.iloc[-1] / quantities.iloc[-1]
    
        return book_cost

    
    def get_pnl(self,book_cost,price):
    
        positions_history={}
        transaction_type={}
        results={}
        profit_and_loss={}
        pnl_per_crypto={}
    
        crypto_list=self.get_crypto_traded(price)
        
        for crypto in crypto_list:
    
            dataset=price[price['Market'].str[:len(crypto)]==crypto]
    
            grouped=dataset.groupby(by='Date(UTC)').sum()
            positions_history[crypto]=dict(zip(grouped.index,grouped['Amount'].astype(float)))
            transaction_type[crypto]=list(zip(dataset['Date(UTC)'],dataset['Type']))
    
            temp=price[price['Market'].str[:len(crypto)]==crypto].copy()
            temp['Flows']=np.where(temp['Type']=='SELL',-temp['Amount'],temp['Amount'])
            temp['Flows'].sum()
            temp=temp.set_index('Date(UTC)').sort_index()
            temp['Cost']=book_cost[crypto+'USDT']
            #temp['Cost']=temp['Cost'].fillna(method='ffill')
            temp['Cost']=temp['Cost'].ffill()
            temp[crypto]=np.where(temp['Type']=='SELL',(temp['Cost']-temp['Price in USDT'])*temp['Flows'],0)
            
            profit_and_loss[crypto]=temp[crypto]
    
            pnl_per_crypto[crypto+'USDT']=profit_and_loss[crypto].sum()
            
        realized_pnl=pd.DataFrame(pnl_per_crypto.values(),index=pnl_per_crypto.keys(),columns=['Realized PnL'])
        
        return realized_pnl,profit_and_loss

    def get_historical_positions(self,price):
    
        crypto_list=self.get_crypto_traded(price)
        quantities={}
        dataframe_total={}
    
    
        for crypto in crypto_list:
    
            dataset=price[price['Market'].str[:len(crypto)]==crypto].copy()
            dataset['Quantities']=np.where(dataset['Type']=="SELL",-dataset['Amount'].astype(float),dataset['Amount'].astype(float))
    
            quantities[crypto]=list(zip(dataset['Date(UTC)'],dataset['Quantities']))
            temp=pd.DataFrame(quantities[crypto],columns=['Date','Quantities']).groupby(by='Date').sum()
            dataframe_total[crypto]=dict(zip(temp.index,temp['Quantities']))
    
        historical_positions=pd.DataFrame(dataframe_total).sort_index()
        historical_positions=historical_positions.groupby(historical_positions.index).sum()
        historical_positions.index=historical_positions.index.round('d')
        historical_positions=historical_positions.groupby(historical_positions.index).sum().cumsum()
    
        return historical_positions


# In[ ]:




