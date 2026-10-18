"""All routes of the API, one module per domain (mounted under /api/v1 in app/main.py)"""
from fastapi import APIRouter

from . import account, health, market_risk, portfolio, profile, risk, strategy, universe

v1_router = APIRouter()
for router in (health.router, universe.router, strategy.router, portfolio.router, risk.router,
               risk.var_router, market_risk.router, account.router, profile.router):
    v1_router.include_router(router)

__all__ = ["v1_router"]
