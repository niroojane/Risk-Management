"""Strategy Router Aggregator"""
from fastapi import APIRouter

from .optimization import router as optimization_router

router = APIRouter(prefix="/strategy", tags=["Strategy"])

router.include_router(optimization_router)

__all__ = ["router"]
