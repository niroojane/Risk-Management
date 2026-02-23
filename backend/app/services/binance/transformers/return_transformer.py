"""Transform price data to return metrics"""
import math
import logging
from typing import Optional

import pandas as pd

from ....models.investment_universe.market_data_models import AssetReturnMetrics, MarketReturnsData

logger = logging.getLogger(__name__)


class ReturnTransformer:

    @staticmethod
    def calculate_asset_returns(prices: pd.DataFrame) -> Optional[MarketReturnsData]:
        if prices.empty or len(prices) < 2:
            return None

        total_returns = prices.iloc[-1] / prices.iloc[0] - 1

        days_elapsed = (prices.index[-1] - prices.index[0]).days
        if days_elapsed > 0:
            annualized_returns = (1 + total_returns) ** (365 / days_elapsed) - 1
        else:
            annualized_returns = pd.Series(0.0, index=total_returns.index)

        latest_year = prices.index[-1].year
        ytd_start = pd.Timestamp(year=latest_year, month=1, day=1)
        ytd_prices = prices.loc[prices.index >= ytd_start]

        if len(ytd_prices) >= 2:
            ytd_returns = ytd_prices.iloc[-1] / ytd_prices.iloc[0] - 1
        else:
            ytd_returns = pd.Series(0.0, index=total_returns.index)

        assets = []
        for symbol in total_returns.index:
            total_ret = float(total_returns[symbol])
            ytd_ret = float(ytd_returns[symbol])
            ann_ret = float(annualized_returns[symbol])

            if not any(math.isnan(v) or math.isinf(v) for v in (total_ret, ytd_ret, ann_ret)):
                assets.append(AssetReturnMetrics(
                    symbol=symbol,
                    total_return=round(total_ret, 6),
                    ytd_return=round(ytd_ret, 6),
                    annualized_return=round(ann_ret, 6),
                ))

        return MarketReturnsData(
            period_start_date=prices.index[0].to_pydatetime(),
            ytd_start_date=ytd_start.to_pydatetime(),
            assets=assets,
        )
