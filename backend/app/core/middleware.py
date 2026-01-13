"""
Middleware configuration
Centralizes all middleware setup for the FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from ..config import CORS_ORIGINS

logger = logging.getLogger(__name__)


def setup_middlewares(app: FastAPI) -> None:
    """
    Configure all application middlewares

    Args:
        app: FastAPI application instance
    """
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info(f"CORS middleware configured with origins: {CORS_ORIGINS}")

    # Future middlewares can be added here:
    # - Rate limiting middleware
    # - Authentication middleware
    # - Request ID middleware
    # - Compression middleware
