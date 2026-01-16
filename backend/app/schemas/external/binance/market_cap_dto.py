from pydantic import BaseModel, Field

class BinanceMarketCapDTO(BaseModel): 
    """Raw market cap data from Binance API"""

    Ticker: str = Field(..., description="Trading pair symbol (e.g., BTCUSDT)")
    Long_name: str = Field(..., alias="Long name", description="Full asset name")
    Short_Name: str = Field(..., alias="Short Name", description="Base asset symbol")
    Quote_Short_Name: str = Field(..., alias="Quote Short Name", description="Quote asset symbol")
    Close: float = Field(..., description="Current closing price", gt=0)
    Supply: float = Field(..., description="Circulating supply", ge=0)
    Market_Cap: float = Field(..., alias="Market Cap", description="Market capitalization", ge=0)

    class Config:
        populate_by_name = True
