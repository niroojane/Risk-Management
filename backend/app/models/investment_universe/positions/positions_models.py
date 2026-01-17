"""Position entities Domain objects for position data"""
from datetime import datetime
from pydantic import BaseModel, Field


class Position(BaseModel):
    """Position at a specific point in time"""
    date: datetime = Field(..., description="Position date")
    symbol: str = Field(..., description="Trading symbol")
    position: float = Field(..., description="Position value in quote asset", ge=0)
