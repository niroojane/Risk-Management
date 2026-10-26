# Copyright (c) 2025 Niroojane Selvam
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""Binance Spot API: market caps, daily closes, account snapshots, trade pair prices.

The module functions hold the logic shared by the notebooks (`BinanceAPI`) and the web app backend,
which calls them in worker threads behind its own cache and rate limiter.
"""

import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count

import pandas as pd
import requests
from binance.spot import Spot

logger = logging.getLogger(__name__)

MARKET_CAP_URL = "https://www.binance.com/bapi/asset/v2/public/asset-service/product/get-products"
KLINE_COLUMNS = ['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time', 'Quote Asset Volume',
                 'Number of Trades', 'TB Base Volume', 'TB Quote Volume', 'Ignore']
CASH_TICKER = 'USDTUSDT'


def daterange(start_date, end_date,interval=30):
    for n in range(0,int((end_date - start_date).days),interval):
        yield start_date + datetime.timedelta(n)


# ---------------------------------------------------------------------- shared functions

def get_market_cap(quote="USDT"):
    """Binance products quoted in `quote`, largest market cap first (public endpoint, no key)"""
    resp = requests.get(MARKET_CAP_URL)

    market_cap=pd.DataFrame(resp.json()['data'])
    market_cap=market_cap[market_cap['q']==quote]

    market_cap=market_cap[['an','qn','s','b','q','c','cs']]
    market_cap['c']=market_cap['c'].astype(float)

    market_cap.columns=['Long name','Quote Name','Ticker','Short Name','Quote Short Name','Close','Supply']
    market_cap['Market Cap']=market_cap['Close']*market_cap['Supply']

    return market_cap.sort_values(by='Market Cap',ascending=False)


def klines_to_closes(klines):
    """Daily klines -> close prices indexed by 'YYYY-MM-DD' (the UTC day of the close)"""
    data = pd.DataFrame(klines, columns=KLINE_COLUMNS)
    index = pd.to_datetime(data['Close Time'], unit='ms').dt.strftime('%Y-%m-%d')
    return pd.Series(data['Close'].astype(float).values, index=index.values)


def fetch_closes(spot, tickers, start_ms, end_ms=None):
    """Daily closes of `tickers` from `start_ms` (and up to `end_ms`), one column per ticker retrieved.

    USDTUSDT is 1, a ticker with no klines in the window is all NaN, and a ticker Binance rejects
    is skipped with a warning.
    """
    closes = {}
    for ticker in tickers:
        if ticker == CASH_TICKER:
            closes[ticker] = None
            continue
        try:
            kwargs = {'startTime': start_ms} if end_ms is None else {'startTime': start_ms, 'endTime': end_ms}
            klines = spot.klines(ticker, "1d", **kwargs)
            closes[ticker] = klines_to_closes(klines) if klines else pd.Series(dtype=float)
        except Exception as e:
            logger.warning(f"{ticker} not retrieved: {e}")

    series = {t: s for t, s in closes.items() if s is not None}
    price = pd.concat(series, axis=1) if series else pd.DataFrame()
    if CASH_TICKER in closes:
        price[CASH_TICKER] = 1.0
    return price[[t for t in closes if t in price.columns]]


def snapshot_balances(snapshot):
    """Raw `account_snapshot` answer -> [{'date': 'YYYY-MM-DD', 'balances': [{asset, free, locked, total}]}].

    Binance takes each daily snapshot at 23:59:59 UTC, so the date is the UTC day.
    """
    days = []
    for vo in snapshot.get('snapshotVos', []):
        days.append({
            'date': pd.to_datetime(vo['updateTime'], unit='ms').strftime('%Y-%m-%d'),
            'balances': [
                {
                    'asset': b['asset'],
                    'free': b['free'],
                    'locked': b['locked'],
                    'total': float(b['free']) + float(b['locked']),
                }
                for b in vo['data']['balances']
            ],
        })
    return days


def pair_ticker(market):
    """USDT ticker that prices the quote asset of `market` (e.g. ETHBTC -> BTCUSDT)"""
    if market.endswith('USDT'):
        return market
    if market.endswith('TRY'):
        return 'USDT' + market[-3:]
    return market[-3:] + 'USDT'


def pair_price(spot, market, time_of_trade):
    """USDT price of the quote asset of `market` at `time_of_trade`, interpolated on 1-minute closes"""
    start = int(time_of_trade.round(freq='min').timestamp() - 60) * 1000
    klines = spot.klines(pair_ticker(market), interval='1m', startTime=start, limit=2)

    close_prev, close_next = float(klines[0][4]), float(klines[1][4])
    t_prev, t_next = pd.to_datetime(klines[0][6], unit='ms'), pd.to_datetime(klines[1][6], unit='ms')

    total_diff = (t_next - t_prev) / pd.Timedelta(minutes=1)
    weight_prev = (t_next - time_of_trade) / pd.Timedelta(minutes=1) / total_diff
    weight_next = (time_of_trade - t_prev) / pd.Timedelta(minutes=1) / total_diff

    price = close_prev * weight_prev + close_next * weight_next
    return 1 / price if market.endswith('TRY') else price


# ---------------------------------------------------------------------- notebook client

class BinanceAPI:

    def __init__(self,binance_api_key,binance_api_secret):

        self.binance_api_key=binance_api_key
        self.binance_api_secret=binance_api_secret

        self.binance_api=Spot(self.binance_api_key,self.binance_api_secret)

    def get_market_cap(self,quote="USDT"):

        return get_market_cap(quote)

    def get_price(self,ticker_list,date=None):

        # today at call time (a default in the signature would be fixed when the module loads)
        date=date or datetime.datetime.today()
        timestamp_sec=int((date-datetime.timedelta(1)).timestamp()*1000)

        price=fetch_closes(self.binance_api,list(ticker_list),timestamp_sec)
        price.index=pd.to_datetime(price.index).strftime('%Y-%m-%d')

        return price

    def get_price_threading(self,tickers,start_date):

        today = datetime.date.today()
        days_total = (today - start_date).days
        if days_total <= 0:
            print("Start date must be in the past.")
            return

        remaining = days_total % 500
        numbers_of_table = days_total // 500

        start_dt= datetime.datetime.combine(start_date, datetime.time())
        end_dates = [
                start_dt + datetime.timedelta(days=500 * i)
                for i in range(numbers_of_table + 1)
            ]

        end_dates.append(
            datetime.datetime.combine(
                today - datetime.timedelta(days=remaining),
                datetime.time()
            )
        )

        def fetch_prices(end_date):
            return self.get_price(tickers, end_date)

        price = None

        try:
            with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
                futures = [executor.submit(fetch_prices, d) for d in end_dates]

                for future in as_completed(futures):
                    data = future.result()

                    if price is None:
                        price = data
                    else:
                        price = price.combine_first(data)

        except Exception as e:
            print("❌ Error while fetching prices:", e)
            return

        price = price.sort_index()
        price = price[~price.index.duplicated(keep="first")]
        price.index = pd.to_datetime(price.index)

        return price

    def get_inventory(self):

        ptf=pd.DataFrame(self.binance_api.user_asset())
        ptf['Ticker']=ptf['asset']+"USDT"
        ptf=ptf.set_index('Ticker')

        price=self.get_price(ptf.index).T
        price.columns=['Price']

        data=pd.concat([price,ptf],axis=1)
        data['Price in USDT']=data['Price']*(data['free'].astype(float)+data['locked'].astype(float))

        inventory=pd.DataFrame(data['Price in USDT'])
        inventory['Weights']=inventory['Price in USDT']/inventory['Price in USDT'].sum()

        inventory.loc['Total']=inventory.sum()

        return inventory.sort_values(by='Weights',ascending=False)

    def get_positions_history(self,enddate=None):

        enddate=enddate or datetime.datetime.today()
        startdate=enddate-datetime.timedelta(30)
        timestamp_end = int(enddate.timestamp() * 1000)

        snapshot=self.binance_api.account_snapshot(type='SPOT',limit=30,endTime=timestamp_end)

        holdings={day['date']: {b['asset']: b['total'] for b in day['balances']}
                  for day in snapshot_balances(snapshot)}

        quantities=pd.DataFrame(holdings).T
        quantities.columns=quantities.columns+'USDT'

        prices=self.get_price(quantities.columns,startdate)
        prices=prices.loc[~prices.index.duplicated(keep='last')]

        positions = quantities * prices.loc[quantities.index]
        positions=positions.groupby(level=0).sum()

        return positions,quantities

    def get_trades(self,symbols):

            trades={}
            history=pd.DataFrame()

            for symbol in symbols:
                trades[symbol]=self.binance_api.my_trades(symbol=symbol)

            for key in trades:

                history=pd.concat([history,pd.DataFrame(trades[key])])

            history['time']=pd.to_datetime(history['time'],unit='ms')

            return history
