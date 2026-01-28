# CLAUDE.md

This file provides guidance to Claude Code when working with the frontend codebase.

## Project Overview

Frontend React + TypeScript pour le système Risk-Management. Interface web moderne qui remplace le Jupyter notebook, communiquant avec le backend FastAPI situé dans `/backend`.

**Fonctionnalités principales** : Optimisation de portefeuille, métriques de risque (VaR/CVaR), calcul de PnL, visualisations interactives.

## Stack Technique

- **React 19** + **TypeScript**
- **Vite** (build tool)
- **React Router** (routing)
- **Zustand** (state client-side)
- **TanStack Query** (state server-side, cache API)
- **Tailwind CSS** (styling)

## Commandes Essentielles

```bash
npm install          # Installation
npm run dev          # Dev server (http://localhost:5173)
npm run build        # Build production
npm run lint         # Linter
```

## Architecture

### Principes Clés

1. **State Management**
   - **Zustand** : Client state (UI, user preferences, selections)
   - **TanStack Query** : Server state (API data, cache, sync)

2. **Feature-Based Structure**
   - 1 page = 1 Jupyter notebook tab
   - Each page folder contains its own `components/` subfolder
   - Example: `pages/Universe/components/MarketCapTable.tsx`

3. **Services API**
   - All API calls centralized in `src/services/`
   - One service per feature
   - Axios config in `src/services/api.ts`

### Critical Components

**⭐ AllocationGrid** (Strategy page)
- Mimics pandas DataFrame from Jupyter notebook
- Editable grid: rows = strategies, columns = asset allocations
- Must validate: weights sum to 100%
- Add/remove custom strategies
- Similar to `grid.data` in notebook

**⭐ Heatmap** (Calendar Metrics)
- Monthly/yearly returns visualization
- Color-coded (green = positive, red = negative)
- Same as notebook's calendar view

**⭐ VaRComparison** (VaR Metrics)
- Side-by-side comparison of 5 VaR calculation methods
- Historical, Parametric, Multivariate, Copula (3 types), Monte Carlo
- Display VaR/CVaR at multiple confidence levels (90%, 95%, 99%)

### Page Structure Pattern

Each page follows this pattern:
```
pages/FeatureName/
├── FeatureName.tsx          # Page container (handles state, API calls)
└── components/              # Page-specific components
    ├── ComponentA.tsx
    └── ComponentB.tsx
```

Page component responsibilities:
- Fetch data with TanStack Query
- Manage local UI state with useState
- Pass data to child components
- Handle user actions (button clicks)

### Table Component Pattern

For complex tables (TanStack Table), use this modular architecture:

```
pages/FeatureName/
├── FeatureName.tsx
├── components/
│   ├── FeatureTable.tsx           # Main table (orchestration)
│   ├── FeatureTableHeader.tsx     # Header rendering
│   └── FeatureTableBody.tsx       # Body rendering
├── hooks/
│   ├── useFeatureColumns.tsx      # Column definitions
│   └── useFeatureTable.ts         # Table logic (state, filters, pagination)
└── constants/
    └── table.ts                   # Headers, messages, config
```

**Global Utils** (reusable across all pages):
- `src/utils/formatters.ts` - Number/currency formatting
- `src/utils/table.ts` - Table helpers (numeric columns, aria sort)

**Example** (MarketCapTable):
```typescript
// MarketCapTable.tsx (45 lines - orchestration only)
const { table, globalFilter, setGlobalFilter } = useMarketCapTable({ data, topN });
return (
  <div>
    <SearchBar />
    <table>
      <MarketCapTableHeader table={table} />
      <MarketCapTableBody table={table} />
    </table>
    <Pagination />
  </div>
);
```

**Benefits**:
- Each file has one responsibility
- Hooks are testable independently
- Formatters/helpers reusable across all tables
- Easy to maintain and extend

### Mapping Backend/Frontend

| Route Frontend | Endpoints Backend | Fonctionnalité |
|----------------|-------------------|----------------|
| `/universe` | `/api/v1/investment-universe/*` | Market cap, sélection actifs |
| `/strategy` | `/api/v1/strategy/*` | Optimisation, contraintes |
| `/positioning` | `/api/v1/positioning/*` | Positions, PnL |
| `/performance` | `/api/v1/performance/*` | Returns, drawdown, volatility |
| `/risk-metrics` | `/api/v1/metrics/*` | VaR, CVaR, métriques ex-ante/ex-post |
| `/market-risk` | `/api/v1/market-risk/*` | PCA, corrélations |

### Variables d'Environnement

```env
VITE_API_URL=http://localhost:8000    # Backend API
VITE_WS_URL=ws://localhost:8000       # WebSocket
```

## Patterns de Développement

### 1. Ajouter une Nouvelle Page

```
1. Créer src/pages/FeatureName/FeatureName.tsx
2. Créer src/services/featureService.ts
3. Définir types dans src/types/feature.ts
4. Ajouter route dans App.tsx
5. Utiliser TanStack Query pour data fetching
```

### 2. Appels API

```typescript
// src/services/strategyService.ts
export const strategyService = {
  optimize: async (params: OptimizationParams) => {
    const { data } = await apiClient.post('/api/v1/strategy/optimize', params);
    return data;
  }
};

// Dans un composant
const { data, isLoading, error } = useQuery({
  queryKey: ['strategy', 'optimize'],
  queryFn: () => strategyService.optimize(params)
});
```

### 3. TypeScript

Toujours typer les réponses API :

```typescript
// src/types/api.ts
export interface PositionData {
  asset: string;
  quantity: number;
  value_usdt: number;
  weight: number;
}
```

## Important Implementation Details

### Optimization Constraints (Strategy Page)

Must support same constraints as Jupyter notebook:
- **Asset-level**: min/max weight per asset
- **Portfolio-level**: diversification limits
- **Sum-to-one**: weights must equal 100%

Constraints built dynamically from user input via `ConstraintForm.tsx`.

### VaR Calculation Methods

Display results from 5 different methods (same as notebook):
1. **Historical VaR**: Empirical quantile
2. **Parametric VaR**: Normal distribution assumption
3. **Multivariate Distribution**: Correlated normal simulation
4. **Copula-based VaR**: Gaussian, t-Student, Gumbel copulas (tail dependencies)
5. **Monte Carlo**: GBM with Cholesky decomposition

Each method returns VaR/CVaR at 90%, 95%, 99% confidence levels.

### Date Handling

- All dates should be timezone-naive (match backend)
- Date ranges used for all historical data queries
- Rebalancing frequencies: Daily, Weekly, Monthly, Quarterly, Yearly

### Performance Optimization

- Use TanStack Query's `staleTime` to avoid unnecessary refetches
- Lazy load route components with `React.lazy()`
- Virtualize large tables (100+ rows) with `react-virtual`
- Debounce user inputs (sliders, search) with 300ms delay

## Bonnes Pratiques

- **TypeScript** : Typer systématiquement props, state, retours de fonctions
- **Performance** : Utiliser React.memo, useMemo, useCallback si nécessaire
- **Code Splitting** : React.lazy() pour lazy loading des pages
- **Error Handling** : Try/catch dans les services, afficher messages utilisateur
- **TanStack Query** : Configurer staleTime et cacheTime selon les besoins

## Développement par Phases

Le projet suit une roadmap en 10 phases (voir `README.md`).

**Phase actuelle** : Phase 1 - Infrastructure de base ⏳

Chaque phase frontend dépend de la disponibilité des APIs backend correspondantes.

## Backend

Le backend doit être running sur `http://localhost:8000`. Voir [`/backend/README.md`](../backend/README.md) pour setup.

**Important** : Vérifier que CORS est configuré pour accepter l'origine frontend.
