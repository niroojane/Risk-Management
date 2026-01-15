"""Market Cap Mapper Transforms raw Binance API data to MarketCapItem entities"""
from typing import List

from ...models.investment_universe import MarketCapItem


class MarketCapMapper:
    """Stateless mapper for market cap data transformations"""

    @staticmethod
    def to_entity(raw_item: dict) -> MarketCapItem:
        """Transform a single raw Binance item to MarketCapItem entity"""
        return MarketCapItem(
            symbol=raw_item["Ticker"],
            long_name=raw_item["Long name"],
            base_asset=raw_item["Short Name"],
            quote_asset=raw_item["Quote Short Name"],
            price=float(raw_item["Close"]),
            supply=float(raw_item["Supply"]),
            market_cap=float(raw_item["Market Cap"])
        )

    @staticmethod
    def to_entities(raw_data: List[dict], limit: int = None) -> List[MarketCapItem]:
        """Transform a list of raw Binance items to MarketCapItem entities"""
        data_to_transform = raw_data[:limit] if limit else raw_data
        return [MarketCapMapper.to_entity(item) for item in data_to_transform]
