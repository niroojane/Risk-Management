"""Transform Binance account snapshot data"""
from typing import List, Dict, Any
from datetime import datetime

from ....schemas.external.binance import BinanceAccountSnapshotDTO


class BalanceTransformer:
    """Transforms account snapshot data from Binance API"""

    @staticmethod
    def snapshot_to_dict(snapshot_dto: BinanceAccountSnapshotDTO) -> List[Dict[str, Any]]:
        """Convert snapshot DTO to list of dicts with balances by date"""
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

        return snapshots_data

    @staticmethod
    def snapshots_to_quantities_dict(
        snapshots: List[Dict[str, Any]],
        quote: str = "USDT"
    ) -> Dict[str, Dict[datetime, float]]:
        """Convert snapshots to nested dict: {symbol: {date: quantity}}"""
        quantities_dict = {}

        for snapshot in snapshots:
            date = datetime.fromisoformat(snapshot["date"]).date()
            for balance in snapshot["balances"]:
                symbol = balance["asset"] + quote
                if symbol not in quantities_dict:
                    quantities_dict[symbol] = {}
                quantities_dict[symbol][date] = balance["total"]

        return quantities_dict
