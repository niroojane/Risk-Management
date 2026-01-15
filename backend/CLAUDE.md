# CLAUDE.md - Backend Agent

FastAPI backend for cryptocurrency portfolio management system.

## Architecture

**Clean Architecture en 6 couches:**
- `app/core/`: Config, rate limiter, cache, middleware, exceptions
- `app/services/`: BinanceService (async wrapper des modules legacy)
- `app/api/v1/`: Routes FastAPI (gestion HTTP uniquement)
- `app/controllers/`: Logique métier et orchestration
- `app/mappers/`: Transformation de données (external format ↔ domain entities)
- `app/models/`: Entities (objets métier purs organisés par domaine)
- `app/schemas/`: Schemas Pydantic (Request/Response API contracts)

**Pattern clé - Flux de données:**
```
Route → Controller → Service → API externe
  ↓         ↓
  ↓      Mapper → Entity
  ↓         ↓
Schema ← Response
```

**Séparation des responsabilités:**
- **Route**: Validation HTTP, status codes, HTTPException
- **Controller**: Orchestration, logique métier, construction réponse
- **Mapper**: Transformation dict ↔ Entity (stateless)
- **Service**: Appels API externes, rate limiting, cache
- **Entity**: Objets métier purs
- **Schema**: Contrats API (Request/Response)

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

# Lancer le serveur (prod)
uvicorn app.main:app --port 8000 --workers 4

# Tests (12 tests: cache, rate limiter, binance service)
pytest tests/ -v
pytest tests/test_cache_service.py::test_cache_basic_operations -v

# Logs
tail -f logs/app.log

# API docs
curl http://localhost:8000/health
# Swagger: http://localhost:8000/docs
```

## Ajouter un endpoint

1. Entity dans `app/models/<domain>/<feature>_entities.py`
2. Schema (Request + Response) dans `app/schemas/<domain>/<feature>_schemas.py`
3. Route dans `app/api/v1/<domain>.py` avec `BinanceServiceDep` (dependency injection)
4. Enregistrer le router dans `app/main.py`

**Structure des imports:**
```python
# Dans app/api/v1/<domain>.py
from ...models.<domain> import MyEntity
from ...schemas.<domain> import MyRequest, MyResponse
```

## Patterns importants

**Dependency Injection:**
- `BinanceServiceDep`: Service Binance avec rate limiting + cache (utilise variables d'environnement)
- `CacheServiceDep`: Service de cache
- Les dépendances sont des singletons via `@lru_cache()` dans `app/core/dependencies.py`

**Wrapper legacy sync → async:**
```python
async def my_method(self):
    await self._with_rate_limit(weight=10)
    result = await self._run_in_executor(self._legacy_api.method, arg=value)
    return self._dataframe_to_dict(result)
```

**Cache pattern:**
```python
cached = await self._cache.get(cache_key)
if cached: return cached
data = await fetch_data()
await self._cache.set(cache_key, data, ttl=300)
```

**Rate limiter:**
- Binance = 1200 req/min weight-based
- `await self._with_rate_limit(weight=40)` avant chaque call

## Phase actuelle

Phase 3: Investment Universe API (market-cap, prices, returns)
Voir [ROADMAP.md](./ROADMAP.md)
