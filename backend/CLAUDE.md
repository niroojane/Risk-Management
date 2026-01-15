# CLAUDE.md - Backend Agent

FastAPI backend for cryptocurrency portfolio management system.

## Architecture

**Clean Architecture en 4 couches:**
- `app/core/`: Config, rate limiter, cache, middleware, exceptions
- `app/services/`: BinanceService (async wrapper des modules legacy)
- `app/api/v1/`: Routes FastAPI par domaine
- `app/models/`: Entities (domaine) + Schemas (API contracts)

**Pattern clé:**
- Entities = objets métier purs
- Schemas = Request/Response wrappés dans `APIResponse`
- Services utilisent `run_in_executor()` pour appeler les modules legacy sync

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

1. Entity dans `app/models/entities/<domain>/<feature>_entities.py`
2. Schema (Request + Response) dans `app/models/schemas/<domain>/<feature>_schemas.py`
3. Route dans `app/api/v1/<domain>.py` avec `BinanceServiceDep` (dependency injection)
4. Enregistrer le router dans `app/main.py`

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
