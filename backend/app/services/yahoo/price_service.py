"""Daily prices from Yahoo Finance, converted to the base currency (multi-asset profile)"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd

from .market_data import YahooMarketData
from src.MultiAsset import quote_currencies
from ..binance.price_service import PriceService
from ...core.market import CurrencySettings
from src import Yahoo_API as yahoo_api

logger = logging.getLogger(__name__)


class YahooPriceService(PriceService):
    """Same interface as the Binance PriceService, so every analytics endpoint works unchanged.

    Prices are Yahoo adjusted closes; with `convert_to_base` they are converted
    to the base currency with the day's FX (pence quotes included), as the
    Multi Asset App's prices_to_base.
    """

    def __init__(self, market_data: YahooMarketData, currency: CurrencySettings):
        self._market = market_data
        self._currency = currency

    async def get_price_frame(
        self,
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        if end_date is None:
            end_date = datetime.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        local = await self._market.close(symbols, start_date, end_date, use_cache)
        if local.empty or not self._currency.convert_to_base:
            return local

        base = self._currency.base_currency
        ccys = quote_currencies(local.columns, await self._market.currencies(local.columns, use_cache),
                                trades=None, base=base)
        fx = await self._market.fx(ccys.values, base, start_date, use_cache)
        if fx.attrs.get('missing'):
            logger.warning(f"No FX rate for {fx.attrs['missing']} -> {base}; left unconverted")
        prices = yahoo_api.to_base_currency(local, ccys, fx)
        prices.attrs['currencies'] = ccys.to_dict()
        return prices
