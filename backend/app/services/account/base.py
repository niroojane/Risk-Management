"""Interface of the real-portfolio providers (Binance account or Excel files)"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import pandas as pd


@dataclass
class AccountHistory:
    """Daily position values (+ 'Total', in base currency) and units held"""
    positions: pd.DataFrame
    quantities: pd.DataFrame


class PortfolioAccount(ABC):
    """What the app needs from the real portfolio, whatever its source"""

    @abstractmethod
    async def holdings_view(self, use_cache: bool = True) -> Dict[str, Any]:
        """{'holdings': table, 'tickers': held assets, 'weights': {ticker: weight} without cash}"""

    @abstractmethod
    async def positioning(self, model_weights: pd.Series) -> Dict[str, Any]:
        """{'positioning': current holdings vs the model, 'holdings': table}"""

    @abstractmethod
    async def pnl(self, use_cache: bool = True) -> Dict[str, Any]:
        """{'pnl': P&L per asset, 'trades': trade history, 'warnings': [...]}"""

    @abstractmethod
    async def get_history(self, use_cache: bool = True) -> AccountHistory:
        """Saved daily positions and quantities"""

    @abstractmethod
    async def get_history_prices(self, history: AccountHistory, use_cache: bool = True) -> pd.DataFrame:
        """Daily prices (base currency) of every asset held in the history"""

    @abstractmethod
    async def pnl_history(self, history: AccountHistory, prices: pd.DataFrame,
                          use_cache: bool = True) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """(P&L per asset + 'Total' each day, daily change of the total, warnings)"""

    @abstractmethod
    async def upload(self) -> Dict[str, Any]:
        """Save the history files ({'files': {name: status}, 'messages': [...]})"""
