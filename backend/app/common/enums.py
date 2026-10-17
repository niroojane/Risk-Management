"""Common domain types and enums Reusable domain types for the entire application"""
from enum import Enum


class QuoteAsset(str, Enum):
    """Supported quote assets"""
    USDT = "USDT"
    BUSD = "BUSD"
    BTC = "BTC"
    ETH = "ETH"


class RebalancingFrequency(str, Enum):
    """Rebalancing frequencies of a portfolio simulation"""
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    YEARLY = "Yearly"


class OptimizationObjective(str, Enum):
    """Portfolio optimization objectives (relative ones need a benchmark)"""
    MINIMUM_VARIANCE = "minimum_variance"
    SHARPE_RATIO = "sharpe_ratio"
    RISK_PARITY = "risk_parity"
    MAXIMUM_DIVERSIFICATION = "maximum_diversification"
    EIGENPORTFOLIO = "eigenportfolio"
    TRACKING_ERROR = "tracking_error"
    INFORMATION_RATIO = "information_ratio"


class ConstraintSign(str, Enum):
    """Comparison operator of an optimization constraint"""
    EQ = "="
    GE = ">="
    LE = "<="

    @property
    def solver_sign(self) -> str:
        """Sign as expected by the analytics constraint builders"""
        return {"=": "=", ">=": "≥", "<=": "≤"}[self.value]

    @classmethod
    def _missing_(cls, value):
        aliases = {"≥": ">=", "≤": "<=", "==": "="}
        if value in aliases:
            return cls(aliases[value])
        return None


class VaRMethod(str, Enum):
    """Simulation methods of the VaR endpoint"""
    MULTIVARIATE = "multivariate"
    GAUSSIAN_COPULA = "gaussian_copula"
    T_COPULA = "t_copula"
    GUMBEL_COPULA = "gumbel_copula"
    MONTE_CARLO = "monte_carlo"
