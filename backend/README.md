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
pip install -r requirements-backend.txt
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
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Mode production

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## ✅ Tester

### Via curl

```bash
curl http://localhost:8000/health
```

### Via navigateur

- **Documentation** : http://localhost:8000/docs
- **Health check** : http://localhost:8000/health

## 📊 Endpoints Disponibles

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | API info |
| GET | `/health` | Health check |
| GET | `/docs` | Documentation Swagger |
| GET | `/redoc` | Documentation ReDoc |

> Les endpoints de l'Investment Universe API sont en cours de développement. Voir [ROADMAP.md](./ROADMAP.md)

## 📁 Structure

```
backend/
├── app/
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration
│   ├── dependencies.py      # DI
│   ├── api/                 # Endpoints REST
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   ├── core/                # Utilities
│   └── utils/               # Helpers
├── logs/                    # Logs
├── tests/                   # Tests
└── requirements-backend.txt
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
