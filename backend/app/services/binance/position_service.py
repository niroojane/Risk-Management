"""Position operations (prices, quantities, and positions calculation)"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

from .binance_service import BinanceClient
from ...core.config import CACHE_PRICES_TTL
from ...schemas.external.binance import BinanceKlineDTO, BinanceAccountSnapshotDTO

logger = logging.getLogger(__name__)


class PositionService:
    """Handles position-related operations (prices, quantities, positions)"""

    def __init__(self, client: BinanceClient):
        self._client = client

    async def get_historical_prices(
        self,
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Get historical kline/price data for symbols"""
        if end_date is None:
            end_date = datetime.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        cache_key = f"historical_prices:{','.join(sorted(symbols))}:{start_date.date()}:{end_date.date()}"

        async def fetch():
            logger.info(
                f"Fetching historical prices for {len(symbols)} symbols "
                f"({start_date.date()} to {end_date.date()})"
            )

            timestamp_sec = int((end_date - timedelta(1)).timestamp() * 1000)

            async def fetch_symbol_klines(symbol: str):
                try:
                    raw_klines = await self._client._run_in_executor(
                        self._client.api.binance_api.klines,
                        symbol,
                        "1d",
                        startTime=timestamp_sec
                    )

                    klines = [BinanceKlineDTO.from_array(kline) for kline in raw_klines]

                    if start_date:
                        klines = [
                            k for k in klines
                            if datetime.fromtimestamp(k.Close_Time / 1000, tz=timezone.utc) >= start_date
                        ]

                    return {
                        "symbol": symbol,
                        "klines": [k.model_dump() for k in klines]
                    }

                except Exception as e:
                    logger.warning(f"Failed to fetch prices for {symbol}: {e}")
                    return None

            results = await asyncio.gather(*[fetch_symbol_klines(symbol) for symbol in symbols])
            all_prices = [result for result in results if result is not None]

            return {
                "symbols": symbols,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "data": all_prices,
                "count": len(all_prices),
                "timestamp": datetime.utcnow().isoformat(),
            }

        return await self._client.fetch_with_cache(
            cache_key=cache_key,
            api_call=fetch,
            weight=len(symbols),
            ttl=CACHE_PRICES_TTL,
            use_cache=use_cache,
        )

    async def get_historical_quantities(
        self,
        end_date: Optional[datetime] = None,
        limit: int = 30,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Get historical account quantities from Binance snapshots"""
        if end_date is None:
            end_date = datetime.today()

        limit = max(7, min(30, limit))
        cache_key = f"historical_quantities:{end_date.date()}:{limit}"

        async def fetch():
            logger.info(f"Fetching historical quantities (end_date={end_date.date()}, limit={limit})")

            timestamp_end = int(end_date.timestamp() * 1000)

            raw_snapshot = await self._client._run_in_executor(
                self._client.api.binance_api.account_snapshot,
                type='SPOT',
                limit=limit,
                endTime=timestamp_end
            )

            snapshot_dto = BinanceAccountSnapshotDTO(**raw_snapshot)

            snapshots_data = []
            for snapshot_vo in snapshot_dto.snapshotVos:
                date = datetime.fromtimestamp(snapshot_vo.updateTime / 1000)
                balances = [
                    {
                        "asset": balance.asset,
                        "free": balance.free,
                        "locked": balance.locked,
                        "total": float(balance.free) + float(balance.locked)
                    }
                    for balance in snapshot_vo.data.balances
                ]

                snapshots_data.append({
                    "date": date.isoformat(),
                    "balances": balances
                })

            return {
                "end_date": end_date.isoformat(),
                "limit": limit,
                "data": snapshots_data,
                "count": len(snapshots_data),
                "timestamp": datetime.utcnow().isoformat(),
            }

        return await self._client.fetch_with_cache(
            cache_key=cache_key,
            api_call=fetch,
            weight=2,
            ttl=CACHE_PRICES_TTL,
            use_cache=use_cache,
        )

    async def get_historical_positions(
        self,
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Calculate historical positions by multiplying quantities by prices"""
        cache_key = f"historical_positions:{','.join(sorted(symbols))}:{start_date}:{end_date}"

        async def fetch():
            logger.info(f"Calculating historical positions for {len(symbols)} symbols")

            prices_data = await self.get_historical_prices(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                use_cache=use_cache
            )

            quantities_data = await self.get_historical_quantities(
                end_date=end_date,
                use_cache=use_cache
            )

            # Build prices dict: {symbol: {date: price}}
            prices_dict = {}
            for symbol_data in prices_data["data"]:
                symbol = symbol_data["symbol"]
                prices_dict[symbol] = {
                    datetime.fromtimestamp(k["Close_Time"] / 1000).date(): float(k["Close"])
                    for k in symbol_data["klines"]
                }

            # Build quantities dict: {symbol: {date: quantity}}
            quantities_dict = {}
            for snapshot in quantities_data["data"]:
                date = datetime.fromisoformat(snapshot["date"]).date()
                for balance in snapshot["balances"]:
                    symbol = balance["asset"] + "USDT"
                    if symbol not in quantities_dict:
                        quantities_dict[symbol] = {}
                    quantities_dict[symbol][date] = balance["total"]

            # Calculate positions: quantity × price
            positions = []
            for symbol in symbols:
                if symbol not in prices_dict or symbol not in quantities_dict:
                    continue

                for date in sorted(set(prices_dict[symbol].keys()) & set(quantities_dict[symbol].keys())):
                    position_value = quantities_dict[symbol][date] * prices_dict[symbol][date]
                    positions.append({
                        "date": datetime.combine(date, datetime.min.time()).isoformat(),
                        "symbol": symbol,
                        "position": round(position_value, 2)
                    })

            return {
                "symbols": symbols,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "data": positions,
                "count": len(positions),
                "timestamp": datetime.utcnow().isoformat(),
            }

        return await self._client.fetch_with_cache(
            cache_key=cache_key,
            api_call=fetch,
            weight=len(symbols) + 2,
            ttl=CACHE_PRICES_TTL,
            use_cache=use_cache,
        )
