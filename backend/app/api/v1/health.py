"""
Health and system status endpoints
"""
from fastapi import APIRouter
from datetime import datetime

from ...core.config import API_VERSION, API_TITLE

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint

    Returns:
        dict: API health status and metadata
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": API_VERSION,
        "service": API_TITLE,
    }


@router.get("/")
async def root():
    """
    Root endpoint with API information

    Returns:
        dict: API welcome message and documentation links
    """
    return {
        "message": f"Welcome to {API_TITLE}",
        "version": API_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }
