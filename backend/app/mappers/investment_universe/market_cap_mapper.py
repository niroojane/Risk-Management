"""Market Cap Mapper Transforms raw Binance API data to MarketCapItem entities"""
from typing import List
from pydantic import ValidationError

from ...models.investment_universe import MarketCapItem
from ...schemas.external.binance import BinanceMarketCapDTO
from ...core import DataValidationError


class MarketCapMapper:
    """Stateless mapper for market cap data transformations"""

    @staticmethod
    def to_entity(raw_item: dict) -> MarketCapItem:
        """Transform a single raw Binance item to MarketCapItem entity"""
        try : 
            dto = BinanceMarketCapDTO(**raw_item)

            return MarketCapItem(
                symbol=dto.Ticker,
                long_name=dto.Long_name,
                base_asset=dto.Short_Name,
                quote_asset=dto.Quote_Short_Name,
                price=float(dto.Close),
                supply=float(dto.Supply),
                market_cap=float(dto.Market_Cap)
            ) 
        except (KeyError, ValueError, ValidationError) as e:
            raise DataValidationError(
                message=f"Failed to map market cap data for symbol {raw_item.get('Ticker', 'UNKNOWN')}",
                detail=str(e)
            )
            

    @staticmethod
    def to_entities(raw_data: List[dict], limit: int = None) -> List[MarketCapItem]:
        """Transform a list of raw Binance items to MarketCapItem entities"""
        data_to_transform = raw_data[:limit] if limit else raw_data
        return [MarketCapMapper.to_entity(item) for item in data_to_transform]
