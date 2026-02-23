"""Transform price data to per-asset risk metrics"""
import math
import logging
from typing import List, Optional

import numpy as np
import pandas as pd
from scipy.stats import norm

from ....models.investment_universe.market_data_models import AssetRiskMetrics

logger = logging.getLogger(__name__)


def _safe_float(val) -> Optional[float]:
    try:
        v = float(val)
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 4)
    except (TypeError, ValueError):
        return None


class RiskTransformer:

    @staticmethod
    def calculate_asset_risk(prices: pd.DataFrame) -> Optional[List[AssetRiskMetrics]]:
        if prices.empty or len(prices) < 2:
            return None

        if not isinstance(prices.index, pd.DatetimeIndex):
            prices = prices.copy()
            prices.index = pd.to_datetime(prices.index)

        inception_year = int(prices.index[0].year)

        try:
            vol_daily = prices.pct_change().iloc[-260:].std() * np.sqrt(260)

            weekly_prices = prices.resample("W").last()
            vol_3y_weekly = weekly_prices.iloc[-153:].pct_change().std() * np.sqrt(52)

            monthly_prices = prices.resample("ME").last()
            vol_5y_monthly = monthly_prices.iloc[-50:].pct_change().std() * np.sqrt(12)
            vol_inception_monthly = monthly_prices.iloc[-181:].pct_change().std() * np.sqrt(12)

            drawdown_series = (prices - prices.cummax()) / prices.cummax()
            max_drawdown = drawdown_series.min()
            date_of_max_drawdown = drawdown_series.idxmin()

            Q = 0.05
            intervals = np.arange(Q, 1.0, 0.0005, dtype=float)
            cvar_95 = vol_inception_monthly * norm(loc=0, scale=1).ppf(1 - intervals).mean() / Q

        except Exception as exc:
            logger.warning(f"Risk metrics computation failed: {exc}")
            return None

        results: List[AssetRiskMetrics] = []
        for symbol in prices.columns:
            try:
                dd_date = date_of_max_drawdown[symbol]
                dd_date_str = dd_date.date().isoformat() if pd.notna(dd_date) else None

                results.append(AssetRiskMetrics(
                    symbol=symbol,
                    annualized_vol_daily=_safe_float(vol_daily[symbol]),
                    annualized_vol_3y_weekly=_safe_float(vol_3y_weekly[symbol]),
                    annualized_vol_5y_monthly=_safe_float(vol_5y_monthly[symbol]),
                    annualized_vol_since_inception_monthly=_safe_float(vol_inception_monthly[symbol]),
                    inception_year=inception_year,
                    cvar_parametric_95=_safe_float(cvar_95[symbol]),
                    max_drawdown=_safe_float(max_drawdown[symbol]),
                    date_of_max_drawdown=dd_date_str,
                ))
            except Exception as exc:
                logger.warning(f"Risk metrics failed for {symbol}: {exc}")
                continue

        return results or None
