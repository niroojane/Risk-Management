# 📊 Portfolio Management & Risk Analysis Platform

Interactive portfolio management apps built with **ipywidgets** (Jupyter), **Streamlit** and a **web app** (FastAPI + React). They cover **portfolio optimization, risk analysis, P&L and strategy backtesting**, for crypto (Binance) and multi-asset universes (ETFs, stocks, indices via Yahoo Finance).

The analytics live in one shared library (`src/`) used by the notebooks, Streamlit and the web app's backend.

---

## 🧭 The Apps

| App | Data | What it does |
|---|---|---|
| **Crypto App** (`Crypto App.ipynb`, `Crypto_App.py`) | Binance | Optimization, rolling backtests, P&L from your Binance positions, risk and VaR analysis |
| **Multi Asset App** (`Multi Asset App.ipynb`) | Yahoo Finance + Excel positions / trades | Same toolkit for ETFs, stocks and indices: Yahoo search bar, predefined universe, prices converted to a base currency |
| **HMM Regime App** (`HMM Regime App.ipynb`) | Yahoo Finance or CSV / Excel | Detects market regimes with a Hidden Markov Model and backtests a different strategy in each regime |
| **Streamlit App** (`Streamlit_App.py`) | Binance | Web version of the Crypto App |
| **Web App** (`backend/` + `frontend/`) | Binance, or Yahoo Finance + Excel positions / trades | Browser version of the Crypto App and Multi Asset App, with the same tabs and sub-tabs. Launched with `start-binance.bat` or `start-yahoo.bat` |

---

## 🚀 Key Features

### ⚖️ Portfolio Optimization

Long-only, fully-invested portfolios:

* Maximum Sharpe Ratio
* Minimum Variance
* Risk Parity
* Maximum Diversification
* Eigen Portfolio
* **Minimum Tracking Error** and **Maximum Information Ratio**, both relative to a benchmark allocation
* Equal Weight

Constrained and unconstrained versions are computed side by side. Strategy overlays let you combine a core strategy with tactical sleeves.

In the Multi Asset App and the web app, every scenario of the HMM Regime App is a strategy too (**Regime · &lt;scenario&gt;**): the regime in force picks the strategy and constraints at each rebalancing, and it can be the core or an overlay of any other strategy.

### 🔒 Constraint Engine

* **Asset constraints**: one asset `≥ / ≤ / =` a weight, or every asset at once (`All ≤ 0.3` caps each weight at 30%).
* **Risk constraints**, all ex-ante and annualized:
  * Volatility
  * Beta to the benchmark allocation
  * Tracking error to the benchmark allocation
  * Information ratio to the benchmark allocation

Limits are in decimals (`0.05` = 5%); the information ratio is a ratio (`0.5`). If constraints conflict and can't all be met, a warning is raised instead of returning weights that silently break them.

### 🔁 Backtesting & Rebalancing

* Buy & Hold and periodic rebalancing: weekly, monthly, quarterly, yearly
* Rolling re-optimization at each rebalancing date, with constraints rebuilt on each window
* Transaction fees on the traded amount (`rebalanced_dynamic_quantities`)

### 🌦️ Regime-Based Strategies (HMM Regime App)

* Gaussian HMM on features built per asset class:
  * returns and volatility
  * a PCA market factor
  * average correlation
  * drawdown
* Settings: number of states, covariance type, restarts, training window, walk-forward refits (growing or sliding window), signal confirmation, and BIC model selection.
* **No look-ahead by default**: the regime on day *t* only uses data up to *t* (filtered probabilities), and weights decided at *t* earn the returns of *t+1*.
* Each regime gets its own strategy, exposure (the rest in cash), asset constraints and risk limits.
* Results:
  * performance, drawdown, rolling volatility and correlation, with the regime shaded behind each chart
  * metrics by regime
  * a weights history and a log of every rebalancing decision
* Benchmarks: a static strategy, any loaded asset, or other portfolios' returns (e.g. the Crypto App's `global_returns`).

### 📈 Performance & Risk Analytics

* Returns since inception, year-to-date and annualized; calendar (yearly / monthly) returns, volatility, tracking error and Sharpe
* Volatility (daily, weekly, monthly), maximum drawdown, CVaR
* Ex-ante volatility, risk contribution (idiosyncratic vs correlation) and tracking-error decomposition over time
* Beta analysis, PCA, correlation matrices, efficient frontier

### 🧩 Value at Risk & Stress Testing

* In the apps: multivariate normal, Gaussian copula, Student-t copula, Gumbel copula and Monte Carlo VaR / CVaR, plus their history over time
* Stress grid: the diagonal multiplies each asset's volatility; the off-diagonal adds correlation shocks; expected returns can be shocked too
* In `src/RiskMetrics.py` as well: historical and parametric VaR, rolling VaR and the Kupiec backtest

### 💰 P&L & Positions

* P&L rebuilt from the trade history (average-cost method), realized and unrealized
* Positions and quantities history; ex-post performance of the actual portfolio vs the model allocations

---

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/niroojane/Risk-Management
cd Risk-Management
```

### 2. Install dependencies (notebooks and Streamlit)

```bash
pip install -r requirements.txt
```

Tested with Python 3.13 and the exact versions in `requirements.txt`.

The web app has its own dependencies (`backend/requirements.txt`, `frontend/package.json`), installed automatically by its launchers. See [Run the Apps](#️-run-the-apps).

### 3. Add your keys

The notebooks and Streamlit import their credentials from a `keys.py` file at the project root:

```python
# keys.py
binance_api_key = "your_binance_key"
binance_api_secret = "your_binance_secret"
token = "your_github_token"          # GitHub file updates (src/Git.py)
repo_owner = "your_github_user"
repo_name = "your_repo"
branch = "main"
```

The HMM Regime App needs none of them. It only uses the Binance-free Yahoo / file sources.

The web app reads the same credentials from a single `.env` file at the project root, shared by the backend and the frontend:

```bash
cp .env.example .env   # then fill in BINANCE_API_KEY, BINANCE_API_SECRET, GITHUB_TOKEN...
```

> ⚠️ Never commit or push `keys.py` or `.env`. `.env` is already in `.gitignore`; add `keys.py` too.
> ⚠️ The P&L and positioning tabs need the Excel files (trade history, positions, quantities). By default the apps read them from this repository's `BinancePTF/` and `ETF/` folders.

---

## ▶️ Run the Apps

#### Jupyter (ipywidgets)

```bash
jupyter notebook "Crypto App.ipynb"
jupyter notebook "Multi Asset App.ipynb"
jupyter notebook "HMM Regime App.ipynb"
```

Run all cells; the app appears under the last cell.

#### Streamlit

```bash
streamlit run Streamlit_App.py
```

#### Web App (Windows)

Requires Python 3.11+ and [Node.js](https://nodejs.org) LTS. Double-click one of:

| Launcher | Data | Backend | App |
|---|---|---|---|
| `start-binance.bat` | Binance prices and account | http://localhost:8000 | http://localhost:5173 |
| `start-yahoo.bat` | Yahoo Finance prices, portfolio from the `ETF/` Excel files | http://localhost:8001 | http://localhost:5174 |

The first launch creates `backend/.venv` and installs the Python and npm packages. Both versions can run side by side, and each keeps its own workspace in the browser. API documentation: `http://localhost:8000/docs` (or `8001`). See [SETUP.md](SETUP.md) for details.

**Share a temporary link:** double-click `share-yahoo.bat` (or `share-binance.bat`). It starts the app if needed, then prints a public `https://….trycloudflare.com` link (a [Cloudflare quick tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/), installed with winget on first use). The link works while your PC and its windows stay open, and changes each time. Anyone with it uses the app with your `.env` credentials, so only send it to people you trust.

---

## 📏 Conventions

* Returns are daily simple returns; volatilities, tracking errors and information ratios are annualized with **252** periods per year.
* Ex-ante measures use the covariance and mean of the selected estimation window.

---

## 🧱 Project Structure

```
├── src/
│   ├── RiskMetrics.py        # Optimization, constraints, VaR, simulations, risk decomposition
│   ├── Metrics.py            # Performance / risk tables, calendar metrics, efficient frontier
│   ├── Rebalancing.py        # Buy & hold, periodic and dynamic rebalancing, book cost
│   ├── Backtest.py           # Rolling optimization with overlays ('Get Results')
│   ├── Regime.py             # HMM regime engine and scenarios (HMM Regime App, regime strategies)
│   ├── Workspace.py          # Weight series of every portfolio and the risk / performance views
│   ├── Account.py            # Crypto holdings, positioning and P&L history
│   ├── MultiAsset.py         # Multi-asset trades, ledger, holdings and P&L
│   ├── PortfolioAnalytics.py # Whole allocation grids for the web app: constraints, optimization, VaR, asset metrics
│   ├── Binance_API.py        # Binance market data and account (also used by the web app's backend)
│   ├── Yahoo_API.py          # Yahoo Finance search, prices, ticker details, FX conversion
│   ├── Stock_Data.py         # Yahoo Finance closes (legacy loader)
│   ├── PnL_Computation.py    # Portfolio P&L from Binance trades
│   ├── PositionHandler.py    # Positions / quantities Excel files
│   ├── Git.py                # GitHub integration
│   ├── PPTx.py               # PowerPoint export
│   └── __init__.py
│
├── Crypto App.ipynb          # Crypto app (ipywidgets)
├── Crypto_App.py             # Same app as an importable module (local only, not versioned)
├── Multi Asset App.ipynb     # Multi-asset app (ipywidgets)
├── HMM Regime App.ipynb      # Regime detection & regime-based backtests (ipywidgets)
├── Streamlit_App.py          # Streamlit application
├── keys.py                   # Your credentials for the notebooks / Streamlit (not versioned)
├── requirements.txt          # Notebooks and Streamlit dependencies
│
├── backend/                  # Web app API (FastAPI) -- see backend/README.md
├── frontend/                 # Web app UI (React + TypeScript) -- see frontend/README.md
├── scripts/                  # Shared launchers (launch.bat, share.bat)
├── start-binance.bat         # Web app, crypto version
├── start-yahoo.bat           # Web app, multi-asset version
├── share-binance.bat         # Temporary public link to the crypto version
├── share-yahoo.bat           # Temporary public link to the multi-asset version
├── .env.example              # Web app settings template (copy to .env, not versioned)
├── SETUP.md                  # Detailed setup and troubleshooting
├── .streamlit/
└── README.md
```

---

## 🧠 Use Cases

* Portfolio construction and optimization under realistic constraints
* Benchmark-relative investing (tracking error / information ratio budgets)
* Regime-aware allocation research
* Risk monitoring, VaR and stress testing
* Strategy comparison (Buy & Hold vs Rebalancing vs regime-based)
* Educational tool for quantitative finance

---

📄 License

This project is licensed under the MIT License.

👤 Author

Niroojane Selvam

📬 Contact

LinkedIn

Feel free to reach out for questions, feedback, or collaboration.

⭐ If you find this project useful, consider giving it a star!
