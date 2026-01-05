"""
Main FastAPI application entry point
Risk Management API for cryptocurrency portfolio management
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging

from .config import (
    API_TITLE,
    API_VERSION,
    API_DESCRIPTION,
    API_V1_PREFIX,
    CORS_ORIGINS,
)
from .core.logging_config import setup_logging
from .core.exceptions import setup_exception_handlers

# Setup logging
logger = setup_logging(log_level="INFO")

# Create FastAPI application
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup exception handlers
setup_exception_handlers(app)

# Note: Router will be added once api/router.py is created
# from .api.router import api_router
# app.include_router(api_router, prefix=API_V1_PREFIX)


@app.get("/health", tags=["Health"])
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


@app.get("/", tags=["Root"])
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


@app.on_event("startup")
async def startup_event():
    """
    Actions to perform on application startup
    """
    logger.info(f"{API_TITLE} v{API_VERSION} starting up...")
    logger.info(f"CORS origins: {CORS_ORIGINS}")
    # Future: Initialize cache, validate config, setup WebSocket manager


@app.on_event("shutdown")
async def shutdown_event():
    """
    Actions to perform on application shutdown
    """
    logger.info(f"{API_TITLE} shutting down...")
    # Future: Cleanup WebSocket connections, close cache


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
