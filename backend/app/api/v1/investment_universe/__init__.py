"""Investment Universe Router Aggregator"""
from fastapi import APIRouter

from .market_cap import router as market_cap_router
from .prices import router as prices_router
from .asset_metrics import router as asset_metrics_router

# Create main investment universe router
router = APIRouter(prefix="/investment-universe", tags=["Investment Universe"])

# Include all sub-routers (remove their individual prefix since parent has it)
router.include_router(market_cap_router, prefix="", tags=[])
router.include_router(prices_router, prefix="", tags=[])
router.include_router(asset_metrics_router, prefix="", tags=[])

__all__ = ["router"]
