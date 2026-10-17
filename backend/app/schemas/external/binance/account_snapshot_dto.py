from typing import List
from pydantic import BaseModel, Field


class BinanceBalanceDTO(BaseModel):
    """Single asset balance in account snapshot"""

    asset: str = Field(..., description="Asset symbol (e.g., BTC, ETH)")
    free: str = Field(..., description="Available balance")
    locked: str = Field(..., description="Locked balance")

    class Config:
        populate_by_name = True


class BinanceSnapshotDataDTO(BaseModel):
    """Data section of account snapshot"""

    balances: List[BinanceBalanceDTO] = Field(..., description="List of asset balances")
    totalAssetOfBtc: str = Field(..., description="Total account value in BTC")

    class Config:
        populate_by_name = True


class BinanceSnapshotVoDTO(BaseModel):
    """Single snapshot entry"""

    data: BinanceSnapshotDataDTO = Field(..., description="Snapshot data")
    type: str = Field(..., description="Account type (spot, margin, futures)")
    updateTime: int = Field(..., description="Snapshot timestamp in milliseconds")

    class Config:
        populate_by_name = True


class BinanceAccountSnapshotDTO(BaseModel):
    """Complete account snapshot response from Binance API

    Response structure:
    {
        "code": 200,
        "msg": "",
        "snapshotVos": [
            {
                "data": {
                    "balances": [
                        {"asset": "BTC", "free": "0.09905021", "locked": "0.00000000"},
                        {"asset": "USDT", "free": "1.89109409", "locked": "0.00000000"}
                    ],
                    "totalAssetOfBtc": "0.09942700"
                },
                "type": "spot",
                "updateTime": 1576281599000
            }
        ]
    }
    """

    code: int = Field(..., description="Response code (200 for success)")
    msg: str = Field(..., description="Response message")
    snapshotVos: List[BinanceSnapshotVoDTO] = Field(..., description="List of account snapshots")

    class Config:
        populate_by_name = True
