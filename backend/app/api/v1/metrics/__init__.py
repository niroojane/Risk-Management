"""Risk Metrics Router Aggregator"""
from fastapi import APIRouter

from .var import router as var_router

router = APIRouter(prefix="/metrics", tags=["Risk Metrics"])

router.include_router(var_router)

__all__ = ["router"]
