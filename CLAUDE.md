# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Risk-Management is a cryptocurrency portfolio management and risk analysis system built with Python. The application provides portfolio optimization, risk metrics calculation (VaR, CVaR), PnL tracking, and interactive visualization through a Jupyter notebook interface. It integrates with Binance API for live market data and position tracking.

## Architecture

### Core Module Structure

The codebase follows a modular architecture with clear separation of concerns:

- **Binance_API.py**: Handles all Binance API interactions (market data, prices, positions, trades)
- **RiskMetrics.py**: Core quantitative finance engine containing:
  - `Portfolio` class: Basic portfolio construction and optimization
  - `RiskAnalysis` class (extends Portfolio): Advanced risk metrics including VaR simulations, PCA, variance decomposition, copula models
- **PnL_Computation.py**: Calculates profit/loss, book costs, and realized/unrealized PnL from trade history
- **Rebalancing.py**: Portfolio rebalancing logic (buy-and-hold vs. periodic rebalancing)
- **Stock_Data.py**: Yahoo Finance integration for traditional equity data
- **Git.py**: GitHub API integration for pushing Excel reports to repository
- **Crypto_App.py**: Main application UI orchestrator using ipywidgets (tabbed interface)

### Key Design Patterns

**Class Inheritance**: `RiskAnalysis` extends `Portfolio` to add risk-specific functionality while reusing core portfolio methods.

**Strategy Pattern**: Portfolio optimization supports multiple objectives (`minimum_variance`, `sharpe_ratio`, `risk_parity`) passed as strings to the `optimize()` method.

**Data Flow**:
1. Market data fetched via `BinanceAPI` or `Stock_Data`
2. Returns computed and passed to `RiskAnalysis`
3. Optimization produces weights
4. Weights fed to rebalancing functions for backtesting
5. Results visualized through interactive widgets

### State Management

The application uses global variables in `Crypto_App.py` to maintain state across widget interactions:
- `prices`, `returns_to_use`: Market data
- `dataframe`: Cleaned price data
- `rolling_optimization`: Time-series of optimal allocations
- `performance_fund`, `performance_pct`: Portfolio performance metrics
- `quantities`: Position sizes over time
- `grid.data`: Current allocation matrix (editable DataGrid widget)

## Common Development Commands

### Environment Setup
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
jupyter notebook "Crypto App.ipynb"
# Then execute all cells to launch the interactive UI
```

### Testing Individual Modules
```python
# Test Binance API connection
from Binance_API import BinanceAPI
api = BinanceAPI(api_key, api_secret)
market_cap = api.get_market_cap()

# Test portfolio optimization
from RiskMetrics import RiskAnalysis
import pandas as pd
returns = pd.DataFrame(...)  # Your returns data
portfolio = RiskAnalysis(returns)
weights = portfolio.optimize('sharpe_ratio')

# Test rebalancing
from Rebalancing import rebalanced_portfolio
rebal_values = rebalanced_portfolio(prices, weights, frequency='Monthly')
```

## Important Implementation Details

### Optimization Constraints

Constraints are built dynamically from user input in the UI:
- Asset-level constraints: `create_constraint(sign, limit, position)`
- Portfolio-level constraints: `diversification_constraint(sign, limit)`
- All constraints combined with `sum_equal_one` equality constraint in `Portfolio.optimize()`

### VaR Calculation Methods

The `RiskAnalysis` class implements 5 VaR approaches:
1. **Historical VaR**: Empirical quantile from return distribution
2. **Parametric VaR**: Assumes normal distribution
3. **Multivariate Distribution**: Correlated normal simulation
4. **Copula-based VaR**: Gaussian, t-Student, and Gumbel copulas to model tail dependencies
5. **Monte Carlo**: Geometric Brownian motion with Cholesky decomposition for correlation

### PnL Calculation Quirks

- `PnL_Computation.get_trade_in_usdt()` handles cross-pairs (e.g., ETHBTC) by converting to USDT terms using interpolated minute-level prices
- Book cost uses cumulative averaging: `(total.shift(-1) + total) / (quantities.shift(-1) + quantities)`
- Realized PnL only computed on SELL transactions

### Rebalancing Logic

Two rebalancing modes:
- **Static weights** (`rebalanced_portfolio`): Fixed allocation rebalanced at specified frequency
- **Dynamic weights** (`rebalanced_dynamic_quantities`): Allocation changes over time based on rolling optimization matrix

## Data Dependencies

### External APIs
- **Binance Spot API**: Market data, account positions, trade history (requires API key/secret)
- **Yahoo Finance**: Traditional stock data via `yfinance` library
- **GitHub API**: Used to push Excel position/quantity files to repository (requires personal access token)

### Excel Files
- `Positions.xlsx`: Historical portfolio values by asset (loaded from GitHub)
- `Quantities.xlsx`: Historical position quantities (loaded from GitHub)
- `Trade History Reconstructed.xlsx`: Manual trade history for PnL reconstruction

## Widget UI Structure

The Jupyter notebook creates a tabbed interface with 10 tabs:
1. **Investment Universe**: Select top N crypto by market cap, fetch prices
2. **Strategy**: Portfolio optimization with constraints, allocation grid
3. **Positioning**: Current positions vs. model, PnL breakdown
4. **Strategy Return**: Performance charts, drawdown, rolling volatility
5. **Ex Post Metrics**: Actual portfolio performance from historical positions
6. **Calendar Metrics**: Yearly/monthly return heatmaps
7. **Ex Ante Metrics**: Variance contribution, tracking error forecasts
8. **Value at Risk Metrics**: VaR/CVaR across 5 simulation methods
9. **Market Risk**: PCA analysis, eigen portfolios
10. **Correlation**: Asset correlation matrices, rolling correlations

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

### Date Handling
- All dates normalized to timezone-naive pandas DatetimeIndex
- Rebalancing dates computed using pandas offsets (BMonthEnd, BQuarterEnd, BYearEnd)
- Historical data fetched in 500-day chunks due to Binance API limits

## Security Notes

- API keys stored in `Git.py` (currently empty placeholders)
- Never commit filled API keys - use environment variables in production
- The `.claudeignore` file excludes certain files from Claude's context
