# Setup

The project has two sets of apps with separate setups:

- **Notebooks and Streamlit** (`Crypto App.ipynb`, `Multi Asset App.ipynb`, `HMM Regime App.ipynb`, `Streamlit_App.py`): Python only, credentials in `keys.py`.
- **Web app** (`backend/` + `frontend/`): FastAPI + React, credentials in `.env`, launched with `start-binance.bat` or `start-yahoo.bat`.

## 🔑 Credentials

**Binance API** (crypto apps):
1. Go to https://www.binance.com/en/my/settings/api-management
2. Create a new API key
3. Copy the API Key and the Secret Key
4. ⚠️ Enable **reading only** (no trading, no withdrawals)

**GitHub token** (optional, only to push the Positions / Quantities Excel files):
1. Go to https://github.com/settings/tokens
2. Generate a token with the `repo` scope
3. Copy the token

## 📓 Notebooks and Streamlit

### 1. Install the dependencies

```bash
pip install -r requirements.txt
```

Tested with Python 3.13 and the exact versions in `requirements.txt`.

### 2. Create `keys.py` at the project root

```python
binance_api_key = "your_binance_key"
binance_api_secret = "your_binance_secret"
token = "your_github_token"
repo_owner = "your_github_user"
repo_name = "Risk-Management"
branch = "main"
```

### 3. Run

```bash
jupyter notebook "Crypto App.ipynb"     # or "Multi Asset App.ipynb", "HMM Regime App.ipynb"
streamlit run Streamlit_App.py
```

In Jupyter, run all cells: the app appears under the last cell.

## 🌐 Web App

### 1. Prerequisites

- **Python 3.11+** from python.org or Anaconda / Miniconda. On the first run, the launcher creates `backend/.venv` from the first suitable Python it finds:
  1. the `BASE_PYTHON` environment variable, if set
  2. the `py` launcher
  3. `python` on the PATH
  4. the usual Anaconda / Miniconda folders

  If yours is somewhere else, run `set BASE_PYTHON=C:\path\to\python.exe` before the launcher.
- **Node.js LTS** from https://nodejs.org (provides `npm`).

### 2. Create `.env` at the project root

One file feeds both the backend and the frontend:

```bash
cp .env.example .env
```

Then fill it in:

```bash
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

GITHUB_TOKEN=your_github_token          # optional: 'Upload Files' / 'Update Files'
GITHUB_REPO_OWNER=your_github_username
GITHUB_REPO_NAME=Risk-Management
GITHUB_BRANCH=main
```

The Yahoo version needs no Binance key; it reads its portfolio files from the repository's `ETF/` folder on GitHub.

### 3. Launch

Double-click one of the launchers at the project root:

| Launcher | Data | Backend | App |
|---|---|---|---|
| `start-binance.bat` | Binance prices and account | http://localhost:8000 | http://localhost:5173 |
| `start-yahoo.bat` | Yahoo Finance prices, `ETF/` Excel portfolio | http://localhost:8001 | http://localhost:5174 |

The first launch installs the Python packages (`backend/requirements.txt`) and the npm packages, then opens two windows (backend and frontend) and the app in your browser. Close those two windows to stop the app. Both versions can run at the same time.

### Manual launch (any OS)

```bash
# Backend
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt          # Windows: .venv\Scripts\pip
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
# Yahoo version: set MARKET=multi_asset and use --port 8001

# Frontend (another terminal)
cd frontend
npm install
npm run dev                                         # http://localhost:5173
# Yahoo version: VITE_API_URL=http://localhost:8001 npm run dev -- --port 5174
```

## ⚠️ Security

- **Never commit** `.env` or `keys.py`. `.env` is listed in the root `.gitignore`; add `keys.py` as well.
- Keep your API keys read-only.
- If a key has ever been pushed, regenerate it on Binance / GitHub.

## 🐛 Common Problems

### `ModuleNotFoundError: No module named 'X'`
- Notebooks: `pip install -r requirements.txt`
- Web app: `backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt`

The launcher only installs packages when an import fails, so after a version change in `backend/requirements.txt` run the command above.

### `binance.error.ClientError: APIError(code=-2015)`
Check that the API key has reading permissions and that your IP is allowed.

### "Binance service not configured" (web app, HTTP 503)
`BINANCE_API_KEY` / `BINANCE_API_SECRET` are missing from the `.env` file of the project folder.

### "The backend is not reachable" (web app)
The backend window is closed or still starting: wait a few seconds and reload, or launch the `.bat` again.

### `Activate.ps1 cannot be loaded because running scripts is disabled`
Use the `.bat` launchers (they don't need activation), or run `.venv\Scripts\python.exe` directly.

### Port already in use
Another copy of the app is running: close its backend / frontend windows first.
