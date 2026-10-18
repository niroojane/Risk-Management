"""Public market data operations (market cap, exchange info)"""
import logging
from typing import List
from src import Binance_API as binance_api
from .binance_client import BinanceClient
from ...core.config import CACHE_MARKET_CAP_TTL
from ...schemas.universe import MarketCapItem

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

            market_cap = await self._client._run_in_executor(binance_api.get_market_cap, quote)

            items = []
            for _, row in market_cap.iterrows():
                try:
                    items.append(MarketCapItem(
                        symbol=row['Ticker'],
                        long_name=row['Long name'],
                        base_asset=row['Short Name'],
                        quote_asset=row['Quote Short Name'],
                        price=float(row['Close']),
                        supply=float(row['Supply']),
                        market_cap=float(row['Market Cap']),
                    ))
                except Exception as e:
                    logger.warning(f"Skipping invalid market cap item: {e}")
            return items

        return await self._client.fetch_with_cache(
            cache_key=cache_key,
            api_call=fetch,
            weight=40,
            ttl=CACHE_MARKET_CAP_TTL,
            use_cache=use_cache,
        )
