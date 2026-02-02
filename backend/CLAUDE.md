# CLAUDE.md - Backend Agent

FastAPI backend for cryptocurrency portfolio management system.

## Architecture

**Clean Architecture en 6 couches:**
- `app/core/`: Config, rate limiter, cache, middleware, exceptions
- `app/services/binance/`: Services Binance modulaires avec appels API directs
- `app/api/v1/`: Routes FastAPI (gestion HTTP uniquement)
- `app/controllers/`: Logique métier et orchestration
- `app/mappers/`: Transformation de données (external format ↔ domain entities)
- `app/models/`: Entities (objets métier purs organisés par domaine)
- `app/schemas/`: Schemas Pydantic (Request/Response API contracts)

**Services Binance (architecture refactorisée):**
```
services/binance/
├── binance_client.py        # Client async de base (rate limiting, cache)
├── market_data_service.py   # Market cap, données publiques
├── price_service.py         # Klines/prix historiques
├── quantity_service.py      # Snapshots de compte
├── position_service.py      # Orchestration des calculs de positions
└── transformers/
    ├── kline_transformer.py    # Transformations pandas klines
    └── balance_transformer.py  # Transformations balances
```

**Flux de données:**
```
Route → Controller → Service → Binance API
  ↓         ↓          ↓
  ↓         ↓      Transformer
  ↓      Mapper → Entity
  ↓         ↓
Schema ← Response
```

**Note sur BINANCE_API.py (legacy):**
Le fichier `BINANCE_API.py` dans la racine du projet est un module legacy servant de référence pour la logique. Le backend fait les appels API Binance directement avec `binance-connector` dans une architecture modulaire refactorisée.

## Variables d'environnement

Fichier `.env` à la racine du projet :
```
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
GITHUB_TOKEN=...
GITHUB_REPO_OWNER=...
GITHUB_REPO_NAME=Risk-Management
```

## Commandes

```bash
# Lancer le serveur (dev)
uvicorn app.main:app --reload --port 8000

# Tests
pytest tests/ -v

# API docs
# Swagger: http://localhost:8000/docs
```

## Dependency Injection

Services disponibles dans `app/core/dependencies.py`:
- `BinanceServiceDep`: Client Binance de base
- `MarketDataServiceDep`: Market cap, données publiques
- `PriceServiceDep`: Prix/klines historiques
- `QuantityServiceDep`: Quantités/balances de compte
- `PositionServiceDep`: Orchestration des calculs de positions
- `CacheServiceDep`: Service de cache

Singletons créés via `@lru_cache()`.

## Ajouter un endpoint

1. Schema (Request + Response) dans `app/schemas/<domain>/`
2. Controller dans `app/controllers/<domain>/` avec injection des services
3. Route dans `app/api/v1/<domain>/` avec dependency injection
4. Enregistrer le router dans `app/main.py`

## Notes importantes

- **Rate limiting**: 1200 req/min weight-based (géré automatiquement par BinanceClient)
- **Cache**: Géré automatiquement par `BinanceClient.fetch_with_cache()`
- **Transformers**: Utilisés pour convertir les données Binance (pandas) vers les formats API
- **Async**: Appels sync Binance wrappés avec `_run_in_executor()`

## Phase actuelle

Phase 3: Investment Universe API (market-cap, prices, returns)
Voir [ROADMAP.md](./ROADMAP.md)
