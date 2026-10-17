# 📊 Portfolio Management & Risk Analysis Platform

Interactive portfolio management apps built with **ipywidgets** (Jupyter) and **Streamlit**. They cover **portfolio optimization, risk analysis, P&L and strategy backtesting**, for crypto (Binance) and multi-asset universes (ETFs, stocks, indices via Yahoo Finance).

The analytics live in a shared library (`src/`) used by every app.

---

## 🧭 The Apps

| App | Data | What it does |
|---|---|---|
| **Crypto App** (`Crypto App.ipynb`, `Crypto_App.py`) | Binance | Optimization, rolling backtests, P&L from your Binance positions, risk and VaR analysis |
| **Multi Asset App** (`Multi Asset App.ipynb`) | Yahoo Finance + Excel positions / trades | Same toolkit for ETFs, stocks and indices: Yahoo search bar, predefined universe, prices converted to a base currency |
| **HMM Regime App** (`HMM Regime App.ipynb`) | Yahoo Finance or CSV / Excel | Detects market regimes with a Hidden Markov Model and backtests a different strategy in each regime |
| **Streamlit App** (`Streamlit_App.py`) | Binance | Web version of the Crypto App |

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
* Settings: number of states, covariance type, restarts, training window, walk-forward refits, signal confirmation, and BIC model selection.
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

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Tested with Python 3.13 and the exact versions in `requirements.txt`.

### 3. Add your keys

The apps import their credentials from a `keys.py` file at the project root:

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

> ⚠️ Never commit or push `keys.py`; add it to your `.gitignore`.
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
│   ├── Binance_API.py        # Binance market data and account
│   ├── Yahoo_API.py          # Yahoo Finance search, prices, ticker details, FX conversion
│   ├── Stock_Data.py         # Yahoo Finance closes (legacy loader)
│   ├── PnL_Computation.py    # Portfolio P&L from Binance trades
│   ├── PositionHandler.py    # Positions / quantities Excel files
│   ├── Git.py                # GitHub integration
│   ├── PPTx.py               # PowerPoint export
│   └── __init__.py
│
├── Crypto App.ipynb          # Crypto app (ipywidgets)
├── Crypto_App.py             # Same app as an importable module
├── Multi Asset App.ipynb     # Multi-asset app (ipywidgets)
├── HMM Regime App.ipynb      # Regime detection & regime-based backtests (ipywidgets)
├── Streamlit_App.py          # Streamlit application
├── keys.py                   # Your credentials (not versioned)
├── requirements.txt
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
