# Frontend Roadmap

Feuille de route pour le développement du frontend web de Risk-Management.

## ✅ Phase 1 : Infrastructure de Base

- [x] Initialisation du projet (Vite + React + TypeScript)
- [x] Création architecture du projet (Voir README)
- [x] Configuration Tailwind CSS
- [ ] Routing de base (React Router)
- [ ] Configuration ESLint + Prettier
- [ ] Configuration des variables d'environnement
- [ ] Client API HTTP (axios/fetch wrapper)
- [ ] Gestion globale des erreurs
- [ ] Loading states et spinners réutilisables

## ⏳ Phase 2 : Investment Universe

**Backend prérequis** : Phase 3 du backend

- [ ] Page Universe (`pages/Universe/Universe.tsx`)
- [ ] Composants:
  - [ ] `MarketCapTable.tsx` - Top N crypto table (symbol, price, market cap, 24h change)
  - [ ] `DateRangePicker.tsx` - Date range selection
  - [ ] `PriceChart.tsx` - Historical price chart
- [ ] Features:
  - [ ] Slider pour sélection nombre de cryptos
  - [ ] Bouton "Fetch Market Data"
  - [ ] Tri et filtrage du tableau
- [ ] Services:
  - [ ] `universeService.fetchMarketCap()`
  - [ ] `universeService.fetchPositions()`
- [ ] Cache local des données (TanStack Query)

## ⏳ Phase 3 : Strategy & Portfolio Optimization

**Backend prérequis** : Phase 4 du backend

- [ ] Page Strategy (`pages/Strategy/Strategy.tsx`)
- [ ] Composants:
  - [ ] `AllocationGrid.tsx` ⭐ - Editable grid (pandas DataFrame-like)
  - [ ] `ConstraintForm.tsx` - Asset & portfolio constraints
  - [ ] `AllocationChart.tsx` - Pie chart of weights
- [ ] Features:
  - [ ] Sélection objectif (Sharpe Ratio, Minimum Variance, Risk Parity)
  - [ ] Contraintes par asset (min/max weights)
  - [ ] Contraintes de diversification
  - [ ] Validation: weights sum to 100%
  - [ ] Ajout/suppression de stratégies personnalisées
- [ ] Services:
  - [ ] `strategyService.optimize()`
  - [ ] `strategyService.getConstraints()`
  - [ ] `strategyService.saveConstraints()`

## ⏳ Phase 4 : Positioning & PnL

**Backend prérequis** : Phase 5 du backend

- [ ] Page Positioning (`pages/Positioning/Positioning.tsx`)
- [ ] Composants:
  - [ ] `PositionsTable.tsx` - Current vs model positions, delta
  - [ ] `PnLTable.tsx` - Realized/unrealized PnL, book cost
  - [ ] `PnLChart.tsx` - Cumulative PnL chart
- [ ] Features:
  - [ ] Bouton "Get Positions"
  - [ ] Bouton "Get PnL"
  - [ ] Breakdown par asset
- [ ] Services:
  - [ ] `positionService.getPositions()`
  - [ ] `positionService.getPnL()`

## ⏳ Phase 5 : Performance & Returns

**Backend prérequis** : Phase 6 du backend

- [ ] Page Strategy Return (`/performance`)
- [ ] Graphique de performance cumulée
  - [ ] Comparaison stratégie vs benchmark
  - [ ] Sélection de plusieurs stratégies
- [ ] Graphique drawdown
- [ ] Graphique rolling volatility
- [ ] Tableau des métriques clés (Sharpe, Sortino, Max DD)
- [ ] Appel API `GET /api/v1/performance/returns`
- [ ] Appel API `GET /api/v1/performance/drawdown`
- [ ] Appel API `GET /api/v1/performance/volatility`

## ⏳ Phase 6 : Risk Metrics

**Backend prérequis** : Phase 7 du backend

### Page Ex-Post Metrics (`pages/Metrics/ExPost/`)
- [ ] `ExPost.tsx` - Page container
- [ ] `MetricsTable.tsx` - Historical performance metrics

### Page Calendar Metrics (`pages/Metrics/Calendar/`)
- [ ] `Calendar.tsx` - Page container
- [ ] `Heatmap.tsx` ⭐ - Monthly/yearly returns heatmap
- [ ] Frequency selector (monthly/yearly)
- [ ] Fund/benchmark selector

### Page Ex-Ante Metrics (`pages/Metrics/ExAnte/`)
- [ ] `ExAnte.tsx` - Page container
- [ ] `VarianceContribution.tsx` - Variance decomposition
- [ ] `TrackingError.tsx` - Tracking error forecasts

### Page Value at Risk (`pages/Metrics/VaR/`)
- [ ] `VaR.tsx` - Page container
- [ ] `VaRComparison.tsx` ⭐ - 5 methods comparison table
- [ ] `DistributionChart.tsx` - Simulated returns distribution
- [ ] Method selector (Historical, Parametric, Multivariate, Copula, Monte Carlo)
- [ ] VaR percentile input (95%, 99%)

### Services
- [ ] Appels API correspondants (`/api/v1/metrics/*`)

## ⏳ Phase 7 : Market Risk Analytics

**Backend prérequis** : Phase 8 du backend

- [ ] Page Market Risk (`/market-risk`)
- [ ] Analyse PCA
  - [ ] Tableau des composantes principales
  - [ ] Graphique variance expliquée
  - [ ] Eigen portfolios
- [ ] Page Correlation (`/correlation`)
  - [ ] Matrice de corrélation (heatmap)
  - [ ] Rolling correlations
  - [ ] Sélection de paires d'assets
- [ ] Appel API `GET /api/v1/market-risk/pca`
- [ ] Appel API `GET /api/v1/market-risk/correlation`

## ⏳ Phase 8 : UI/UX Polish

- [ ] Navigation globale (sidebar/header)
- [ ] Mode sombre/clair
- [ ] Responsive design (mobile/tablet)
- [ ] Animations et transitions
- [ ] Toast notifications
- [ ] Gestion des états vides
- [ ] Documentation utilisateur
- [ ] Tooltips et aide contextuelle

## ⏳ Phase 9 : Real-time Features

**Backend prérequis** : Phase 9 du backend

- [ ] WebSocket client
- [ ] Prix en temps réel sur le dashboard
- [ ] Indicateur de connexion WebSocket
- [ ] Reconnexion automatique
- [ ] Updates live des positions
- [ ] Notifications en temps réel

## ⏳ Phase 10 : Optimizations & Testing

- [ ] Tests unitaires (Vitest)
- [ ] Tests E2E (Playwright/Cypress)
- [ ] Optimisation des performances (lazy loading, memoization)
- [ ] SEO et meta tags
- [ ] Gestion du cache API
- [ ] Error boundaries React
- [ ] Logging client-side
- [ ] Build optimization

---

**Status actuel** : Phase 1 en cours ⏳

**Note** : Chaque phase dépend de la phase backend correspondante. Le développement peut être fait en parallèle mais le testing nécessite les endpoints backend disponibles.