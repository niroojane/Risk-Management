"""
Custom exceptions and exception handlers for the Risk Management API
"""
from datetime import datetime
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger(__name__)


# Custom Exception Classes
class RiskManagementException(Exception):
    """Base exception for all custom errors"""
    def __init__(self, message: str, detail: str = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class ExternalAPIError(RiskManagementException):
    """Raised when external API call fails (Binance, GitHub, etc.)"""
    pass


class BinanceAPIError(ExternalAPIError):
    """Raised when Binance API returns an error"""
    pass


class DataValidationError(RiskManagementException):
    """Raised when input data validation fails"""
    pass


class CacheError(RiskManagementException):
    """Raised when cache operations fail"""
    pass


class RateLimitError(RiskManagementException):
    """Raised when rate limit is exceeded"""
    pass


class ServiceUnavailableError(RiskManagementException):
    """Raised when a required service is not available or configured"""
    pass


# Exception Handlers
async def binance_api_exception_handler(request: Request, exc: BinanceAPIError):
    """Handle Binance API errors"""
    logger.error(f"Binance API error on {request.url.path}: {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "error": "BinanceAPIError",
            "message": exc.message,
            "detail": exc.detail or "Failed to fetch data from Binance API",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def data_validation_exception_handler(request: Request, exc: DataValidationError):
    """Handle data validation errors"""
    logger.warning(f"Data validation error on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "DataValidationError",
            "message": exc.message,
            "detail": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def cache_exception_handler(request: Request, exc: CacheError):
    """Handle cache errors"""
    logger.error(f"Cache error on {request.url.path}: {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "CacheError",
            "message": exc.message,
            "detail": exc.detail or "Internal cache error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitError):
    """Handle rate limit errors"""
    logger.warning(f"Rate limit exceeded on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "RateLimitError",
            "message": exc.message,
            "detail": exc.detail or "Rate limit exceeded, please try again later",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI validation errors"""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "detail": exc.errors(),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def service_unavailable_exception_handler(request: Request, exc: ServiceUnavailableError):
    """Handle service unavailable errors"""
    logger.warning(f"Service unavailable on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "ServiceUnavailableError",
            "message": exc.message,
            "detail": exc.detail or "Required service is not available",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all other unhandled exceptions"""
    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "detail": str(exc) if logger.level == logging.DEBUG else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


def setup_exception_handlers(app):
    """Register all exception handlers with the FastAPI app"""
    app.add_exception_handler(BinanceAPIError, binance_api_exception_handler)
    app.add_exception_handler(DataValidationError, data_validation_exception_handler)
    app.add_exception_handler(CacheError, cache_exception_handler)
    app.add_exception_handler(RateLimitError, rate_limit_exception_handler)
    app.add_exception_handler(ServiceUnavailableError, service_unavailable_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
