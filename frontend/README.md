# Risk-Management Frontend

Interface web pour le système de gestion de portefeuille et d'analyse de risque de cryptomonnaies.

## Description

Application React + TypeScript qui fournit une interface utilisateur pour visualiser et gérer des portefeuilles de cryptomonnaies, avec analyse de risque, optimisation de portefeuille, et métriques de performance en temps réel.

## Stack Technique

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router
- **Charts**: Chart.js / Recharts
- **HTTP Client**: Axios
- **State Management**: React Context / Redux (TBD)

## Installation

```bash
# Installer les dépendances
npm install

# Lancer le serveur de développement
npm run dev

# Build pour la production
npm run build

# Preview du build
npm run preview
```

## Configuration

Créer un fichier `.env` à la racine du projet:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## Architecture Frontend

### Structure des Dossiers

```
frontend/
├── src/
│   ├── components/
│   │   ├── common/              # Button, Input, Select, DatePicker, Table
│   │   ├── charts/              # LineChart, BarChart, PieChart, Heatmap
│   │   ├── layout/              # Header, Sidebar, Layout
│   │   └── forms/               # Form components
│   │
│   ├── pages/                   # Feature-based structure (1 page = 1 notebook tab)
│   │   ├── Universe/
│   │   │   ├── Universe.tsx
│   │   │   └── components/
│   │   │       ├── MarketCapTable.tsx
│   │   │       ├── PriceChart.tsx
│   │   │       └── DateRangePicker.tsx
│   │   │
│   │   ├── Strategy/
│   │   │   ├── Strategy.tsx
│   │   │   └── components/
│   │   │       ├── AllocationGrid.tsx    # ⭐ Key component (editable grid)
│   │   │       ├── ConstraintForm.tsx
│   │   │       └── AllocationChart.tsx
│   │   │
│   │   ├── Positioning/
│   │   │   ├── Positioning.tsx
│   │   │   └── components/
│   │   │       ├── PositionsTable.tsx
│   │   │       └── PnLTable.tsx
│   │   │
│   │   ├── Performance/
│   │   │   ├── Performance.tsx
│   │   │   └── components/
│   │   │       ├── PerformanceChart.tsx
│   │   │       ├── DrawdownChart.tsx
│   │   │       └── VolatilityChart.tsx
│   │   │
│   │   └── Metrics/
│   │       ├── ExPost/
│   │       ├── Calendar/
│   │       │   └── components/
│   │       │       └── Heatmap.tsx       # ⭐ Key component
│   │       ├── ExAnte/
│   │       └── VaR/
│   │           └── components/
│   │               └── VaRComparison.tsx # ⭐ 5 methods comparison
│   │
│   ├── services/            # API clients
│   │   ├── api.ts
│   │   ├── universeService.ts
│   │   ├── strategyService.ts
│   │   ├── positionService.ts
│   │   └── websocket.ts
│   │
│   ├── types/               # TypeScript types
│   │   ├── portfolio.ts
│   │   ├── risk.ts
│   │   └── api.ts
│   │
│   ├── hooks/               # Custom React hooks
│   │   ├── useApi.ts
│   │   ├── useWebSocket.ts
│   │   └── usePortfolio.ts
│   │
│   ├── stores/              # Zustand stores
│   │   └── portfolioStore.ts
│   │
│   ├── context/             # Context providers
│   │   └── ThemeContext.tsx
│   │
│   ├── utils/               # Utilities
│   │   ├── formatters.ts
│   │   ├── calculations.ts
│   │   └── constants.ts
│   │
│   └── assets/              # Static files
```

### Flux de Données

1. **Initialisation**: L'utilisateur accède à la page
2. **Requête API**: Les services appellent le backend FastAPI via Axios
3. **State Management**: Les données sont stockées dans React Context/Redux
4. **Rendu**: Les composants affichent les données avec charts et tableaux
5. **Interactions**: Les actions utilisateur déclenchent de nouvelles requêtes
6. **WebSocket**: Mise à jour en temps réel des prix et positions

### Pages Principales

| Route | Page | Description |
|-------|------|-------------|
| `/universe` | Investment Universe | Market cap table, price charts, date selection |
| `/strategy` | Strategy | Portfolio optimization, constraints, allocation grid |
| `/positioning` | Positioning | Current positions vs model, PnL breakdown |
| `/performance` | Performance | Returns, drawdown, rolling volatility |
| `/metrics/ex-post` | Ex Post Metrics | Historical performance metrics |
| `/metrics/calendar` | Calendar Metrics | Monthly/yearly returns heatmap |
| `/metrics/ex-ante` | Ex Ante Metrics | Variance contribution, tracking error |
| `/metrics/var` | Value at Risk | VaR/CVaR calculations (5 methods) |
| `/market-risk` | Market Risk | PCA analysis, eigen portfolios |
| `/correlation` | Correlation | Correlation matrix, rolling correlations |

### Composants Clés

**AllocationGrid** (Strategy page)
- Editable grid similar to pandas DataFrame
- Multiple portfolio strategies as rows
- Asset allocations as columns
- Validation: weights sum to 100%

**Heatmap** (Calendar Metrics)
- Monthly/yearly returns visualization
- Color-coded (green/red)

**VaRComparison** (VaR Metrics)
- 5 calculation methods: Historical, Parametric, Multivariate, Copula, Monte Carlo
- Side-by-side comparison table

### Patterns de Développement

#### 1. Services API
```typescript
// services/strategyService.ts
export const optimizePortfolio = async (params: OptimizationParams) => {
  const response = await api.post('/api/v1/strategy/optimize', params);
  return response.data;
};
```

#### 2. Custom Hooks
```typescript
// hooks/usePortfolio.ts
export const usePortfolio = () => {
  const { data, loading, error } = useApi('/api/v1/positions');
  return { portfolio: data, loading, error };
};
```

#### 3. Context pour État Global
```typescript
// context/PortfolioContext.tsx
export const PortfolioProvider = ({ children }) => {
  const [weights, setWeights] = useState({});
  return <PortfolioContext.Provider value={{ weights, setWeights }}>
    {children}
  </PortfolioContext.Provider>;
};
```

## Intégration Backend

Le frontend communique avec l'API backend FastAPI située dans [`/backend`](../backend/README.md).

### Endpoints Principaux

- **Investment Universe**: `/api/v1/investment-universe/*`
- **Strategy**: `/api/v1/strategy/*`
- **Positions**: `/api/v1/positions/*`
- **Performance**: `/api/v1/performance/*`
- **Risk Metrics**: `/api/v1/metrics/*`
- **Market Risk**: `/api/v1/market-risk/*`

## Développement

### Commandes Utiles

```bash
# Linter
npm run lint

# Type checking
npm run type-check

# Tests
npm run test

# Formater le code
npm run format
```

### Bonnes Pratiques

- **TypeScript**: Toujours typer les props, state, et retours de fonctions
- **Composants**: Préférer les functional components avec hooks
- **Styling**: Utiliser Tailwind CSS, éviter le CSS inline
- **Performance**: Utiliser React.memo, useMemo, useCallback si nécessaire
- **API Calls**: Centraliser les appels dans les services
- **Error Handling**: Toujours gérer les erreurs avec try/catch et afficher des messages utilisateur

## Roadmap

Voir le fichier [ROADMAP.md](./ROADMAP.md) pour le détail des phases de développement.

**Status actuel**: Phase 1 - Infrastructure de base ⏳

## License

Propriétaire
