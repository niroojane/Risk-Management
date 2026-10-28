# CLAUDE.md - Backend

FastAPI backend of the Risk Management web app (crypto and multi-asset portfolio management).

## Architecture

**Layers:**
- `app/api/v1/`: FastAPI routes (HTTP only), one file per notebook tab: `health`, `universe`, `strategy`, `portfolio`, `risk` (risk views + `/metrics/var`), `market_risk`, `account`, `profile`
- `app/controllers/`: Orchestration: load prices / account data, run the analytics, build the response. Same file names as the routes, plus `base.py` (`AnalyticsController`, `WorkspaceController`)
- `app/schemas/`: Pydantic schemas (request / response API contracts), same file names, plus `analytics.py` and `workspace.py` shared by several tabs
- `app/services/`: Data sources only (Binance, Yahoo, account, cache); the analytics live in the project's `src/` package
- `app/core/`: Settings, market profiles, dependency injection, exceptions, rate limiter, middleware
- `app/common/`: Enums, response base class, DataFrame serialization (`to_payload`, split layout)

**Data flow:**
```
Route → Controller → Service (Binance / Yahoo / account) → pandas
          ↓
     analytics (thread) → Schema / ViewResponse
```

**Binance services:**
```
services/binance/            # async, cache and rate limiting around src/Binance_API.py
├── binance_client.py        # Async base client (rate limiting, cache) on the Spot client of src/Binance_API.py
├── market_data_service.py   # Market cap (src get_market_cap)
├── price_service.py         # Daily closes of whole UTC days, end date included (today's open candle), in 3-month chunks fetched in parallel (src fetch_closes)
├── quantity_service.py      # Account snapshots (src snapshot_balances)
├── rate_limiter.py          # Request weight limiter
└── dates.py                 # Date-range splitting
```
The Binance parsing (market cap table, klines to closes, snapshot balances, 1-minute pair price of a trade) lives in `src/Binance_API.py`, shared with the notebooks.

**Analytics: the project's shared `src/` package** (also used by the notebooks and Streamlit; no copies here)
```
src/                         # one folder up, made importable by app/__init__.py and pytest.ini
├── RiskMetrics.py           # Portfolio / RiskAnalysis, SLSQP constraints, VaR, PCA, rolling
├── Rebalancing.py           # Buy-and-hold / rebalanced portfolios
├── Metrics.py               # Performance and risk tables (charts only load if plotly is installed)
├── PnL_Computation.py       # Book cost / realized P&L from a trade history
├── Backtest.py              # Rolling optimization: Fund / Core / Overlay
├── Regime.py                # HMM regime engine; scenarios as 'regime:<scenario>' strategies (multi-asset)
├── Workspace.py             # Workspace of named series and the views of the app tabs
├── Account.py               # Crypto holdings, positioning and P&L tables
├── MultiAsset.py            # Multi-asset trades, ledger, holdings, P&L
├── Yahoo_API.py             # yfinance prices, FX, search, details
├── PositionHandler.py       # Update Files (Quantities / Positions)
└── PortfolioAnalytics.py    # Whole-grid computations of the app (constraints, optimization, VaR, asset metrics)
```
Synchronous CPU functions with no I/O. Controllers extend `AnalyticsController` (`controllers/base.py`), or `WorkspaceController` for views that need the workspace. `AnalyticsController` loads prices through `PriceService.get_price_frame()` and runs the computation in a thread (`_compute`, which turns a ValueError into HTTP 400). A change in `src/` changes the notebooks too: run the backend tests and check the notebooks. Allocation grids are index = names, columns = symbols.

**Other services:**
- `services/yahoo/`: `YahooMarketData` (cached prices, currencies, FX, search, details) and `YahooPriceService` (same interface as the Binance `PriceService`, converts to the base currency), on top of `src/Yahoo_API.py`
- `services/account/`: `PortfolioAccount` interface (`base.py`) implemented by `AccountService` (Binance) and `ExcelAccountService` (Excel files via `GitHubStorage`)

## Configuration

One `.env` file at the **project root** (`Risk Management/.env`, path set in `app/core/config.py` as `ENV_FILE`), shared with the frontend. Unknown keys such as `VITE_*` are ignored:
```
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
GITHUB_TOKEN=...
GITHUB_REPO_OWNER=...
GITHUB_REPO_NAME=Risk-Management
GITHUB_BRANCH=main
```
Never put credentials in `config.py`; its defaults stay empty.

## Market profiles

`MARKET` (`app/core/market.py`) selects the profile:
- `crypto`: Binance `PriceService` + `AccountService`
- `multi_asset`: `YahooPriceService` + `ExcelAccountService`, benchmark `CSPX.L` (S&P 500 UCITS ETF). The default universe is the UCITS one of `src/Yahoo_API.py`. The base currency can be changed at runtime with `PUT /api/v1/profile/currency`.

## Commands

```bash
# Run the server (dev)
uvicorn app.main:app --reload --port 8000

# Multi-asset profile, as start-yahoo.bat
MARKET=multi_asset uvicorn app.main:app --reload --port 8001

# Tests
pytest

# API docs: http://localhost:8000/docs
```

## Dependency Injection

Services in `app/core/dependencies.py` (singletons via `@lru_cache()`):
- `BinanceServiceDep`: base Binance client
- `MarketDataServiceDep`: market cap, public data
- `PriceServiceDep` / `RequiredPriceServiceDep`: prices for the active profile. The `Required` version returns 503 when Binance is not configured.
- `AccountServiceDep` / `RequiredAccountServiceDep`: real portfolio for the active profile
- `YahooMarketDataDep`: Yahoo Finance data (multi-asset)
- `QuantityServiceDep`: account quantities / balances

## Adding an endpoint

1. Schema (Request + Response) in `app/schemas/<domain>/`
2. Controller in `app/controllers/<tab>.py`, with the services injected
3. Route in `app/api/v1/<tab>.py`, using dependency injection
4. Register the router in `app/api/v1/__init__.py`
5. Add a test in `tests/`

## Important notes

- **Rate limiting**: 1200 req/min, weight-based (handled by `BinanceClient`)
- **Cache**: `BinanceClient.fetch_with_cache()` and `YahooMarketData` (in-memory `CacheService`)
- **Async**: synchronous Binance / yfinance calls are run in threads
- **Tests**: `tests/test_multi_asset.py` fakes Yahoo and GitHub. `tests/test_workspace_endpoints.py` fakes the price service and the Binance account.
