"""API V1 Router Aggregator"""
from fastapi import APIRouter

from .status.health import router as health_router
from .investment_universe import router as investment_universe_router

# Create main v1 router
v1_router = APIRouter()

# Include all domain routers
v1_router.include_router(health_router)
v1_router.include_router(investment_universe_router)

__all__ = ["v1_router"]
