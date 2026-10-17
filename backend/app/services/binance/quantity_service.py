"""Quantity/balance operations (account snapshots)"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .binance_client import BinanceClient
from .transformers import BalanceTransformer
from ...core.config import CACHE_PRICES_TTL
from ...schemas.external.binance import BinanceAccountSnapshotDTO

logger = logging.getLogger(__name__)


class QuantityService:
    """Handles account balance and quantity data"""

    def __init__(self, client: BinanceClient):
        self._client = client

    async def get_historical_quantities(
        self,
        end_date: Optional[datetime] = None,
        limit: int = 30,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Get historical account quantities from Binance snapshots

        TODO: Retrieve quantities data from database instead of Binance API
        """
        if end_date is None:
            end_date = datetime.today()

        # Clamp limit between 7 and 365 days
        limit = max(7, min(365, limit))
        cache_key = f"historical_quantities:{end_date.date()}:{limit}"

        async def fetch():
            logger.info(f"Fetching historical quantities (end_date={end_date.date()}, limit={limit})")

            timestamp_end = int(end_date.timestamp() * 1000)

            raw_snapshot = await self._client._run_in_executor(
                self._client.spot.account_snapshot,
                type='SPOT',
                limit=limit,
                endTime=timestamp_end
            )

            snapshot_dto = BinanceAccountSnapshotDTO(**raw_snapshot)
            snapshots_data = BalanceTransformer.snapshot_to_dict(snapshot_dto)

            return {
                "end_date": end_date.isoformat(),
                "limit": limit,
                "data": snapshots_data,
                "count": len(snapshots_data),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return await self._client.fetch_with_cache(
            cache_key=cache_key,
            api_call=fetch,
            weight=2,
            ttl=CACHE_PRICES_TTL,
            use_cache=use_cache,
        )
