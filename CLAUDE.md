# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Risk-Management is a portfolio management and risk analysis system in Python: portfolio optimization, risk metrics (VaR, CVaR), P&L tracking, backtesting and interactive visualization. It comes in three forms:

- **Jupyter notebook apps** (ipywidgets): `Crypto App.ipynb` (Binance), `Multi Asset App.ipynb` (Yahoo Finance + Excel portfolio), `HMM Regime App.ipynb` (regime-based strategies)
- **Streamlit app**: `Streamlit_App.py`
- **Web app**: `backend/` (FastAPI) + `frontend/` (React + TypeScript), mirroring the Crypto App and Multi Asset App notebooks. Each folder has its own `CLAUDE.md`.

## Architecture

### Core Library (`src/`)

Shared by the notebooks and Streamlit:

- **Binance_API.py**: Binance API interactions (market data, prices, positions, trades)
- **Yahoo_API.py**: Yahoo Finance search, prices, ticker details, FX conversion to a base currency
- **RiskMetrics.py**: Core quantitative finance engine:
  - `Portfolio` class: portfolio construction and optimization
  - `RiskAnalysis` class (extends Portfolio): VaR simulations, PCA, variance decomposition, copula models
- **Metrics.py**: Performance / risk tables, calendar metrics, efficient frontier
- **Rebalancing.py**: Buy-and-hold, periodic and dynamic rebalancing, book cost
- **PnL_Computation.py**: P&L, book costs, realized / unrealized P&L from Binance trade history
- **PositionHandler.py**: Positions / Quantities Excel files of the multi-asset portfolio
- **Stock_Data.py**: Legacy Yahoo Finance close loader
- **Git.py**: GitHub API integration for pushing Excel reports to the repository
- **PPTx.py**: PowerPoint export (optional dependency)
- **Crypto_App.py** (project root): the Crypto App UI as an importable module

### Web App (`backend/` + `frontend/`)

- The backend ports the `src/` analytics to `backend/app/services/analytics/` (parity verified) and exposes them through FastAPI. Layers: routes (`api/v1`) → controllers → services.
- A market profile chosen with the `MARKET` environment variable selects the data sources. `crypto` uses Binance prices and the Binance account. `multi_asset` uses Yahoo Finance prices converted to a base currency, and the Excel portfolio in `ETF/` on GitHub.
- The frontend reads `GET /api/v1/profile` at startup (benchmark, cash assets, crypto-only pages) and mirrors the notebook tabs and sub-tabs.

### Key Design Patterns

**Class Inheritance**: `RiskAnalysis` extends `Portfolio` to add risk-specific functionality while reusing core portfolio methods.

**Strategy Pattern**: Portfolio optimization supports multiple objectives (`minimum_variance`, `sharpe_ratio`, `risk_parity`, `maximum_diversification`, `eigenportfolio`, `tracking_error`, `information_ratio`) passed as strings to the `optimize()` method.

**Data Flow**:
1. Market data fetched via `BinanceAPI` or `Yahoo_API`
2. Returns computed and passed to `RiskAnalysis`
3. Optimization produces weights
4. Weights fed to rebalancing functions for backtesting
5. Results visualized through interactive widgets (notebooks) or the React frontend (web app)

### State Management (notebooks)

The notebook apps use global variables in `Crypto_App.py` to maintain state across widget interactions:
- `prices`, `returns_to_use`: Market data
- `dataframe`: Cleaned price data
- `rolling_optimization`: Time-series of optimal allocations
- `performance_fund`, `performance_pct`: Portfolio performance metrics
- `quantities`: Position sizes over time
- `grid.data`: Current allocation matrix (editable DataGrid widget)

## Common Development Commands

### Notebooks and Streamlit
```bash
pip install -r requirements.txt
jupyter notebook "Crypto App.ipynb"     # then run all cells
streamlit run Streamlit_App.py
```

### Web App
- `start-binance.bat`: crypto profile (`MARKET=crypto`), backend :8000, app http://localhost:5173
- `start-yahoo.bat`: multi-asset profile (`MARKET=multi_asset`), backend :8001, app http://localhost:5174
- Both call `scripts/launch.bat`, which creates `backend/.venv` and installs the packages on the first run. They can run side by side, and each origin keeps its own workspace in the browser.
- Backend tests: `cd backend && pytest`. Frontend checks: `cd frontend && npm run lint && npm run build`.

### Testing Individual Modules
```python
# Test Binance API connection
from src.Binance_API import BinanceAPI
api = BinanceAPI(api_key, api_secret)
market_cap = api.get_market_cap()

# Test portfolio optimization
from src.RiskMetrics import RiskAnalysis
import pandas as pd
returns = pd.DataFrame(...)  # Your returns data
portfolio = RiskAnalysis(returns)
weights = portfolio.optimize('sharpe_ratio')

# Test rebalancing
from src.Rebalancing import rebalanced_portfolio
rebal_values = rebalanced_portfolio(prices, weights, frequency='Monthly')
```

## Important Implementation Details

### Optimization Constraints

Constraints are built dynamically from user input in the UI:
- Asset-level constraints: `create_constraint(sign, limit, position)`
- Portfolio-level constraints: `diversification_constraint(sign, limit)`
- Risk constraints (volatility, beta, tracking error, information ratio) relative to a benchmark allocation
- All constraints combined with `sum_equal_one` equality constraint in `Portfolio.optimize()`

### VaR Calculation Methods

The `RiskAnalysis` class implements these VaR approaches:
1. **Historical VaR**: Empirical quantile from return distribution
2. **Parametric VaR**: Assumes normal distribution
3. **Multivariate Distribution**: Correlated normal simulation
4. **Copula-based VaR**: Gaussian, t-Student, and Gumbel copulas to model tail dependencies
5. **Monte Carlo**: Geometric Brownian motion with Cholesky decomposition for correlation

### PnL Calculation Quirks

- `PnL_Computation.get_trade_in_usdt()` handles cross-pairs (e.g., ETHBTC) by converting to USDT terms using interpolated minute-level prices
- Book cost uses cumulative averaging: `(total.shift(-1) + total) / (quantities.shift(-1) + quantities)`
- Realized PnL only computed on SELL transactions
- Multi-asset portfolio: average-cost ledger in each asset's trading currency, with fees, translated to the base currency with the day's FX

### Rebalancing Logic

Two rebalancing modes:
- **Static weights** (`rebalanced_portfolio`): Fixed allocation rebalanced at specified frequency
- **Dynamic weights** (`rebalanced_dynamic_quantities`): Allocation changes over time based on rolling optimization matrix

## Data Dependencies

### External APIs
- **Binance Spot API**: Market data, account positions, trade history (requires API key/secret)
- **Yahoo Finance**: Prices, FX rates, symbol search and ticker details via `yfinance`
- **GitHub API**: Pushes the Positions / Quantities Excel files to the repository (requires a personal access token)

### Excel Files
- Crypto (`BinancePTF/` on GitHub): `Positions.xlsx`, `Quantities.xlsx`, `Trade History Reconstructed.xlsx`
- Multi-asset (`ETF/` on GitHub): `Current Portfolio2.xlsx`, `Trade History2.xlsx`, `Positions2.xlsx`, `Quantities2.xlsx`

## Notebook UI Structure

The Crypto App notebook (and the web app) has 5 main tabs:
1. **Investment Universe**: Select the universe (top N crypto by market cap, or Yahoo tickers), fetch prices, asset return / risk tables
2. **Strategy**: Strategy (optimization, constraints, allocation grid) / Positioning / Strategy Return
3. **Current Portfolio**: P&L (P&L Analysis, Return Analysis, Beta Analysis) / Positioning / Calendar Return
4. **Risk Analysis**: Volatility Analysis (Risk Contribution, Risk Trajectory, Tracking Error) / Value at Risk (Value at Risk, Value at Risk History)
5. **Market Risk**: Market Risk (PCA) / Correlation / Market Drivers

## Common Patterns

### Working with the Allocation Grid
```python
# The grid.data is a pandas DataFrame with allocations as rows
# Access current allocation:
current_weights = grid.data.loc['Optimal Portfolio']

# Add new allocation:
new_row = pd.DataFrame([weights], columns=grid.data.columns, index=['My Strategy'])
grid.data = pd.concat([grid.data, new_row])
```

### Adding New Optimization Objectives
1. Define objective function in `RiskMetrics.Portfolio.optimize()`
2. Add to `dico_strategies` in `Crypto_App.display_crypto_app()`
3. Function should take `weights` and return scalar to minimize
4. For the web app: port it to `backend/app/services/analytics/risk_metrics.py` and add it to the `Objective` type of the frontend

### Date Handling
- All dates normalized to timezone-naive pandas DatetimeIndex
- Rebalancing dates computed using pandas offsets (BMonthEnd, BQuarterEnd, BYearEnd)
- Historical data fetched in 500-day chunks due to Binance API limits

## Security Notes

- Notebooks and Streamlit read credentials from `keys.py` (project root); `src/Git.py` only has empty placeholders.
- The web app reads them from the single `.env` at the project root (template: `.env.example`), shared by backend and frontend; only `VITE_*` variables reach the browser.
- Never commit `.env` or `keys.py`; `.env` is in the root `.gitignore`.
