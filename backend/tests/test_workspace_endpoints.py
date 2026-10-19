"""Endpoint tests for the app views (strategy backtest, portfolio, risk, market risk, account)"""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_account_service, get_required_account_service, get_required_price_service
from app.main import app
from app.services.account import AccountHistory, AccountService
from src import Account as account_analytics

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
DATES = pd.date_range("2022-01-01", "2024-12-31", freq="D")


def _prices(symbols, seed=5):
    rng = np.random.default_rng(seed)
    cov = (np.full((4, 4), 2) + np.diag([2, 4, 3, 7])) * 1e-4
    rets = rng.multivariate_normal([0.001, 0.0012, 0.0008, 0.0015], cov, len(DATES))
    frame = pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=DATES, columns=SYMBOLS)
    frame["USDTUSDT"] = 1.0
    return frame[[s for s in symbols if s in frame.columns]]


class FakePriceService:
    async def get_price_frame(self, symbols, start_date=None, end_date=None, use_cache=True):
        frame = _prices(symbols)
        return frame.loc[pd.Timestamp(start_date.date()):pd.Timestamp(end_date.date())].copy()


class FakeAccountService(AccountService):
    """Holds BTC / ETH / USDT since mid-2023, bought in two trades (Binance I/O faked, logic real)"""

    def __init__(self):  # no Binance client / GitHub storage
        days = DATES[DATES >= "2023-06-01"]
        self.quantities = pd.DataFrame({"BTCUSDT": 0.5, "ETHUSDT": 4.0, "USDTUSDT": 1000.0}, index=days)
        prices = _prices(["BTCUSDT", "ETHUSDT", "USDTUSDT"]).loc[days]
        self.positions = self.quantities * prices
        self.positions["Total"] = self.positions.sum(axis=1)
        self.trades = account_analytics.trades_in_usdt(pd.DataFrame({
            "Date(UTC)": ["2023-05-30 10:00", "2023-05-31 12:00"],
            "Market": ["BTCUSDT", "ETHUSDT"],
            "Type": ["BUY", "BUY"],
            "Price": [100.0, 120.0],
            "Amount": [0.5, 4.0],
            "Pair Price": [1.0, 1.0],
        }))

    async def get_history(self, use_cache=True):
        return AccountHistory(positions=self.positions, quantities=self.quantities)

    async def get_history_prices(self, history, use_cache=True):
        return _prices(list(history.quantities.columns))

    async def get_book_cost(self, use_cache=True):
        book_cost, realized = account_analytics.book_cost_and_pnl(self.trades)
        return book_cost, realized, self.trades

    async def get_holdings(self, use_cache=True):
        self.holdings_use_cache = use_cache
        balances = pd.DataFrame({"free": [0.5, 4.0, 1000.0], "locked": [0.0, 0.0, 0.0]},
                                index=["BTCUSDT", "ETHUSDT", "USDTUSDT"])
        prices = _prices(["BTCUSDT", "ETHUSDT", "USDTUSDT"]).iloc[-1]
        return account_analytics.holdings_table(balances, prices), balances


@pytest.fixture
def client():
    account = FakeAccountService()
    app.dependency_overrides[get_required_price_service] = FakePriceService
    app.dependency_overrides[get_account_service] = lambda: account
    app.dependency_overrides[get_required_account_service] = lambda: account
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


ALLOCATIONS = {
    "Optimal Portfolio": {"BTCUSDT": 0.4, "ETHUSDT": 0.3, "BNBUSDT": 0.2, "SOLUSDT": 0.1},
    "Equal Weighted": {s: 0.25 for s in SYMBOLS},
}
WINDOW = {"symbols": SYMBOLS, "history_start": "2022-01-01T00:00:00", "start_date": "2023-07-01T00:00:00",
          "end_date": "2024-12-31T00:00:00", "allocations": ALLOCATIONS}


def frame(payload):
    """split payload -> DataFrame"""
    return pd.DataFrame(payload["data"], index=payload["index"], columns=payload["columns"])


@pytest.fixture
def strategies(client):
    """Fund / Core / Overlay schedules from a rolling backtest"""
    response = client.post("/api/v1/strategy/backtest", json={
        "symbols": SYMBOLS, "start_date": "2022-01-01T00:00:00", "end_date": "2024-12-31T00:00:00",
        "objective": "minimum_variance", "frequency": "Quarterly",
        "overlays": [{"objective": "sharpe_ratio", "limit": 0.2}],
        "constraints": [{"asset": "All", "sign": "<=", "limit": 0.6}],
    })
    assert response.status_code == 200, response.text
    return response.json()["data"]


class TestStrategy:
    def test_backtest(self, strategies):
        assert set(strategies["schedules"]) == {"Fund", "Core", "Overlay"}
        fund = pd.DataFrame.from_dict(strategies["schedules"]["Fund"], orient="index")
        np.testing.assert_allclose(fund.sum(axis=1), 1.0, atol=1e-4)
        assert fund.iloc[1:].max().max() <= 0.6 * 0.8 + 0.2 + 1e-4  # core capped at 60%, overlay up to 20%
        assert sum(strategies["model"].values()) == pytest.approx(1.0, abs=1e-4)
        metrics = frame(strategies["metrics"])
        assert {"Fund", "Core", "Overlay", "Bitcoin"} <= set(metrics.columns)
        assert "Tracking Error to Bitcoin" in metrics.index

    def test_overlays_over_100_percent(self, client):
        response = client.post("/api/v1/strategy/backtest", json={
            "symbols": SYMBOLS, "start_date": "2022-01-01T00:00:00", "end_date": "2024-12-31T00:00:00",
            "overlays": [{"objective": "sharpe_ratio", "limit": 0.7}, {"objective": "risk_parity", "limit": 0.6}],
        })
        assert response.status_code == 400

    def test_performance_view(self, client, strategies):
        response = client.post("/api/v1/portfolio/performance", json={
            **WINDOW, "strategies": strategies["schedules"], "benchmark": "Equal Weighted",
            "frontier_points": 10, "constraints": [{"asset": "BTCUSDT", "sign": ">=", "limit": 0.3}],
        })
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        levels = frame(data["levels"])
        assert list(levels.columns[:3]) == ["Fund", "Core", "Overlay"]
        assert "Rebalanced Equal Weighted" in levels.columns and "Bitcoin" in levels.columns
        np.testing.assert_allclose(levels.iloc[0].to_numpy(dtype=float), 100.0)
        risk = frame(data["risk_table"])
        assert risk.loc["TEV (daily)", "Rebalanced Equal Weighted"] == pytest.approx(0.0)
        assert data["frontier"]["constrained"] is not None


class TestPortfolioViews:
    def test_calendar(self, client, strategies):
        response = client.post("/api/v1/portfolio/calendar", json={
            **WINDOW, "strategies": strategies["schedules"], "fund": "Fund", "benchmark": "Core", "period": "Month",
        })
        assert response.status_code == 200, response.text
        returns = frame(response.json()["data"]["returns"])
        assert list(returns.columns) == ["Fund", "Core"]
        assert "2024-12" in returns.index

    def test_return_analysis_with_historical(self, client):
        response = client.post("/api/v1/portfolio/return-analysis", json={
            **WINDOW, "include_historical": True, "fund": "Historical Portfolio", "benchmark": "Bitcoin",
        })
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        contribution = frame(data["contribution"])
        assert "Total Return" in contribution.columns
        drawdown = frame(data["drawdown"])
        assert "Historical Portfolio" in drawdown.columns

    def test_beta(self, client):
        response = client.post("/api/v1/portfolio/beta", json={
            **WINDOW, "include_historical": True, "fund": "Rebalanced Optimal Portfolio", "benchmark": "Bitcoin",
            "window": 60,
        })
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert frame(data["portfolio_beta"])["Bitcoin"].dropna().round(6).eq(1.0).all()
        assert "Total Beta" in frame(data["beta_contribution"]).columns

    def test_pnl_analysis(self, client):
        response = client.post("/api/v1/portfolio/pnl-analysis", json=WINDOW)
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert "Historical Portfolio" in frame(data["cumulative_return"]).columns
        assert {"Cumulative P&L", "Total P&L"} <= set(frame(data["cumulative_contribution"]).columns)
        assert "Total" in frame(data["positions"]).columns


class TestRiskViews:
    def test_contribution(self, client):
        response = client.post("/api/v1/risk/contribution", json={
            "symbols": SYMBOLS, "start_date": "2023-07-01T00:00:00", "end_date": "2024-12-31T00:00:00",
            "allocations": ALLOCATIONS, "fund": "Optimal Portfolio", "benchmark": "Equal Weighted",
        })
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        contribution = frame(data["contribution"])
        assert {"Profit and Loss (Buy and Hold)", "Vol Contribution"} <= set(contribution.columns)
        ex_ante = frame(data["ex_ante"])
        assert ex_ante.loc["Equal Weighted", "Tracking Error Ex Ante"] == pytest.approx(0.0)

    def test_trajectory(self, client):
        response = client.post("/api/v1/risk/trajectory", json={
            **WINDOW, "include_historical": True, "selected": "Historical Portfolio", "window": 120,
        })
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        vol = frame(data["volatility"])
        assert {"Historical Portfolio", "Rebalanced Optimal Portfolio", "Bitcoin"} <= set(vol.columns)
        assert "Total Vol" in frame(data["vol_contribution"]).columns

    def test_tracking_error(self, client):
        response = client.post("/api/v1/risk/tracking-error", json={
            **WINDOW, "selected": "Rebalanced Optimal Portfolio", "benchmark": "Bitcoin", "window": 120,
        })
        assert response.status_code == 200, response.text
        te = frame(response.json()["data"]["tracking_error"])
        assert te["Bitcoin"].dropna().abs().max() == pytest.approx(0.0)
        assert te["Rebalanced Optimal Portfolio"].dropna().gt(0).all()

    def test_var_history(self, client):
        response = client.post("/api/v1/risk/var-history", json={
            **WINDOW, "start_date": "2024-06-01T00:00:00", "selected": "Rebalanced Optimal Portfolio",
            "method": "multivariate", "window": 150, "iterations": 300,
        })
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert frame(data["var"]).lt(0).all().all()
        assert "Portfolio" in frame(data["selected_var"]).columns

    def test_stress_preview(self, client):
        grid = (np.eye(4) * 1.5).tolist()
        grid[1][0] = 0.3
        response = client.post("/api/v1/risk/stress-preview", json={
            "symbols": SYMBOLS, "start_date": "2023-07-01T00:00:00", "end_date": "2024-12-31T00:00:00",
            "stress_factor": grid, "mean_shock": {"btcusdt": 2.0},
        })
        assert response.status_code == 200, response.text
        moments = frame(response.json()["data"]["moments"])
        assert moments.loc["BTCUSDT", "Shocked Vol"] == pytest.approx(moments.loc["BTCUSDT", "Vol"] * 1.5)
        assert moments.loc["BTCUSDT", "Shocked Means"] == pytest.approx(moments.loc["BTCUSDT", "Means"] * 2)


class TestMarketRiskViews:
    def test_pca(self, client):
        response = client.post("/api/v1/market-risk/pca-analysis", json={
            "symbols": SYMBOLS, "start_date": "2023-07-01T00:00:00", "end_date": "2024-12-31T00:00:00",
            "num_components": 3, "component": "PC2", "num_closest": 2,
        })
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["component"] == "PC2"
        assert frame(data["variance_explained"]).iloc[:, 0].sum() == pytest.approx(1.0)
        assert frame(data["similarity"]).shape[1] == 2

    def test_correlation(self, client):
        response = client.post("/api/v1/market-risk/correlation-analysis", json={
            "symbols": SYMBOLS, "start_date": "2023-07-01T00:00:00", "end_date": "2024-12-31T00:00:00",
            "asset1": "btcusdt", "asset2": "ETHUSDT", "window": 90,
        })
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert list(frame(data["rolling_correlation"]).columns) == ["BTCUSDT/ETHUSDT"]
        assert frame(data["matrix"]).loc["BTCUSDT", "BTCUSDT"] == 1.0

    def test_drivers(self, client):
        response = client.post("/api/v1/market-risk/drivers", json={
            **WINDOW, "eigen_frequency": "Quarterly", "component": "PC1", "window": 90,
        })
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        performance = frame(data["performance"])
        assert performance["Market Index"].iloc[-1] != pytest.approx(100.0)  # a real, non-zero index
        np.testing.assert_allclose(frame(data["weights"]).sum(axis=1), 1.0)


class TestAccount:
    def test_holdings(self, client):
        response = client.get("/api/v1/account/holdings")
        assert response.status_code == 200, response.text
        assert set(response.json()["data"]["tickers"]) == {"BTCUSDT", "ETHUSDT", "USDTUSDT"}

    def test_positioning(self, client):
        response = client.post("/api/v1/account/positioning",
                               json={"model_weights": {"btcusdt": 0.5, "SOLUSDT": 0.5}})
        assert response.status_code == 200, response.text
        table = frame(response.json()["data"]["positioning"])
        total = table.loc["Total"]
        assert total["Model"] == pytest.approx(total["Current Portfolio in USDT"])
        assert table.loc["SOLUSDT", "Spread"] < 0

    @pytest.mark.parametrize("method, url, body", [
        ("get", "/api/v1/account/holdings", None),
        ("post", "/api/v1/account/positioning", {"model_weights": {"BTCUSDT": 1.0}}),
        ("get", "/api/v1/account/pnl", None),
    ])
    def test_refresh_skips_cache(self, client, method, url, body):
        account = app.dependency_overrides[get_required_account_service]()
        kwargs = {"json": body} if body else {}
        assert client.request(method, url, **kwargs).status_code == 200
        assert account.holdings_use_cache is True
        assert client.request(method, url + "?use_cache=false", **kwargs).status_code == 200
        assert account.holdings_use_cache is False

    def test_pnl(self, client):
        response = client.get("/api/v1/account/pnl")
        assert response.status_code == 200, response.text
        pnl = frame(response.json()["data"]["pnl"])
        assert pnl.loc["BTCUSDT", "Average Cost"] == pytest.approx(100.0)
        assert pnl.loc["BTCUSDT", "Book Cost"] == pytest.approx(50.0)
