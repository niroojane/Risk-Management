"""Real portfolio: positioning vs the model"""
from typing import Dict

from pydantic import BaseModel, Field, field_validator

from app.schemas.workspace import upper_keys


class PositioningRequest(BaseModel):
    """Current holdings vs. the model allocation"""
    model_weights: Dict[str, float] = Field(default_factory=dict, description="Model weights by symbol")

    @field_validator('model_weights')
    @classmethod
    def normalize(cls, v):
        return upper_keys(v)
