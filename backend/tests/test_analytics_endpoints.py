"""Endpoint tests for the analytics API (prices served by a fake PriceService)"""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_required_price_service
from app.main import app

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
BASE = {"symbols": SYMBOLS, "start_date": "2023-01-01T00:00:00Z", "end_date": "2024-12-31T00:00:00Z"}
ALLOCATIONS = {
    "Fund": {"BTCUSDT": 0.5, "ETHUSDT": 0.3, "BNBUSDT": 0.2},
    "Bitcoin": {"BTCUSDT": 1.0},
}


class FakePriceService:
    """Serves deterministic daily prices; symbols outside the frame have no data"""

    def __init__(self):
        rng = np.random.default_rng(3)
        dates = pd.date_range("2023-01-01", "2024-12-31", freq="D")
        cov = np.array([[4, 3, 2], [3, 6, 2], [2, 2, 5]]) * 1e-4
        rets = rng.multivariate_normal([0.001, 0.0012, 0.0008], cov, len(dates))
        self.frame = pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=dates, columns=SYMBOLS)

    async def get_price_frame(self, symbols, start_date=None, end_date=None, use_cache=True):
        return self.frame[[s for s in symbols if s in self.frame.columns]].copy()


@pytest.fixture
def client():
    app.dependency_overrides[get_required_price_service] = FakePriceService
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def post(client, url, **body):
    return client.post(f"/api/v1{url}", json={**BASE, **body})


class TestInvestmentUniverse:
    def test_asset_metrics(self, client):
        response = post(client, "/investment-universe/asset-metrics")
        assert response.status_code == 200, response.text
        btc = response.json()["data"][0]
        assert btc["symbol"] == "BTCUSDT"
        assert btc["max_drawdown"] <= 0
        assert len(btc["max_drawdown_date"]) == 10

    def test_unknown_symbol_is_a_400(self, client):
        response = client.post("/api/v1/investment-universe/asset-metrics",
                               json={**BASE, "symbols": ["BTCUSDT", "FOOUSDT"]})
        assert response.status_code == 400
        assert "FOOUSDT" in response.json()["message"]


class TestStrategy:
    def test_optimize(self, client):
        response = post(
            client, "/strategy/optimize",
            objectives=["sharpe_ratio", "minimum_variance", "tracking_error"],
            constraints=[{"asset": "all", "sign": "<=", "limit": 0.6}],
            risk_constraints={"volatility": {"sign": "≤", "limit": 0.5}},
            benchmark={"btcusdt": 1.0},
        )
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert set(data["allocations"]) == {"sharpe_ratio", "minimum_variance", "tracking_error", "equal_weight"}
        for weights in data["allocations"].values():
            assert sum(weights.values()) == pytest.approx(1.0, abs=1e-5)
            assert max(weights.values()) <= 0.6 + 1e-5
        assert set(data["metrics"]) == {"Expected Returns", "Expected Volatility", "Sharpe Ratio"}

    def test_relative_objective_without_benchmark_is_a_400(self, client):
        response = post(client, "/strategy/optimize", objectives=["information_ratio"])
        assert response.status_code == 400
        assert "benchmark" in response.json()["message"]

    def test_constraint_on_unknown_symbol_is_a_422(self, client):
        response = post(client, "/strategy/optimize", constraints=[{"asset": "XRPUSDT", "sign": "<=", "limit": 0.2}])
        assert response.status_code == 422

class TestMetrics:
    def test_var(self, client):
        response = post(client, "/metrics/var", allocations=ALLOCATIONS, iterations=1000,
                        methods=["multivariate", "monte_carlo"], mean_shock={"btcusdt": 0.5},
                        stress_factor=[1.5, 1.0, 1.0], backtest_window=60)
        assert response.status_code == 200, response.text
        fund = response.json()["data"]["Fund"]
        assert set(fund["methods"]) == {"historical", "parametric", "multivariate", "monte_carlo"}
        assert fund["methods"]["monte_carlo"]["histogram"]["counts"]
        assert fund["backtest"]["kupiec"]["P-value"]

    def test_var_bad_stress_shape_is_a_422(self, client):
        response = post(client, "/metrics/var", allocations=ALLOCATIONS, stress_factor=[1.0, 2.0])
        assert response.status_code == 422


def test_missing_binance_credentials_is_a_503():
    """Without the override, the analytics routes need a configured Binance client"""
    from app.core import dependencies

    dependencies.get_price_service.cache_clear()
    original = dependencies.get_binance_service
    dependencies.get_binance_service = lambda: None
    try:
        with TestClient(app) as test_client:
            response = post(test_client, "/investment-universe/asset-metrics")
        assert response.status_code == 503
    finally:
        dependencies.get_binance_service = original
        dependencies.get_price_service.cache_clear()
