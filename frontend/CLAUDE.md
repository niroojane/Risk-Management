# CLAUDE.md

This file provides guidance to Claude Code when working with the frontend codebase.

## Project Overview

React + TypeScript frontend of the Risk-Management web app. It replaces the Jupyter notebook interface (Crypto App and Multi Asset App) and talks to the FastAPI backend in `/backend`.

**Main features**: portfolio optimization and rolling backtests, risk metrics (VaR/CVaR, risk contribution, tracking error), P&L of the real portfolio, market risk (PCA, correlation, market drivers), interactive charts.

## Tech Stack

- **React 19** + **TypeScript**, **Vite 7**
- **React Router 7** (nested tab routes)
- **Zustand** (client state, persisted workspace)
- **TanStack Query** (server state, API cache)
- **Tailwind CSS 4** (styling)
- **Lightweight Charts 5.2.1** (line charts) and **ECharts 6.1.0** (other charts), pinned to exact versions

## Essential Commands

```bash
npm install          # Install
npm run dev          # Dev server (http://localhost:5173)
npm run build        # Type check + production build
npm run lint         # ESLint + Prettier
```

## Architecture

### Key Principles

1. **State management**
   - **Zustand** (`src/store/workspaceStore.ts`): the notebook's shared state (universe, date ranges, constraints, overlays, allocation grid, backtest, dropdown selections), persisted in localStorage (`risk-management-workspace`, with a version + migrate)
   - **TanStack Query**: server data. Views are button-driven with `useView` (`src/hooks/useWorkspace.ts`), like the notebook's buttons: results are cached per parameters and kept on screen when they change. Pass `auto` for views that should load on their own. Rolling views whose values don't depend on the date range (Risk Trajectory, Tracking Error, VaR History, Market Drivers: the first window reaches back before the start date, and the market index is simulated on the whole history) use `useRangeView` instead: a date range inside the loaded one is sliced in the browser, and a run loads the union of both ranges. Market Drivers then rebases its performance and counts its P&L from the first date (`rebaseFrame`, `fromFirstRow`).

2. **Market profile**
   - `ProfileProvider` (`src/components/layout/ProfileProvider.tsx`) loads `GET /api/v1/profile` before rendering. `useProfile()` / `useIsMultiAsset()` (`src/hooks/useProfile.ts`) expose it.
   - Never hardcode crypto assumptions. Use `useBenchmark()` (label `Bitcoin` / `Benchmark`, ticker `BTCUSDT` / `CSPX.L`), `profile.cash_assets`, `profile.excluded_symbols` and `profile.include_holdings_in_universe`.
   - Routes can be restricted to a market with `markets` in `routes.config.ts` (`routesFor(market)`).

3. **Feature-based structure**
   - 1 page folder = 1 notebook tab (`src/pages/<Tab>/`), with its own `components/` when needed
   - Shared page components in `src/pages/shared/`

4. **API services**
   - All API calls in `src/services/` (`workspaceService.ts`, `universeService.ts`, `profileService.ts`)
   - Axios client in `src/services/api.ts`, base URL from `VITE_API_URL`

5. **Light / dark mode**
   - `useThemeStore` (`src/store/themeStore.ts`), persisted as `risk-management-theme`: the OS preference until the user picks a mode with the sidebar's `ThemeToggle`. It sets the `dark` class on `<html>` (Tailwind's `dark:` variant, the `.dark` tokens of `index.css`). An inline script in `index.html` applies the saved mode before the first paint.
   - Charts take their colours from `useChartTheme()` (`src/hooks/useTheme.ts`): a chart option built in a `useMemo` lists it in its dependencies, so it follows a switch.

### Mapping Backend / Frontend

Routes mirror the notebook tabs (`src/routes/routes.config.ts`). Groups render a tab bar (`TabLayout`).

| Frontend route | Notebook tab | Backend endpoints |
|----------------|--------------|-------------------|
| `/universe/overview` (+ `market-cap`, `prices` for crypto) | Investment Universe | `/investment-universe/*`, `/universe/*` (Yahoo), `/account/holdings` |
| `/strategy/{builder,positioning,returns}` | Strategy › Strategy / Positioning / Strategy Return | `/strategy/{optimize,backtest}`, `/portfolio/{performance,calendar}`, `/account/*` |
| `/portfolio/pnl/{analysis,returns,beta}`, `/portfolio/{positioning,calendar}` | Current Portfolio › P&L / Positioning / Calendar Return | `/portfolio/*`, `/account/*` |
| `/risk/volatility/{contribution,trajectory,tracking-error}`, `/risk/var/{simulation,history}` | Risk Analysis | `/risk/*`, `/metrics/var` |
| `/market-risk/{pca,correlation,drivers}` | Market Risk | `/market-risk/{pca-analysis,correlation-analysis,drivers}` |

Workspace views send the named series with `useWorkspacePayload`: the allocations, the Fund / Core / Overlay schedules, the benchmark and the Historical Portfolio. Results come back as pandas frames in split layout (`Frame`: `index`, `columns`, `data`).

### Charts

`src/components/data`:
- `TimeSeriesChart`: TradingView Lightweight Charts, for date-indexed lines. It has a clickable legend and shows values under the crosshair.
- `EChart`: Apache ECharts (tree-shaken), for bars, heatmaps, scatter and histograms.
- `FrameChart`: picks between the two for a `Frame`. Pass `visible` to choose the series shown at first.

### Tables

Every table, the Market Cap and Prices explorers included, is a `DataTable` (`src/components/data`) fed a `Frame`, with a per-column `format` (`number` / `percent` / `currency`).

### Components

- `@/components/ui`: app building blocks (`Field`, `SelectField`, `DateField`, `RangeFields`, `Toolbar`, `Panel`, `RunButton`, `Notice`, `ViewStatus`, `Loading`, error boundaries). The basic shadcn controls are imported by path (`@/components/ui/button`, `input`, `slider`, `alert`).
- `@/components/data`: `DataTable` and the charts.
- `@/components/layout`: `Layout`, `Sidebar`, `ThemeToggle`, `TabLayout`, `ProfileProvider`.
- `cn()` (class name merge) is in `@/utils/cn`.

### Environment Variables

Read from the single `.env` at the project root (`envDir` in `vite.config.ts`), shared with the backend; only `VITE_*` variables are exposed:

```env
VITE_API_URL=http://localhost:8000    # Backend API (start-*.bat sets it)
```

## Development Patterns

### Adding a page

1. Create `src/pages/<Tab>/<Page>.tsx` (default export)
2. Add the API call to the matching service in `src/services/`, with its types in `src/types/`
3. Register it in `src/routes/routes.config.ts` (lazy-loaded; add `markets` if it only applies to one market)
4. Fetch with `useView` (button-driven) or `useQuery`

### API calls

```typescript
// src/services/workspaceService.ts -- post() prefixes /api/v1 and returns a ViewResponse<T>
export const workspaceService = {
  riskTrajectory: (params: WorkspacePayload & { window: number }) =>
    post<RiskTrajectoryView>('/risk/trajectory', params),
};

// In a page
const view = useView('risk-trajectory', params, workspaceService.riskTrajectory);
// <RunButton onClick={view.run} loading={view.isFetching}>  <ViewStatus {...view} />
```

### TypeScript

Always type API responses (`src/types/workspace.ts`, `universe.ts`, `profile.ts`).

## Important Implementation Details

- **Constraints** (Strategy page): asset-level weight bounds (one asset or `All`), and risk limits (volatility, beta, tracking error, information ratio) relative to a benchmark allocation, the same as in the notebook.
- **VaR**: the Value at Risk page runs the backend's simulation methods (multivariate, Gaussian / t / Gumbel copulas, Monte Carlo), plus historical and parametric VaR. A stress grid shocks volatilities, correlations and expected returns.
- **Dates**: `yyyy-MM-dd` strings, timezone-naive like the backend. Rebalancing frequencies: Weekly, Monthly, Quarterly, Yearly.
- **Performance**: pages are lazy-loaded; long computations use a 15-minute request timeout.

## Best Practices

- **TypeScript**: type props, state and return values
- **Performance**: React.memo, useMemo and useCallback when needed
- **Errors**: show API errors with `apiErrorMessage` / `ViewStatus`, never fail silently
- **Lint**: `react-refresh/only-export-components`, so keep hooks and helpers out of component files

## Backend

The backend runs on `http://localhost:8000` (Binance) or `8001` (Yahoo). See [`/backend/README.md`](../backend/README.md). CORS must allow the frontend's origin (`CORS_ORIGINS`: 5173 and 5174 by default).
