# Backend Roadmap

Feuille de route pour le développement du backend FastAPI.

## ✅ Phase 1 : Infrastructure de Base

- [x] Structure des dossiers
- [x] FastAPI app avec CORS
- [x] Logging configuration
- [x] Exception handlers
- [x] Health check endpoint
- [x] Documentation auto-générée
- [x] Dependency injection

## ✅ Phase 2 : Services Fondamentaux

- [x] Rate limiter pour Binance API (`core/rate_limiter.py`)
- [x] Cache service avec TTL (`services/cache_service.py`)
- [x] Binance service wrapper (`services/binance_service.py`)

## ⏳ Phase 3 : Investment Universe API

- [ ] Pydantic models (`models/common.py`, `models/investment_universe.py`)
- [ ] GET `/api/v1/investment-universe/market-cap`
- [ ] GET `/api/v1/investment-universe/prices`
- [ ] GET `/api/v1/investment-universe/returns`
- [ ] GET `/api/v1/investment-universe/asset-metrics`
- [ ] Router aggregator (`api/router.py`)
- [ ] Tests unitaires

## ⏳ Phase 4 : WebSocket

- [ ] WebSocket manager (`services/websocket_service.py`)
- [ ] WebSocket models (`models/websocket.py`)
- [ ] WS `/ws/prices` endpoint
- [ ] Background task pour polling prix
- [ ] Heartbeat mechanism

## ⏳ Phase 5 : Autres Features (Structure seulement)

- [ ] Strategy router (`api/v1/strategy.py`)
- [ ] Positioning router (`api/v1/positioning.py`)
- [ ] Performance router (`api/v1/performance.py`)
- [ ] Ex Post Metrics router (`api/v1/ex_post_metrics.py`)
- [ ] Calendar Metrics router (`api/v1/calendar_metrics.py`)
- [ ] Ex Ante Metrics router (`api/v1/ex_ante_metrics.py`)
- [ ] VaR Metrics router (`api/v1/var_metrics.py`)
- [ ] Market Risk router (`api/v1/market_risk.py`)
- [ ] Correlation router (`api/v1/correlation.py`)

---

**Status actuel** : Phase 1 ✅ | Phase 2 ✅ | Phase 3 en cours ⏳
