"""Quantity entities Domain objects for quantity data"""
from datetime import datetime
from pydantic import BaseModel, Field


class Quantity(BaseModel):
    """Asset quantity at a specific point in time"""
    date: datetime = Field(..., description="Snapshot date")
    symbol: str = Field(..., description="Trading symbol")
    quantity: float = Field(..., description="Quantity in base asset", ge=0)
