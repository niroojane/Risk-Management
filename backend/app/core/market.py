"""Market profile: which data the backend serves (crypto from Binance, or multi-asset from Yahoo)

Selected at start-up with the MARKET environment variable ('crypto' or
'multi_asset'), set by start-binance.bat / start-yahoo.bat. Everything that
differs between the Crypto App and the Multi Asset App notebooks lives here;
the analytics are shared.
"""
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Tuple

from .config import settings

CRYPTO = 'crypto'
MULTI_ASSET = 'multi_asset'

FIAT_CURRENCIES: Tuple[str, ...] = ('USD', 'EUR', 'GBP', 'CHF', 'JPY', 'CAD', 'AUD', 'HKD', 'SEK', 'NOK',
                                    'DKK', 'SGD', 'HUF', 'PLN', 'CZK', 'NZD', 'ZAR', 'ILS', 'CNY', 'INR')
BASE_CURRENCY_CHOICES: Tuple[str, ...] = ('USD', 'EUR', 'GBP', 'CHF', 'JPY', 'HUF', 'CAD', 'AUD', 'SEK', 'NOK',
                                          'DKK', 'PLN', 'CZK')


@dataclass(frozen=True)
class MarketProfile:
    name: str
    label: str
    price_source: str
    benchmark_ticker: str
    benchmark_label: str
    # held but never part of the investment universe; no return of their own
    cash_assets: Tuple[str, ...]
    # never part of the universe (stablecoins)
    excluded_symbols: Tuple[str, ...]
    # GitHub folder and file names of the saved portfolio history
    data_folder: str
    positions_file: str
    quantities_file: str
    trades_file: str
    current_portfolio_file: str = ''
    # the account's assets are added to the universe on 'Get Prices'
    include_holdings_in_universe: bool = True
    # the backtest's 'Model' is its last complete period (-2) or its last row (-1)
    model_row: int = -2
    default_universe: Dict[str, List[str]] = field(default_factory=dict)


CRYPTO_PROFILE = MarketProfile(
    name=CRYPTO,
    label='Crypto',
    price_source='Binance',
    benchmark_ticker='BTCUSDT',
    benchmark_label='Bitcoin',
    cash_assets=('USDTUSDT',),
    excluded_symbols=('USDTUSDT', 'USDCUSDT'),
    data_folder=settings.GITHUB_DATA_FOLDER,
    positions_file='Positions',
    quantities_file='Quantities',
    trades_file='Trade History Reconstructed',
)

MULTI_ASSET_PROFILE = MarketProfile(
    name=MULTI_ASSET,
    label='Multi Asset',
    price_source='Yahoo Finance',
    benchmark_ticker='^GSPC',
    benchmark_label='Benchmark',
    cash_assets=FIAT_CURRENCIES + ('Cash',),
    excluded_symbols=(),
    data_folder='ETF',
    positions_file='Positions2',
    quantities_file='Quantities2',
    trades_file='Trade History2',
    current_portfolio_file='Current Portfolio2',
    include_holdings_in_universe=False,
    model_row=-1,
    default_universe={
        'Commodities': ['ISLN.L', 'GOLD.PA', 'BZ=F'],
        'Bonds': ['IEF', 'IEI'],
        'Credit': ['DHY', 'LQD'],
        'Equity': ['^GSPC', 'IDU', 'XLK', 'SOXX', 'XLP', 'XLY', 'IYJ', 'MXI', 'IYE',
                   'PICK', 'EXV5.DE', 'IUHC.L', 'IYG', 'XSW'],
    },
)


@lru_cache()
def get_profile() -> MarketProfile:
    market = (settings.MARKET or CRYPTO).strip().lower()
    if market not in (CRYPTO, MULTI_ASSET):
        raise ValueError(f"MARKET must be '{CRYPTO}' or '{MULTI_ASSET}', got {settings.MARKET!r}")
    return MULTI_ASSET_PROFILE if market == MULTI_ASSET else CRYPTO_PROFILE


@dataclass
class CurrencySettings:
    """Base currency of the multi-asset prices (changeable at runtime, like the notebook's dropdown)"""
    base_currency: str = 'USD'
    convert_to_base: bool = True
    # currency the values of the Positions file are expressed in
    positions_currency: str = 'USD'


@lru_cache()
def get_currency_settings() -> CurrencySettings:
    return CurrencySettings()
