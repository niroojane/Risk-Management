# Risk Management API - Backend

FastAPI backend of the Risk Management web app. It serves the analytics of the Crypto App and Multi Asset App notebooks to the React frontend: optimization, backtests, performance, P&L, risk decomposition, VaR and market risk. The calculations come from the project's shared `src/` package (one folder up), the same code the notebooks use.

## 📋 Prerequisites

- Python 3.11+ (tested with 3.13)
- Binance API keys for the crypto version (not needed for the Yahoo version)

## 🚀 Installation

The easiest way is the launchers at the project root (`start-binance.bat`, `start-yahoo.bat`), which create `backend/.venv` and install everything. Manually:

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip
```

### Configuration

Settings are read from the single `.env` file at the **project root** (one level above `backend/`), shared with the frontend. Copy `../.env.example` to `../.env` and fill it in:

```bash
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
GITHUB_TOKEN=your_token
GITHUB_REPO_OWNER=your_username
GITHUB_REPO_NAME=Risk-Management
GITHUB_BRANCH=main
```

The market is chosen with the `MARKET` environment variable (set by the launchers):

| `MARKET` | Prices | Portfolio | Benchmark |
|---|---|---|---|
| `crypto` (default) | Binance | Binance account + `BinancePTF/` Excel files | Bitcoin (`BTCUSDT`) |
| `multi_asset` | Yahoo Finance, converted to a base currency | `ETF/` Excel files on GitHub | `^GSPC` |

## ▶️ Run

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --reload --port 8000

# Multi-asset version (as start-yahoo.bat)
MARKET=multi_asset .venv/bin/python -m uvicorn app.main:app --reload --port 8001
```

## ✅ Tests

```bash
pytest                                   # all tests (70)
pytest tests/test_multi_asset.py -v      # one file
```

| File | Covers |
|---|---|
| `test_analytics.py` | Ported analytics (rebalancing, optimization, VaR, asset metrics) |
| `test_analytics_endpoints.py` | Asset metrics, optimization and VaR endpoints |
| `test_workspace_endpoints.py` | Backtest, portfolio, risk, market risk and account views |
| `test_multi_asset.py` | Yahoo profile: prices with FX, universe search / details, Excel portfolio, Update Files (Yahoo and GitHub faked) |
| `test_binance_service.py`, `test_cache_service.py`, `test_rate_limiter.py` | Infrastructure |

## 📊 Endpoints

All under `/api/v1`. Interactive documentation: http://localhost:8000/docs

| Area | Endpoints |
|---|---|
| Status | `GET /health` |
| Profile | `GET /profile`, `PUT /profile/currency` |
| Investment Universe | `POST /investment-universe/{market-cap, prices, asset-metrics}` |
| Yahoo universe (multi-asset) | `GET /universe/search`, `POST /universe/{details, check}` |
| Strategy | `POST /strategy/{optimize, backtest}` |
| Current Portfolio | `POST /portfolio/{performance, calendar, return-analysis, beta, pnl-analysis}` |
| Risk Analysis | `POST /risk/{contribution, trajectory, tracking-error, var-history, stress-preview}`, `POST /metrics/var` |
| Market Risk | `POST /market-risk/{pca-analysis, correlation-analysis, drivers}` |
| Account | `GET /account/{holdings, pnl}`, `POST /account/{positioning, upload}` |

## 📁 Structure

```
backend/
├── app/
│   ├── main.py              # Entry point
│   ├── core/                # Settings, market profiles, dependencies, exceptions, rate limiter
│   ├── api/v1/              # Routes (HTTP only), one file per notebook tab
│   ├── controllers/         # Load data, run the analytics in a worker thread, build responses (same file names)
│   ├── schemas/             # Pydantic request / response models (validation, /docs)
│   ├── common/              # Enums, response base, DataFrame serialization
│   └── services/
│       ├── cache.py         # In-memory cache
│       ├── binance/         # Binance client, prices, market data, quantities
│       ├── yahoo/           # Yahoo Finance prices and FX (cached), on top of src/Yahoo_API.py
│       └── account/         # Real portfolio: Binance account or Excel files (GitHub storage)
├── tests/
└── requirements.txt
```

## 📝 Logs

- Console: stdout
- File: `backend/logs/app.log`

## 🔗 Frontend

The React frontend in [`../frontend`](../frontend/README.md) calls this API at `VITE_API_URL` (set by the launchers). Allowed browser origins are in `CORS_ORIGINS` (`app/core/config.py`): ports 5173 and 5174 by default.

See also [`../CLAUDE.md`](../CLAUDE.md) for the project overview.
