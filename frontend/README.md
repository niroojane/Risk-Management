# Risk Management - Frontend

React + TypeScript interface of the Risk Management web app. It reproduces the tabs and sub-tabs of the Crypto App and Multi Asset App notebooks: investment universe, strategy optimization and backtests, current portfolio P&L, risk analysis, VaR and market risk.

## Tech Stack

- **React 19** + **TypeScript**, built with **Vite 7**
- **Tailwind CSS 4** (styling), Radix UI primitives
- **React Router 7** (nested tab routes)
- **TanStack Query** (server data, cache) and **Zustand** (workspace state, persisted in the browser)
- **TradingView Lightweight Charts** (date-indexed line charts) and **Apache ECharts** (bars, heatmaps, scatter, histograms)
- **Axios** (HTTP client)

## Getting Started

The launchers at the project root (`start-binance.bat`, `start-yahoo.bat`) install and start everything. Manually:

```bash
npm install
npm run dev            # http://localhost:5173
```

| Command | Description |
|---|---|
| `npm run dev` | Development server |
| `npm run build` | Type check + production build (`dist/`) |
| `npm run preview` | Serve the production build |
| `npm run lint` / `npm run lint:fix` | ESLint (with Prettier) |
| `npm run format` / `npm run format:check` | Prettier |

## Configuration

The frontend reads the single `.env` file at the **project root**, shared with the backend (`envDir` in `vite.config.ts`). Only `VITE_*` variables reach the browser:

```env
VITE_API_URL=http://localhost:8000   # backend URL (the launchers set it: 8000 for Binance, 8001 for Yahoo)
```

At startup the app loads the backend's market profile (`GET /api/v1/profile`) and adapts to it. In the crypto version the universe is the top N market caps, the benchmark is Bitcoin, and the Market Cap and Prices pages are shown. In the multi-asset version you get the Yahoo ticker search and details, a base currency setting and the `^GSPC` benchmark.

## Structure

```
src/
├── components/
│   ├── ui/            # Controls (button, input, slider, alert), fields, panels, loading, error boundaries
│   ├── data/          # DataTable, TimeSeriesChart (Lightweight Charts), EChart, FrameChart
│   └── layout/        # Layout, Sidebar, TabLayout, ProfileProvider
├── pages/             # One folder per notebook tab
│   ├── Universe/      # Investment Universe (+ crypto-only Market Cap, Prices)
│   ├── Strategy/      # Strategy, Strategy Return
│   ├── CurrentPortfolio/
│   ├── RiskAnalysis/
│   ├── MarketRisk/
│   └── shared/        # Shared by several pages (Positioning, guards, asset tables...)
├── routes/            # Route tree (routes.config.ts) mirroring the notebook tabs
├── services/          # API clients (workspace, universe, profile)
├── store/             # Zustand workspace store
├── hooks/             # useWorkspace, useProfile, useSeriesPair
├── types/             # API types
└── utils/             # Formatters, frame helpers, cn (class names)
```

## Pages

| Route | Notebook tab |
|---|---|
| `/universe/overview` (+ `market-cap`, `prices` for crypto) | Investment Universe |
| `/strategy/{builder, positioning, returns}` | Strategy › Strategy / Positioning / Strategy Return |
| `/portfolio/pnl/{analysis, returns, beta}`, `/portfolio/{positioning, calendar}` | Current Portfolio |
| `/risk/volatility/{contribution, trajectory, tracking-error}`, `/risk/var/{simulation, history}` | Risk Analysis |
| `/market-risk/{pca, correlation, drivers}` | Market Risk |

## Backend

The API is in [`../backend`](../backend/README.md). The backend must allow the frontend's origin (`CORS_ORIGINS`: ports 5173 and 5174 by default).
