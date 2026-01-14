"""
Backend configuration file
Extends root config.py with backend-specific settings
"""
import sys
from pathlib import Path

# Add root directory to Python path to import root config
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

# Import all settings from root config
from config import *

# Backend-specific settings
API_V1_PREFIX = "/api/v1"
API_TITLE = "Risk Management API"
API_VERSION = "1.0.0"
API_DESCRIPTION = "Cryptocurrency Portfolio Management Backend"

# WebSocket settings
WS_HEARTBEAT_INTERVAL = 30  # seconds
WS_PRICE_UPDATE_INTERVAL = 5  # seconds

# Cache settings
CACHE_DEFAULT_TTL = 300  # seconds (5 minutes)
CACHE_MARKET_CAP_TTL = 300  # 5 minutes
CACHE_PRICES_TTL = 3600  # 1 hour
CACHE_RETURNS_TTL = 3600  # 1 hour
CACHE_METRICS_TTL = 3600  # 1 hour
CACHE_INVENTORY_TTL = 30  # 30 seconds

# Binance API rate limiting
BINANCE_RATE_LIMIT_CALLS = 1200  # requests per period
BINANCE_RATE_LIMIT_PERIOD = 60  # seconds (1 minute)

# CORS settings
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
