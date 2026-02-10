# Backend Roadmap

Feuille de route pour le développement du backend FastAPI.

## ✅ Phase 1 : Infrastructure de Base

- [x] Structure des dossiers
- [x] FastAPI app avec CORS
- [x] Variables d'environnement
- [x] Logging configuration
- [x] Exception handlers
- [x] Health check endpoint
- [x] Documentation auto-générée
- [x] Dependency injection

## ✅ Phase 2 : Services Fondamentaux

- [x] Rate limiter pour Binance API (`core/rate_limiter.py`)
- [x] Cache service avec TTL (`services/cache_service.py`)
- [x] Binance service wrapper (`services/binance_service.py`)

## ✅ Phase 3 : Investment Universe API

**Refactorisation architecture :**
- [x] Clean architecture (models aplatis, services séparés)
- [x] Models : `market_cap`, `market_data`, `positions`, `quantities`
- [x] Services : `MarketCapService`, `MarketDataService`, `PositionService`, `QuantityService`
- [x] Controllers : `MarketCapController`, `MarketDataController`, `PositionsController`

**Endpoints :**
- [x] POST `/api/v1/investment-universe/market-cap` - Top N cryptos
- [x] POST `/api/v1/investment-universe/market-data` - Prices + returns (parallélisé 3 mois)
- [x] POST `/api/v1/investment-universe/positions` - Positions historiques
- [ ] Ajouter asset risk metrics à market-data (volatility, sharpe, drawdown)

## ⏳ Phase 4 : Strategy & Portfolio Optimization

- [x] POST `/api/v1/investment-universe/positions` (quantities × prices)
- [ ] Pydantic models (`models/strategy/`, `schemas/strategy/`)
- [ ] POST `/api/v1/strategy/optimize` (`api/v1/strategy/optimization.py`)
- [ ] GET/POST `/api/v1/strategy/constraints` (`api/v1/strategy/constraints.py`)
- [ ] Controllers (`controllers/strategy/`)
- [ ] Tests unitaires

## ⏳ Phase 5 : Positioning & PnL

- [ ] Pydantic models (`models/positioning/`, `schemas/positioning/`)
- [ ] GET `/api/v1/positioning/positions` (`api/v1/positioning/positions.py`)
- [ ] GET `/api/v1/positioning/pnl` (`api/v1/positioning/pnl.py`)
- [ ] Controllers (`controllers/positioning/`)
- [ ] Tests unitaires

## ⏳ Phase 6 : Performance Analytics

- [ ] Pydantic models (`models/performance/`, `schemas/performance/`)
- [ ] GET `/api/v1/performance/returns` (`api/v1/performance/returns.py`)
- [ ] GET `/api/v1/performance/drawdown` (`api/v1/performance/drawdown.py`)
- [ ] GET `/api/v1/performance/volatility` (`api/v1/performance/volatility.py`)
- [ ] Controllers (`controllers/performance/`)
- [ ] Tests unitaires

## ⏳ Phase 7 : Risk Metrics

- [ ] Pydantic models (`models/metrics/`, `schemas/metrics/`)
- [ ] GET `/api/v1/metrics/ex-post` (`api/v1/metrics/ex_post.py`)
- [ ] GET `/api/v1/metrics/ex-ante` (`api/v1/metrics/ex_ante.py`)
- [ ] GET `/api/v1/metrics/calendar` (`api/v1/metrics/calendar.py`)
- [ ] GET `/api/v1/metrics/var` (`api/v1/metrics/var.py`)
- [ ] Controllers (`controllers/metrics/`)
- [ ] Tests unitaires

## ⏳ Phase 8 : Market Risk Analytics

- [ ] Pydantic models (`models/market_risk/`, `schemas/market_risk/`)
- [ ] GET `/api/v1/market-risk/pca` (`api/v1/market-risk/pca.py`)
- [ ] GET `/api/v1/market-risk/correlation` (`api/v1/market-risk/correlation.py`)
- [ ] Controllers (`controllers/market_risk/`)
- [ ] Tests unitaires

## ⏳ Phase 9 : WebSocket Real-time Data

- [ ] WebSocket manager (`services/websocket_service.py`)
- [ ] Pydantic models (`models/websocket/`, `schemas/websocket/`)
- [ ] WS `/ws/prices` (`api/v1/websocket/prices.py`)
- [ ] Background task pour polling prix
- [ ] Heartbeat mechanism
- [ ] Tests unitaires

---

**Status actuel** : Phase 1 ✅ | Phase 2 ✅ | Phase 3 ✅ (asset risk à finaliser) | Phase 4 à démarrer
