"""Public market data operations (market cap, exchange info)"""
import logging
from typing import List
from datetime import datetime, timezone
import pandas as pd
import requests

from .binance_client import BinanceClient
from ...core.config import CACHE_MARKET_CAP_TTL
from ...models.investment_universe import MarketCapItem
from ...schemas.external.binance import BinanceMarketCapDTO
from ...core import DataValidationError

logger = logging.getLogger(__name__)


class MarketDataService:
    """Handles public Binance market data endpoints"""

    def __init__(self, client: BinanceClient):
        self._client = client

    async def get_market_cap(
        self, quote: str = "USDT", use_cache: bool = True
    ) -> List[MarketCapItem]:
        """Get market capitalization for all trading pairs"""
        cache_key = f"market_cap:{quote}"

        async def fetch():
            logger.info(f"Fetching market cap from Binance public API (quote={quote})")

            resp = await self._client._run_in_executor(
                requests.get,
                "https://www.binance.com/bapi/asset/v2/public/asset-service/product/get-products"
            )

            market_cap = pd.DataFrame(resp.json()['data'])
            market_cap = market_cap[market_cap['q'] == quote]
            market_cap = market_cap[['an', 'qn', 's', 'b', 'q', 'c', 'cs']]
            market_cap['c'] = market_cap['c'].astype(float)

            market_cap.columns = [
                'Long name', 'Quote Name', 'Ticker', 'Short Name',
                'Quote Short Name', 'Close', 'Supply'
            ]
            market_cap['Market Cap'] = market_cap['Close'] * market_cap['Supply']
            market_cap = market_cap.sort_values(by='Market Cap', ascending=False)

            # Convert DataFrame to list of MarketCapItem instances
            items = []
            for _, row in market_cap.iterrows():
                try:
                    # Create DTO first for validation
                    dto = BinanceMarketCapDTO(
                        Long_name=row['Long name'],
                        Quote_Name=row['Quote Name'],
                        Ticker=row['Ticker'],
                        Short_Name=row['Short Name'],
                        Quote_Short_Name=row['Quote Short Name'],
                        Close=row['Close'],
                        Supply=row['Supply'],
                        Market_Cap=row['Market Cap']
                    )

                    # Convert to domain model
                    items.append(MarketCapItem(
                        symbol=dto.Ticker,
                        long_name=dto.Long_name,
                        base_asset=dto.Short_Name,
                        quote_asset=dto.Quote_Short_Name,
                        price=float(dto.Close),
                        supply=float(dto.Supply),
                        market_cap=float(dto.Market_Cap)
                    ))
                except Exception as e:
                    logger.warning(f"Skipping invalid market cap item: {e}")
                    continue

            return items

        return await self._client.fetch_with_cache(
            cache_key=cache_key,
            api_call=fetch,
            weight=40,
            ttl=CACHE_MARKET_CAP_TTL,
            use_cache=use_cache,
        )
