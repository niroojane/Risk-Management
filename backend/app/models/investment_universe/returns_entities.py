"""Returns entities Domain objects for return data"""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field

from app.common import ReturnType


class ReturnDataPoint(BaseModel):
    """Single return data point"""
    timestamp: datetime = Field(..., description="Return timestamp")
    return_value: float = Field(..., description="Return value")


class AssetReturns(BaseModel):
    """Return data for a single asset"""
    symbol: str = Field(..., description="Trading symbol")
    return_type: ReturnType = Field(..., description="Return calculation type used")
    returns: List[ReturnDataPoint] = Field(..., description="Historical returns")
