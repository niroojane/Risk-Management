"""Tests for the analytics library (app.services.analytics)"""
import numpy as np
import pandas as pd
import pytest

from app.common import frame_to_dict, series_to_dict, to_json_value
from src import PnL_Computation as pnl
from src.RiskMetrics import RiskAnalysis
from src import PortfolioAnalytics as analytics
from src.Rebalancing import get_rebalancing_dates, rebalanced_portfolio

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]


@pytest.fixture
def prices():
    """Two years of correlated daily prices"""
    rng = np.random.default_rng(7)
    dates = pd.date_range("2023-01-01", "2024-12-31", freq="D")
    cov = np.array([[4, 3, 2], [3, 6, 2], [2, 2, 5]]) * 1e-4
    rets = rng.multivariate_normal([0.001, 0.0012, 0.0008], cov, len(dates))
    return pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=dates, columns=SYMBOLS)


@pytest.fixture
def returns(prices):
    return analytics.to_returns(prices)


@pytest.fixture
def allocations():
    return analytics.allocation_frame(
        {"Fund": {"BTCUSDT": 0.5, "ETHUSDT": 0.3, "BNBUSDT": 0.2}, "Bitcoin": {"BTCUSDT": 1.0}}, SYMBOLS
    )


class TestOptimization:
    @pytest.mark.parametrize("objective", analytics.ABSOLUTE_OBJECTIVES)
    def test_weights_are_long_only_and_fully_invested(self, returns, objective):
        weights = RiskAnalysis(returns).optimize(objective)
        assert weights.min() >= 0
        assert weights.sum() == pytest.approx(1.0)

    def test_minimum_variance_beats_equal_weight(self, returns):
        portfolio = RiskAnalysis(returns)
        min_var = portfolio.optimize("minimum_variance")
        assert portfolio.variance(min_var) <= portfolio.variance(np.full(3, 1 / 3)) + 1e-9

    def test_weight_constraints_hold(self, returns):
        constraints = analytics.build_constraints(returns, [("All", "≤", 0.5), ("BNBUSDT", "≥", 0.2)])
        allocations, _ = analytics.optimize_allocations(returns, ["sharpe_ratio"], constraints)
        weights = allocations.loc["sharpe_ratio"]
        assert weights.max() <= 0.5 + 1e-6
        assert weights["BNBUSDT"] >= 0.2 - 1e-6

    def test_relative_objective_needs_benchmark(self, returns):
        with pytest.raises(ValueError, match="benchmark"):
            analytics.optimize_allocations(returns, ["tracking_error"])

    def test_tracking_error_objective_replicates_benchmark(self, returns):
        bench = pd.Series({"BTCUSDT": 0.6, "ETHUSDT": 0.4, "BNBUSDT": 0.0})
        allocations, _ = analytics.optimize_allocations(returns, ["tracking_error"], bench_weights=bench)
        np.testing.assert_allclose(allocations.loc["tracking_error"].to_numpy(), bench.to_numpy(), atol=1e-3)

    def test_equal_weight_is_added(self, returns):
        allocations, _ = analytics.optimize_allocations(returns, ["minimum_variance"])
        np.testing.assert_allclose(allocations.loc["equal_weight"].to_numpy(), np.full(3, 1 / 3))


class TestRebalancing:
    def test_rebalancing_dates_exclude_last_day(self, prices):
        dates = get_rebalancing_dates(prices, "Monthly")
        assert dates[0] == prices.index[0]
        assert prices.index[-1] not in dates

    def test_rebalanced_weights_reset_after_rebalance(self, prices):
        weights = np.array([0.5, 0.3, 0.2])
        values = rebalanced_portfolio(prices, weights, frequency="Monthly")
        # the day after a month end, holdings are back to the target weights (at the previous close)
        day = pd.Timestamp("2023-02-01")
        quantities = values.loc[day] / prices.loc[day]
        prev_value = (quantities * prices.loc[pd.Timestamp("2023-01-31")])
        np.testing.assert_allclose((prev_value / prev_value.sum()).to_numpy(), weights)

class TestRisk:
    def test_vol_decomposition_sums_to_volatility(self, returns):
        weights = np.array([0.5, 0.3, 0.2])
        portfolio = RiskAnalysis(returns)
        contrib = portfolio.var_contrib(weights)[0]
        assert contrib["Vol Contribution"].sum() == pytest.approx(portfolio.variance(weights))

    def test_value_at_risk_methods(self, prices, returns, allocations):
        np.random.seed(0)
        result = analytics.value_at_risk(prices, returns, allocations, iterations=2000, backtest_window=60)
        fund = result["Fund"]
        assert set(fund["methods"]) == {"historical", "parametric", *analytics.SIMULATION_METHODS}
        for method, values in fund["methods"].items():
            assert values["var"] < 0, method
            assert values["cvar"] <= values["var"], method
        # the per-asset contributions of a simulated VaR scenario add up to it
        mv = fund["methods"]["multivariate"]
        assert mv["var_contribution"].sum() == pytest.approx(mv["var"])
        assert sum(mv["histogram"]["counts"]) == 2000
        assert list(fund["backtest"]["kupiec"].index) == ["Proportion of failure", "Kupiec Stat", "P-value"]

    def test_value_at_risk_accepts_stress_grid(self, prices, returns, allocations):
        grid = np.eye(3) * 1.5
        grid[1, 0] = 0.2
        result = analytics.value_at_risk(prices, returns, allocations, iterations=500,
                                         stress_factor=grid.tolist(), methods=["gaussian_copula", "gumbel_copula"])
        assert set(result["Fund"]["methods"]) == {"historical", "parametric", "gaussian_copula", "gumbel_copula"}

class TestUniverse:
    def test_asset_metrics_columns(self, prices):
        metrics = analytics.asset_metrics(prices)
        assert list(metrics.index) == SYMBOLS
        assert (metrics["max_drawdown"] <= 0).all()


class TestPnL:
    def test_weighted_average_book_cost_and_realized_pnl(self):
        trades = pd.DataFrame({
            "Date(UTC)": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "Market": ["BTCUSDT", "BTCUSDT", "BTCUSDT"],
            "Type": ["BUY", "BUY", "SELL"],
            "Amount": [1.0, 1.0, 1.0],
            "Price in USDT": [100.0, 200.0, 300.0],
            "Total in USDT": [100.0, 200.0, 300.0],
            "Pair Price": [1.0, 1.0, 1.0],
        })
        book_cost = pnl.get_book_cost(trades)
        assert book_cost["BTCUSDT"].iloc[-1] == pytest.approx(150.0)
        realized, _ = pnl.get_pnl(book_cost, trades)
        assert realized.loc["BTCUSDT", "Realized PnL"] == pytest.approx(150.0)


class TestSerialization:
    def test_json_values(self):
        assert to_json_value(np.float64("nan")) is None
        assert to_json_value(np.inf) is None
        assert to_json_value(pd.Timestamp("2024-01-02")) == "2024-01-02"
        assert to_json_value(pd.NaT) is None
        assert to_json_value(np.int64(3)) == 3
        assert to_json_value(np.complex128(2 + 0j)) == 2.0

    def test_frames(self):
        frame = pd.DataFrame({"a": [1.0, np.nan]}, index=pd.to_datetime(["2024-01-01", "2024-01-02"]))
        assert frame_to_dict(frame) == {"2024-01-01": {"a": 1.0}, "2024-01-02": {"a": None}}
        assert series_to_dict(frame["a"]) == {"2024-01-01": 1.0, "2024-01-02": None}
