"""Common domain types and enums Reusable domain types for the entire application"""
from enum import Enum


class TimeInterval(str, Enum):
    """Supported time intervals"""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"


class QuoteAsset(str, Enum):
    """Supported quote assets"""
    USDT = "USDT"
    BUSD = "BUSD"
    BTC = "BTC"
    ETH = "ETH"


class ReturnType(str, Enum):
    """Return calculation types"""
    SIMPLE = "simple"
    LOGARITHMIC = "log"
