# Risk Management API - Backend

Backend FastAPI pour le système de gestion de portefeuille crypto. Ce backend expose des APIs REST et WebSocket pour l'analyse de portefeuille, l'optimisation, et le calcul de risques.

## 📋 Prérequis

- Python 3.11+
- pip (gestionnaire de paquets Python)
- Variables d'environnement Binance API (optionnel)

## 🚀 Installation

### 1. Installer les dépendances

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configuration

Créez un fichier `.env` à la racine du projet avec vos credentials :

```bash
# Binance API
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# GitHub API
GITHUB_TOKEN=your_token
GITHUB_REPO_OWNER=your_username
GITHUB_REPO_NAME=Risk-Management
GITHUB_BRANCH=main
```

## ▶️ Lancer le Backend

### Mode développement

```bash
cd backend
python3 -m uvicorn app.main:app --reload --port 8000 
```

### Mode production

```bash
python3 -m uvicorn app.main:app --port 8000 --workers 4
```

## ✅ Tests

### Tests unitaires (pytest)

```bash
# Tous les tests
pytest tests/ -v

# Un fichier spécifique
pytest tests/test_cache_service.py -v

# Un test spécifique
pytest tests/test_cache_service.py::test_cache_basic_operations -v
```

**Architecture des tests** :
- `tests/conftest.py` - Fixtures réutilisables
- `tests/test_cache_service.py` - Tests du cache (4 tests)
- `tests/test_rate_limiter.py` - Tests du rate limiter (5 tests)
- `tests/test_binance_service.py` - Tests du service Binance (3 tests)
- `tests/test_position_service.py` - Tests du service Position (5 tests)

**Total : 17 tests** couvrant les services fondamentaux.

### Tester l'API

```bash
# Health check
curl http://localhost:8000/health

# Market cap top 10
curl -X POST http://localhost:8000/api/v1/investment-universe/market-cap \
  -H "Content-Type: application/json" \
  -d '{"quote":"USDT","top_n":10}'

# Positions historiques
curl -X POST http://localhost:8000/api/v1/investment-universe/positions \
  -H "Content-Type: application/json" \
  -d '{"symbols":["BTCUSDT","ETHUSDT"],"start_date":"2026-01-15T00:00:00Z","end_date":"2026-01-17T00:00:00Z"}'

# Documentation interactive
open http://localhost:8000/docs
```

## 📊 Endpoints Disponibles

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | API info |
| GET | `/health` | Health check |
| GET | `/docs` | Documentation Swagger |
| GET | `/redoc` | Documentation ReDoc |
| POST | `/api/v1/investment-universe/market-cap` | Top N cryptos par market cap |
| POST | `/api/v1/investment-universe/positions` | Positions historiques (quantities × prices) |

> Autres endpoints de l'Investment Universe API en développement. Voir [ROADMAP.md](./ROADMAP.md)

## 📁 Structure

```
backend/
├── app/
│   ├── main.py                 # Entry point
│   ├── core/                   # Config, exceptions, dependencies
│   ├── api/v1/                 # REST routes
│   ├── controllers/            # Business logic
│   ├── services/
│   │   ├── binance/           # BinanceClient, UniverseDataService, PositionService
│   │   └── infrastructure/    # Cache
│   ├── models/
│   │   └── investment_universe/
│   │       └── positions/     # Prices, Positions, Quantities entities
│   ├── schemas/
│   │   ├── investment_universe/
│   │   │   └── positions/     # Prices, Positions, Quantities schemas
│   │   └── external/binance/  # DTOs (KlineDTO, AccountSnapshotDTO)
│   └── mappers/                # Data transformers
├── logs/                       # Logs
├── tests/                      # Tests (17 tests)
└── requirements.txt
```

## 📝 Logs

Les logs sont disponibles dans :
- **Console** : stdout
- **Fichier** : `backend/logs/app.log`

```bash
# Voir les logs en temps réel
tail -f backend/logs/app.log
```

## 🛑 Arrêter

- **Foreground** : `Ctrl+C`
- **Background** : `kill -9 $(lsof -t -i:8000)`

## 📚 Documentation

- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc
- **OpenAPI JSON** : http://localhost:8000/openapi.json

## 🔗 Intégration Frontend

Configuration dans `frontend/.env` :
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## 📄 Plus d'informations

- [ROADMAP.md](./ROADMAP.md) - Feuille de route du projet
- [../CLAUDE.md](../CLAUDE.md) - Documentation du projet global

---

**Version** : 1.0.0 | **Status** : En développement
