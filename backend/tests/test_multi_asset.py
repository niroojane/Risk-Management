"""Multi-asset profile (start-yahoo.bat): Yahoo prices with FX, profile / universe endpoints,
and the Excel portfolio (holdings, P&L with fees, P&L history, Update Files).

Yahoo Finance and GitHub are faked; the parsing, FX, ledger and P&L logic is real.
"""
import json
import zlib

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core import market as market_module
from app.core.config import settings
from app.core.dependencies import (
    get_account_service,
    get_required_account_service,
    get_required_price_service,
    get_yahoo_market_data,
)
from app.core.market import MULTI_ASSET_PROFILE, get_currency_settings
from app.main import app
from app.services.account import ExcelAccountService
from app.services.yahoo import YahooMarketData, YahooPriceService
from src import PositionHandler as position_handler
from src import Regime as regime
from src import Yahoo_API as yahoo_api

FX = {'EUR': 1.1, 'GBP': 1.3}


def fake_close(tickers, start=None, end=None, max_workers=8):
    """Business-day closes: FX pairs constant, other tickers a random walk seeded by their name"""
    days = pd.bdate_range(pd.Timestamp(start), pd.Timestamp(end))
    out = pd.DataFrame(index=days)
    for t in tickers:
        if t.endswith('=X'):
            out[t] = FX.get(t[:3], 1.0)
        else:
            rng = np.random.default_rng(zlib.crc32(t.encode()))
            out[t] = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(days))))
    out.attrs['failed'] = []
    return out


def fake_currencies(tickers):
    return pd.Series({t: 'EUR' if t.endswith('.PA') else 'GBp' if t.endswith('.L') else 'USD'
                      for t in tickers}, dtype=object)


def fake_search(query, max_results=10):
    return pd.DataFrame([{'Symbol': 'XLK', 'Name': 'Technology Select Sector SPDR', 'Type': 'ETF',
                          'Exchange': 'NYSE Arca'}])


def fake_details(tickers, refresh=False):
    return pd.DataFrame({t: {'Name': f'{t} fund', 'Type': 'ETF', 'Currency': fake_currencies([t])[t],
                             'Price': 100.0, 'Expense Ratio %': 0.09} for t in tickers}).T


class FakeStorage:
    """The ETF folder in memory: what 'Update Files' writes is kept in `written`"""

    def __init__(self):
        days = pd.bdate_range('2025-03-03', '2025-09-30')
        closes = fake_close(['XLK', 'GOLD.PA'], days[0], days[-1])
        quantities = pd.DataFrame({'XLK': 10.0, 'GOLD.PA': 5.0, 'USD': 1000.0}, index=days)
        positions = quantities * closes.reindex(columns=quantities.columns).fillna(1.0)
        positions['GOLD.PA'] *= FX['EUR']
        positions['Total'] = positions.sum(axis=1)
        self.files = {
            'Current Portfolio2': pd.DataFrame({'asset': ['XLK', 'GOLD.PA', 'USD'],
                                                'free': [10.0, 5.0, 1000.0], 'locked': [0, 0, 0]}),
            'Trade History2': pd.DataFrame({
                'Date(UTC)': ['2025-03-03 15:00', '2025-04-01 10:00', '2025-06-02 15:00'],
                'Market': ['XLKUSD', 'GOLD.PAEUR', 'XLKUSD'],
                'Type': ['BUY', 'BUY', 'SELL'],
                'Price': [100.0, 20.0, 120.0],
                'Amount': [12.0, 5.0, 2.0],
                'Total': [1200.0, 100.0, 240.0],
                'Fee': [0.0, 0.5, 1.0],
                'Fee Coin': ['USD', 'EUR', 'USD'],
            }),
            'Positions2': positions,
            'Quantities2': quantities,
        }
        self.written = {}

    def can_write(self):
        return True

    def read_excel(self, name, index_col=None):
        return self.files[name].copy()

    def write_excel(self, df, name):
        self.written[name] = df
        return 'updated'


@pytest.fixture
def storage():
    return FakeStorage()


@pytest.fixture
def client(monkeypatch, storage):
    for module in (yahoo_api, position_handler):
        monkeypatch.setattr(module, 'get_close', fake_close)
        monkeypatch.setattr(module, 'get_currencies', fake_currencies)
    monkeypatch.setattr(yahoo_api, 'search_yahoo', fake_search)
    monkeypatch.setattr(yahoo_api, 'fetch_ticker_details', fake_details)
    monkeypatch.setattr(yahoo_api, 'has_price_history', lambda t, period='5d': t != 'NOPE')
    monkeypatch.setattr(settings, 'MARKET', 'multi_asset')
    market_module.get_profile.cache_clear()

    currency = get_currency_settings()
    saved = (currency.base_currency, currency.convert_to_base)
    market = YahooMarketData(cache=None)
    account = ExcelAccountService(storage, market, currency, MULTI_ASSET_PROFILE, cache=None)
    app.dependency_overrides[get_yahoo_market_data] = lambda: market
    app.dependency_overrides[get_required_price_service] = lambda: YahooPriceService(market, currency)
    app.dependency_overrides[get_account_service] = lambda: account
    app.dependency_overrides[get_required_account_service] = lambda: account
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    currency.base_currency, currency.convert_to_base = saved
    monkeypatch.undo()
    market_module.get_profile.cache_clear()


def frame(payload):
    return pd.DataFrame(payload["data"], index=payload["index"], columns=payload["columns"])


class TestProfile:
    def test_profile(self, client):
        response = client.get("/api/v1/profile")
        assert response.status_code == 200, response.text
        profile = response.json()["data"]
        assert profile["name"] == "multi_asset"
        assert profile["benchmark_ticker"] == "CSPX.L"
        assert "USD" in profile["cash_assets"]
        assert "Equity" in profile["asset_classes"]
        assert profile["currency"]["base_currency"] == "USD"

    def test_currency_update(self, client):
        response = client.put("/api/v1/profile/currency", json={"base_currency": "eur"})
        assert response.status_code == 200, response.text
        assert response.json()["data"]["currency"]["base_currency"] == "EUR"
        assert client.put("/api/v1/profile/currency", json={"base_currency": "XYZ"}).status_code == 422

    def test_crypto_profile_has_no_yahoo_universe(self, client, monkeypatch):
        monkeypatch.setattr(settings, 'MARKET', 'crypto')
        market_module.get_profile.cache_clear()
        assert client.get("/api/v1/universe/search", params={"q": "gold"}).status_code == 400
        market_module.get_profile.cache_clear()


class TestUniverse:
    def test_search(self, client):
        response = client.get("/api/v1/universe/search", params={"q": "tech"})
        assert response.status_code == 200, response.text
        results = frame(response.json()["data"]["results"])
        assert results.loc["XLK", "Asset Class"] == "ETF"   # QUOTE_TYPE_CLASS

    def test_details(self, client):
        response = client.post("/api/v1/universe/details", json={"tickers": ["XLK", "GOLD.PA"]})
        assert response.status_code == 200, response.text
        details = frame(response.json()["data"]["details"])
        assert list(details.index) == ["XLK", "GOLD.PA"]
        assert details.loc["GOLD.PA", "Currency"] == "EUR"

    def test_check(self, client):
        ok = client.post("/api/v1/universe/check", json={"ticker": "XLK"})
        assert ok.status_code == 200, ok.text
        assert ok.json()["data"]["asset_class"] == "ETF"
        forced = client.post("/api/v1/universe/check", json={"ticker": "XLK", "asset_class": "Credit"})
        assert forced.json()["data"]["asset_class"] == "Credit"
        assert client.post("/api/v1/universe/check", json={"ticker": "NOPE"}).status_code == 400


class TestYahooPrices:
    def _prices(self, client):
        response = client.post("/api/v1/investment-universe/prices", json={
            "symbols": ["XLK", "GOLD.PA", "ISLN.L"], "start_date": "2025-01-02", "end_date": "2025-06-30",
        })
        assert response.status_code == 200, response.text
        return pd.DataFrame(response.json()["data"]["data"]).T

    def test_converted_to_base(self, client):
        prices = self._prices(client)
        local = fake_close(["XLK", "GOLD.PA", "ISLN.L"], "2025-01-02", "2025-06-30")
        day = prices.index[10]
        assert prices.loc[day, "XLK"] == pytest.approx(local.loc[day, "XLK"])
        assert prices.loc[day, "GOLD.PA"] == pytest.approx(local.loc[day, "GOLD.PA"] * FX["EUR"])
        # pence: GBp = GBP / 100
        assert prices.loc[day, "ISLN.L"] == pytest.approx(local.loc[day, "ISLN.L"] * FX["GBP"] / 100)

    def test_local_currencies(self, client):
        client.put("/api/v1/profile/currency", json={"convert_to_base": False})
        prices = self._prices(client)
        local = fake_close(["GOLD.PA"], "2025-01-02", "2025-06-30")
        day = prices.index[10]
        assert prices.loc[day, "GOLD.PA"] == pytest.approx(local.loc[day, "GOLD.PA"])


class TestExcelAccount:
    def test_holdings(self, client):
        response = client.get("/api/v1/account/holdings")
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert set(data["tickers"]) == {"XLK", "GOLD.PA"}
        holdings = frame(data["holdings"])
        assert {"Currency", "Quantity", "Price", "FX Rate", "Market Value", "Weights"} <= set(holdings.columns)
        assert holdings.loc["GOLD.PA", "FX Rate"] == pytest.approx(FX["EUR"])
        assert set(data["weights"]) == {"XLK", "GOLD.PA"}

    def test_positioning(self, client):
        response = client.post("/api/v1/account/positioning", json={"model_weights": {"XLK": 0.6, "IEF": 0.4}})
        assert response.status_code == 200, response.text
        table = frame(response.json()["data"]["positioning"])
        assert {"Current Portfolio", "Current Weights"} <= set(table.columns)
        assert table.loc["IEF", "Spread"] < 0

    def test_pnl_with_fees(self, client):
        response = client.get("/api/v1/account/pnl")
        assert response.status_code == 200, response.text
        pnl = frame(response.json()["data"]["pnl"])
        assert pnl.loc["XLK", "Average Cost"] == pytest.approx(100.0)
        assert pnl.loc["XLK", "Realized P&L"] == pytest.approx(2 * (120.0 - 100.0))
        assert pnl.loc["XLK", "Fees"] == pytest.approx(-1.0)
        # EUR fee and book cost translated to USD
        assert pnl.loc["GOLD.PA", "Fees"] == pytest.approx(-0.5 * FX["EUR"])
        assert pnl.loc["GOLD.PA", "Book Cost"] == pytest.approx(100.0 * FX["EUR"])
        trades = frame(response.json()["data"]["trades"])
        assert len(trades) == 3

    def test_pnl_analysis(self, client):
        response = client.post("/api/v1/portfolio/pnl-analysis", json={
            "symbols": ["XLK", "GOLD.PA", "CSPX.L"], "history_start": "2025-01-02T00:00:00",
            "start_date": "2025-03-03T00:00:00", "end_date": "2025-09-30T00:00:00",
            "allocations": {"Equal": {"XLK": 0.5, "GOLD.PA": 0.5}},
        })
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        returns = frame(data["cumulative_return"])
        assert {"Historical Portfolio", "Benchmark"} <= set(returns.columns)
        assert "Total" in frame(data["positions"]).columns

    def test_update_files(self, client, storage):
        response = client.post("/api/v1/account/upload", json={})
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["files"] == {"Quantities2": "updated", "Positions2": "updated"}
        assert data["messages"]
        quantities = storage.written["Quantities2"]
        assert quantities.index.max() > pd.Timestamp("2025-09-30")
        assert quantities.iloc[-1]["XLK"] == pytest.approx(10.0)
        assert "Total" in storage.written["Positions2"].columns


@pytest.fixture
def scenario_file(tmp_path, monkeypatch):
    """A fast scenario saved by the HMM Regime App: 2 regimes of ^GSPC (faked), one fit"""
    settings = {**regime.comparable(regime.default_settings()), 'n_states': 2, 'refit': 'Never (single fit)',
                'n_init': 1, 'strategies': {'0': 'Equal Weight', '1': 'Minimum Variance'},
                'exposures': {'0': 1.0, '1': 1.0}, 'asset_constraints': [], 'risk_constraints': []}
    path = tmp_path / 'HMM_Scenarios.json'
    path.write_text(json.dumps({'Quick': {'settings': settings, 'result': None, 'saved': 'test'}}), encoding='utf-8')
    monkeypatch.setattr(regime, 'SCENARIO_FILE', str(path))
    return path


class TestRegimeStrategies:
    BACKTEST = {"symbols": ["XLK", "GOLD.PA", "ISLN.L"], "start_date": "2024-01-02T00:00:00",
                "end_date": "2025-06-30T00:00:00", "objective": "risk_parity", "frequency": "Quarterly"}

    def test_scenarios(self, client, scenario_file):
        response = client.get("/api/v1/strategy/regime-scenarios")
        assert response.status_code == 200, response.text
        rows = response.json()["data"]["scenarios"]
        assert [r["key"] for r in rows] == ["regime:Default (initial)", "regime:Quick"]
        assert rows[1]["label"] == "Regime · Quick"
        assert client.get("/api/v1/profile").json()["data"]["regime_strategies"] is True

    def test_regime_overlay(self, client, scenario_file):
        response = client.post("/api/v1/strategy/backtest", json={
            **self.BACKTEST, "overlays": [{"objective": "regime:Quick", "limit": 0.3}]})
        assert response.status_code == 200, response.text
        payload = response.json()
        schedules = {k: pd.DataFrame.from_dict(v, orient="index") for k, v in payload["data"]["schedules"].items()}
        fund, core, overlay = schedules["Fund"], schedules["Core"], schedules["Overlay"]
        np.testing.assert_allclose(fund.sum(axis=1), 1.0, atol=1e-4)
        # the Fund also rebalances on the regime strategy's dates (monthly + regime changes),
        # each part holding its last weights in between
        assert len(fund) > len(core)
        held = lambda f: f.reindex(f.index.union(fund.index)).ffill().reindex(fund.index)
        np.testing.assert_allclose(fund, 0.7 * held(core) + 0.3 * held(overlay), atol=1e-5)
        assert any(w.startswith("Regime · Quick: current regime") for w in payload["warnings"])
        assert {"Fund", "Core", "Overlay"} <= set(frame(payload["data"]["metrics"]).columns)

    def test_regime_core(self, client, scenario_file):
        response = client.post("/api/v1/strategy/backtest", json={**self.BACKTEST, "objective": "regime:Quick"})
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert set(data["schedules"]) == {"Fund", "Core"}
        assert sum(data["model"].values()) == pytest.approx(1.0, abs=1e-4)

    def test_unknown_strategies(self, client, scenario_file):
        response = client.post("/api/v1/strategy/backtest", json={**self.BACKTEST, "objective": "momentum"})
        assert response.status_code == 422
        response = client.post("/api/v1/strategy/backtest", json={**self.BACKTEST, "objective": "regime:Nope"})
        assert response.status_code == 400
        assert "Unknown regime scenario" in response.text

    def test_crypto_profile(self, client, scenario_file, monkeypatch):
        monkeypatch.setattr(settings, 'MARKET', 'crypto')
        market_module.get_profile.cache_clear()
        assert client.get("/api/v1/strategy/regime-scenarios").json()["data"]["scenarios"] == []
        response = client.post("/api/v1/strategy/backtest", json={**self.BACKTEST, "objective": "regime:Quick"})
        assert response.status_code == 400
        market_module.get_profile.cache_clear()
