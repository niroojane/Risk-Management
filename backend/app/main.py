"""
Main FastAPI application entry point
Risk Management API for cryptocurrency portfolio management
"""
from fastapi import FastAPI

from .core.config import API_TITLE, API_VERSION, API_DESCRIPTION, API_V1_PREFIX
from .core.logging_config import setup_logging
from .core.exceptions import setup_exception_handlers
from .core.middleware import setup_middlewares
from .core.events import startup_event, shutdown_event
from .api.v1.health import router as health_router
from .api.v1.investment_universe import router as investment_universe_router

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

# Setup middlewares
setup_middlewares(app)

# Setup exception handlers
setup_exception_handlers(app)

# Include routers
app.include_router(health_router)
app.include_router(investment_universe_router, prefix=API_V1_PREFIX)

# Register lifecycle events
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
