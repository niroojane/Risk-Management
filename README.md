# 📊 Crypto Portfolio Management & Risk Analysis Platform

An interactive portfolio management application built with **Streamlit** and **Ipywidgets**, designed for **portfolio optimization, risk analysis, and strategy backtesting** in cryptocurrency markets.

This project provides a modular and extensible framework for analyzing portfolios, constructing optimal allocations, and evaluating investment strategies using real market data.

---

## 🚀 Key Features

### 📈 Portfolio Analytics

Comprehensive performance and risk analysis:

* **Performance Metrics**

  * Total return (since inception & YTD)
  * Annualized returns

* **Risk Metrics**

  * Volatility (daily & monthly)
  * Maximum drawdown
  * Conditional Value at Risk (CVaR)

* **Visualizations**

  * Portfolio value evolution
  * Drawdown curves
  * Rolling volatility
  * Calendar-based performance
  * Principal Component Analysis (PCA)
  * Risk contribution by asset

---

### ⚖️ Portfolio Optimization

Multiple allocation frameworks for robust portfolio construction:

* Maximum Sharpe Ratio
* Minimum Variance
* Risk Parity
* Maximum Diversification
* Equal Weight Portfolio

Supports realistic portfolio construction through flexible constraints.

---

### 🔒 Constraint Engine

Dynamic and customizable constraint system:

* Asset-level constraints (≥, ≤, =)
* Global diversification constraints
* Interactive UI for adding/removing constraints

---

### 🔁 Rebalancing Engine

Evaluate and compare portfolio strategies:

* Buy & Hold
* Periodic rebalancing:

  * Monthly
  * Quarterly
  * Yearly

Supports dynamic portfolio adjustments over time.

---

### 📊 Efficient Frontier & Allocation Insights

* Interactive efficient frontier visualization
* Portfolio overlays
* Sharpe ratio heatmap
* Correlation matrix

---

### 💰 P&L & Position Analysis

* Profit & Loss computation using historical positions
* Strategy comparison (Strategic vs Tactical Allocation)
* Portfolio positioning analysis

---

### 🧩 Risk Decomposition

Advanced breakdown of portfolio risk:

* Asset-level risk contributions
* Value at Risk (VaR) analysis
* P&L attribution
* Historical contribution to volatility and tracking error
* Market risk exposure analysis

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

### 3. Configure environment

Create a `.env` file (recommended) and add:

```
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret
GITHUB_TOKEN=your_token
```

> ⚠️ Never expose your API keys publicly.
> ⚠️ Make sure to have the relevant Excel Files to Analyze your P&L and Positioning through time

---

### ▶️ Run the Application

#### Streamlit App

```bash
streamlit run Streamlit_App.py
```

#### Jupyter / Ipywidgets

```bash
jupyter notebook Crypto_App.ipynb
```
---

## 📦 Dependencies

Core libraries:

* pandas, numpy, scipy
* matplotlib, plotly, seaborn
* statsmodels
* streamlit, ipywidgets
* yfinance
* openpyxl
* requests, beautifulsoup4
* binance_connector

---

## 🧱 Project Structure

```
├── src/
│   ├── Binance_API.py        # Market data retrieval (Binance)
│   ├── PnL_Computation.py    # Portfolio P&L calculations
│   ├── RiskMetrics.py        # Risk and portfolio analytics
│   ├── Rebalancing.py        # Rebalancing strategies
│   ├── Metrics.py            # Performance metrics
│   ├── Git.py                # GitHub integration
│   └── __init__.py
│
├── Crypto_App.ipynb          # Ipywidgets interface
├── Crypto_App.py             # Ipywidgets script
├── Streamlit_App.py          # Streamlit application
├── requirements.txt
├── Trade_History.xlsx        # Trades Excel File
├── Positions.xlsx            # Marke To Market History
├── Quantities.xlsx           # Historical Quantities
├── .streamlit/
└── README.md
```

---

## 🧠 Use Cases

* Portfolio construction and optimization
* Risk monitoring and reporting
* Strategy comparison (Buy & Hold vs Rebalancing)
* Crypto asset allocation research
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
