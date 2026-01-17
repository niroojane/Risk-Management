"""Investment Universe Router Aggregator"""
from fastapi import APIRouter

from .market_cap import router as market_cap_router
from .positions import router as positions_router

# Create main investment universe router
router = APIRouter(prefix="/investment-universe", tags=["Investment Universe"])

# Include all sub-routers (remove their individual prefix since parent has it)
router.include_router(market_cap_router, prefix="", tags=[])
router.include_router(positions_router, prefix="", tags=[])

__all__ = ["router"]
