"""Transform Binance kline data to various formats"""
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd

from ....schemas.external.binance import BinanceKlineDTO


class KlineTransformer:
    """Transforms raw kline data from Binance API"""

    @staticmethod
    def to_dataframe(klines: List[List], symbol: str) -> pd.DataFrame:
        """Convert raw klines to DataFrame with Close prices indexed by date"""
        columns = [
            'Open Time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close Time', 'Quote Asset Volume', 'Number of Trades',
            'TB Base Volume', 'TB Quote Volume', 'Ignore'
        ]

        df = pd.DataFrame(klines, columns=columns)
        df['Close Time'] = pd.to_datetime(df['Close Time'], unit='ms')
        df = df.set_index('Close Time')
        df['Close'] = df['Close'].astype(float)

        return df[['Close']].rename(columns={'Close': symbol})

    @staticmethod
    def to_dto_list(klines: List[List]) -> List[BinanceKlineDTO]:
        """Convert raw klines to list of DTOs"""
        return [BinanceKlineDTO.from_array(kline) for kline in klines]

    @staticmethod
    def to_dict_by_date(klines: List[BinanceKlineDTO]) -> Dict[str, float]:
        """Convert DTOs to dict keyed by date with Close prices"""
        return {
            datetime.fromtimestamp(k.Close_Time / 1000).date(): float(k.Close)
            for k in klines
        }

    @staticmethod
    def dict_to_dict_by_date(klines: List[Dict[str, Any]]) -> Dict[str, float]:
        """Convert dict klines to dict keyed by date with Close prices"""
        return {
            datetime.fromtimestamp(k['Close_Time'] / 1000).date(): float(k['Close'])
            for k in klines
        }

    @staticmethod
    def merge_symbols_to_dataframe(
        symbols_klines: Dict[str, List[List]]
    ) -> pd.DataFrame:
        """Merge multiple symbols' klines into single DataFrame"""
        price_data = pd.DataFrame()

        for symbol, klines in symbols_klines.items():
            if symbol == 'USDTUSDT':
                price_data[symbol] = 1
                continue

            if klines:
                df = KlineTransformer.to_dataframe(klines, symbol)
                price_data[symbol] = df[symbol]

        # Standardize date format
        if not price_data.empty:
            price_data.index = pd.to_datetime(price_data.index).strftime('%Y-%m-%d')

        return price_data
