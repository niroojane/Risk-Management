"""Portfolio and risk analytics (ported from the legacy `src/` package)

- risk_metrics: Portfolio / RiskAnalysis classes, constraints, rolling risk
- rebalancing: buy-and-hold and rebalanced portfolio simulations
- metrics: performance and risk tables
- pnl: book cost and realized PnL from a trade history
- portfolio_analytics: API-oriented computations used by the controllers
"""
from . import metrics, pnl, portfolio_analytics, rebalancing, risk_metrics
from .risk_metrics import Portfolio, RiskAnalysis

__all__ = [
    "metrics",
    "pnl",
    "portfolio_analytics",
    "rebalancing",
    "risk_metrics",
    "Portfolio",
    "RiskAnalysis",
]
