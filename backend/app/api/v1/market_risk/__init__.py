"""Market Risk Router Aggregator"""
from fastapi import APIRouter

from .views import router as views_router

router = APIRouter(prefix="/market-risk", tags=["Market Risk"])

router.include_router(views_router)

__all__ = ["router"]
