"""Backend configuration using Pydantic Settings"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    API_TITLE: str = "Risk Management API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Cryptocurrency Portfolio Management Backend"

    # Binance API
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""
    BINANCE_RATE_LIMIT_CALLS: int = 1200
    BINANCE_RATE_LIMIT_PERIOD: int = 60

    # Cache TTLs (seconds)
    CACHE_DEFAULT_TTL: int = 300
    CACHE_MARKET_CAP_TTL: int = 300
    CACHE_PRICES_TTL: int = 3600
    CACHE_RETURNS_TTL: int = 3600
    CACHE_METRICS_TTL: int = 3600
    CACHE_INVENTORY_TTL: int = 30

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_PRICE_UPDATE_INTERVAL: int = 5

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # GitHub (optional)
    GITHUB_TOKEN: str = ""
    GITHUB_REPO_OWNER: str = ""
    GITHUB_REPO_NAME: str = "Risk-Management"
    GITHUB_BRANCH: str = "start-web-project"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    @property
    def is_binance_configured(self) -> bool:
        """Check if Binance API credentials are configured"""
        return bool(self.BINANCE_API_KEY and self.BINANCE_API_SECRET)


settings = Settings()

# Export individual settings for backwards compatibility
API_V1_PREFIX = settings.API_V1_PREFIX
API_TITLE = settings.API_TITLE
API_VERSION = settings.API_VERSION
API_DESCRIPTION = settings.API_DESCRIPTION

BINANCE_API_KEY = settings.BINANCE_API_KEY
BINANCE_API_SECRET = settings.BINANCE_API_SECRET
BINANCE_RATE_LIMIT_CALLS = settings.BINANCE_RATE_LIMIT_CALLS
BINANCE_RATE_LIMIT_PERIOD = settings.BINANCE_RATE_LIMIT_PERIOD

CACHE_DEFAULT_TTL = settings.CACHE_DEFAULT_TTL
CACHE_MARKET_CAP_TTL = settings.CACHE_MARKET_CAP_TTL
CACHE_PRICES_TTL = settings.CACHE_PRICES_TTL
CACHE_RETURNS_TTL = settings.CACHE_RETURNS_TTL
CACHE_METRICS_TTL = settings.CACHE_METRICS_TTL
CACHE_INVENTORY_TTL = settings.CACHE_INVENTORY_TTL

WS_HEARTBEAT_INTERVAL = settings.WS_HEARTBEAT_INTERVAL
WS_PRICE_UPDATE_INTERVAL = settings.WS_PRICE_UPDATE_INTERVAL

CORS_ORIGINS = settings.CORS_ORIGINS

GITHUB_TOKEN = settings.GITHUB_TOKEN
GITHUB_REPO_OWNER = settings.GITHUB_REPO_OWNER
GITHUB_REPO_NAME = settings.GITHUB_REPO_NAME
GITHUB_BRANCH = settings.GITHUB_BRANCH
