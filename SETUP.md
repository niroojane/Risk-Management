# Setup Instructions

## 🔧 Configuration Initiale

### 1. Créer le fichier .env

Copiez `.env.example` vers `.env` à la racine du projet :

```bash
cp .env.example .env
```

Ensuite, éditez `.env` et remplissez vos credentials :

```bash
# Binance API Credentials
BINANCE_API_KEY=votre_clé_api_binance
BINANCE_API_SECRET=votre_secret_api_binance

# GitHub API Configuration (optionnel - uniquement pour push des fichiers Excel)
GITHUB_TOKEN=votre_token_github
GITHUB_REPO_OWNER=votre_username_github
GITHUB_REPO_NAME=Risk-Management
GITHUB_BRANCH=main
```

#### Comment obtenir les credentials :

**Binance API** :
1. Allez sur https://www.binance.com/en/my/settings/api-management
2. Créez une nouvelle API key
3. Copiez l'API Key et le Secret Key
4. ⚠️ Activez uniquement "Enable Reading" (pas de trading/withdrawal)

**GitHub Token** (optionnel) :
1. Allez sur https://github.com/settings/tokens
2. Générez un nouveau token avec scope "repo"
3. Copiez le token

### 2. Activer l'environnement virtuel Python

```bash
source venv/bin/activate
```

Vous devriez voir `(venv)` apparaître dans votre terminal.

### 3. Vérifier que les dépendances sont installées

```bash
pip list | grep -E "jupyter|pandas|plotly|binance"
```

Si tout est ok, vous devriez voir les packages listés.

## 🚀 Lancer le Projet

### Option 1 : Jupyter Notebook (Interface Interactive)

```bash
jupyter notebook "Crypto App.ipynb"
```

Cela ouvrira votre navigateur avec le notebook. Ensuite :
1. Cliquez sur "Run All" ou exécutez les cellules une par une
2. L'interface à onglets devrait apparaître à la fin du notebook

### Option 2 : JupyterLab (Interface moderne)

```bash
jupyter lab
```

Puis ouvrez `Crypto App.ipynb` depuis l'interface JupyterLab.

### Option 3 : Exécuter le script Python directement

Si vous voulez juste tester la connexion à l'API :

```bash
python -c "from config import validate_config; validate_config()"
```

Cela va vérifier si vos variables d'environnement sont bien configurées.

## 🧪 Test Rapide

Pour tester que tout fonctionne :

```python
from config import BINANCE_API_KEY, BINANCE_API_SECRET
from Binance_API import BinanceAPI

# Créer une instance de l'API
api = BinanceAPI(BINANCE_API_KEY, BINANCE_API_SECRET)

# Tester la récupération du market cap
market_cap = api.get_market_cap()
print(f"Top 5 cryptos par market cap:")
print(market_cap.head())
```

## ⚠️ Sécurité

- **Ne commitez JAMAIS** votre fichier `.env` dans git
- Le fichier `.gitignore` est déjà configuré pour ignorer `.env`
- Gardez vos API keys secrètes

## 🐛 Problèmes Courants

### "ModuleNotFoundError: No module named 'X'"
```bash
pip install -r requirements.txt
```

### "binance.error.ClientError: APIError(code=-2015)"
Vérifiez que votre API key a les permissions de lecture activées.

### Jupyter ne se lance pas
```bash
pip install --upgrade jupyter
```

### Import config ne fonctionne pas
Assurez-vous d'être dans le bon répertoire :
```bash
pwd  # Devrait afficher: /Users/alix/Risk-Management
```
