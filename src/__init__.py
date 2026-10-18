"""Shared library of the Risk Management apps: the notebooks, Streamlit and the web app backend.

The data clients and modules below load on first use, so importing one part (e.g.
`src.Workspace` in the web app) doesn't import Binance, GitHub or Yahoo clients.
"""
import importlib

# name -> (module, attribute) for `from src import BinanceAPI` and friends
_EXPORTS = {
    "BinanceAPI": ("Binance_API", "BinanceAPI"),
    "PnL": ("PnL_Computation", "PnL"),
    "get_close": ("Stock_Data", "get_close"),
    "GitHub": ("Git", "GitHub"),
}
_MODULES = {"RiskMetrics", "Rebalancing", "Metrics"}

# Define what gets imported with: from src import *
__all__ = [
    "BinanceAPI",
    "PnL",
    "get_close",
    "GitHub",
    "RiskMetrics",
    "Rebalancing",
    "Metrics",
]


def __getattr__(name):
    if name in _EXPORTS:
        module, attribute = _EXPORTS[name]
        return getattr(importlib.import_module(f".{module}", __name__), attribute)
    if name in _MODULES:
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
