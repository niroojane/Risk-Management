"""Health and API information"""
from datetime import datetime

from fastapi import APIRouter

from app.core.config import API_TITLE, API_VERSION

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": API_VERSION,
        "service": API_TITLE,
    }


@router.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": f"Welcome to {API_TITLE}",
        "version": API_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }
