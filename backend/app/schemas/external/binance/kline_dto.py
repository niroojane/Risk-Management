from typing import List, Any
from pydantic import BaseModel, Field, field_validator


class BinanceKlineDTO(BaseModel):
    """Raw kline/candlestick data from Binance API

    Binance returns klines as arrays of 12 elements:
    [
        Open_Time,
        Open,
        High,
        Low,
        Close,
        Volume,
        Close_Time,
        Quote_Asset_Volume,
        Number_of_Trades,
        Taker_Buy_Base_Volume,
        Taker_Buy_Quote_Volume,
        Ignore
    ]
    """

    Open_Time: int = Field(..., description="Kline open time (timestamp in ms)")
    Open: str = Field(..., description="Opening price")
    High: str = Field(..., description="Highest price")
    Low: str = Field(..., description="Lowest price")
    Close: str = Field(..., description="Closing price")
    Volume: str = Field(..., description="Base asset volume")
    Close_Time: int = Field(..., description="Kline close time (timestamp in ms)")
    Quote_Asset_Volume: str = Field(..., description="Quote asset volume")
    Number_of_Trades: int = Field(..., description="Number of trades")
    Taker_Buy_Base_Volume: str = Field(..., alias="TB_Base_Volume", description="Taker buy base asset volume")
    Taker_Buy_Quote_Volume: str = Field(..., alias="TB_Quote_Volume", description="Taker buy quote asset volume")
    Ignore: str = Field(..., description="Unused field (always '0')")

    class Config:
        populate_by_name = True

    @classmethod
    def from_array(cls, data: List[Any]) -> "BinanceKlineDTO":
        """Create BinanceKlineDTO from array format

        Args:
            data: Array of 12 elements from Binance API

        Returns:
            BinanceKlineDTO instance
        """
        if len(data) != 12:
            raise ValueError(f"Expected 12 elements, got {len(data)}")

        return cls(
            Open_Time=data[0],
            Open=data[1],
            High=data[2],
            Low=data[3],
            Close=data[4],
            Volume=data[5],
            Close_Time=data[6],
            Quote_Asset_Volume=data[7],
            Number_of_Trades=data[8],
            Taker_Buy_Base_Volume=data[9],
            Taker_Buy_Quote_Volume=data[10],
            Ignore=data[11],
        )
