"""Excel files of the real portfolio stored in the GitHub repository (BinancePTF folder)"""
import base64
import logging
from io import BytesIO
from typing import Optional

import pandas as pd
import requests

from ...core.exceptions import ExternalAPIError

logger = logging.getLogger(__name__)

POSITIONS_FILE = 'Positions'
QUANTITIES_FILE = 'Quantities'
TRADES_FILE = 'Trade History Reconstructed'


class GitHubStorage:
    """Reads files from the repository's raw URLs and writes them through the contents API"""

    def __init__(self, owner: str, repo: str, branch: str = 'main', folder: str = 'BinancePTF',
                 token: Optional[str] = None, timeout: int = 30):
        self._owner = owner
        self._repo = repo
        self._branch = branch
        self._folder = folder
        self._token = token
        self._timeout = timeout

    @property
    def can_write(self) -> bool:
        return bool(self._token)

    def _path(self, name: str) -> str:
        return f"{self._folder}/{name}.xlsx" if self._folder else f"{name}.xlsx"

    def read_excel(self, name: str, index_col=None) -> pd.DataFrame:
        """Read `<folder>/<name>.xlsx` from the branch"""
        url = f"https://github.com/{self._owner}/{self._repo}/raw/refs/heads/{self._branch}/{self._path(name)}"
        try:
            response = requests.get(url, timeout=self._timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ExternalAPIError(f"Could not download {name}.xlsx from GitHub", detail=str(exc))
        return pd.read_excel(BytesIO(response.content), index_col=index_col)

    def write_excel(self, df: pd.DataFrame, name: str) -> str:
        """Create or update `<folder>/<name>.xlsx`; returns 'created' or 'updated'"""
        if not self._token:
            raise ExternalAPIError("GitHub token not configured", detail="Set GITHUB_TOKEN in .env")

        buffer = BytesIO()
        df.to_excel(buffer, index=True, engine='openpyxl')
        url = f"https://api.github.com/repos/{self._owner}/{self._repo}/contents/{self._path(name)}"
        headers = {'Authorization': f'token {self._token}', 'Accept': 'application/vnd.github.v3+json'}

        existing = requests.get(url, headers=headers, params={'ref': self._branch}, timeout=self._timeout)
        if existing.status_code not in (200, 404):
            raise ExternalAPIError(f"GitHub error while checking {name}.xlsx", detail=existing.text[:300])

        payload = {
            'message': f'Add/Update {name}.xlsx via API',
            'content': base64.b64encode(buffer.getvalue()).decode(),
            'branch': self._branch,
        }
        if existing.status_code == 200:
            payload['sha'] = existing.json()['sha']

        response = requests.put(url, headers=headers, json=payload, timeout=self._timeout)
        if response.status_code not in (200, 201):
            raise ExternalAPIError(f"GitHub error while writing {name}.xlsx", detail=response.text[:300])
        logger.info(f"{name}.xlsx pushed to GitHub")
        return 'updated' if existing.status_code == 200 else 'created'
