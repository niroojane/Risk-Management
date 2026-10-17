"""API V1 Router Aggregator"""
from fastapi import APIRouter

from .status.health import router as health_router
from .investment_universe import router as investment_universe_router
from .strategy import router as strategy_router
from .metrics import router as metrics_router
from .market_risk import router as market_risk_router
from .portfolio import router as portfolio_router
from .risk import router as risk_router
from .account import router as account_router
from .profile import router as profile_router

# Create main v1 router
v1_router = APIRouter()

# Include all domain routers
v1_router.include_router(health_router)
v1_router.include_router(investment_universe_router)
v1_router.include_router(strategy_router)
v1_router.include_router(metrics_router)
v1_router.include_router(market_risk_router)
v1_router.include_router(portfolio_router)
v1_router.include_router(risk_router)
v1_router.include_router(account_router)
v1_router.include_router(profile_router)

__all__ = ["v1_router"]
