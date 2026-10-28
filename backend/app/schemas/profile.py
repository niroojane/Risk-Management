"""Profile and Yahoo universe schemas"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.common import APIResponse
from app.core.market import BASE_CURRENCY_CHOICES


class CurrencySettingsModel(BaseModel):
    base_currency: str = Field(..., description="Currency every price and value is reported in")
    convert_to_base: bool = Field(True, description="Convert the universe prices to the base currency")
    positions_currency: str = Field('USD', description="Currency of the values in the Positions file")
    choices: List[str] = Field(default_factory=lambda: list(BASE_CURRENCY_CHOICES))


class ProfileModel(BaseModel):
    name: str = Field(..., description="'crypto' or 'multi_asset'")
    label: str
    price_source: str
    benchmark_ticker: str
    benchmark_label: str
    cash_assets: List[str]
    excluded_symbols: List[str]
    include_holdings_in_universe: bool
    data_folder: str
    default_universe: Dict[str, List[str]]
    asset_classes: List[str]
    regime_strategies: bool = Field(False, description="The HMM Regime App's scenarios are strategies too")
    currency: CurrencySettingsModel


class ProfileResponse(APIResponse):
    data: ProfileModel


class CurrencyUpdateRequest(BaseModel):
    base_currency: Optional[str] = None
    convert_to_base: Optional[bool] = None

    @field_validator('base_currency')
    @classmethod
    def known_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.upper() not in BASE_CURRENCY_CHOICES:
            raise ValueError(f"base_currency must be one of {', '.join(BASE_CURRENCY_CHOICES)}")
        return v.upper() if v else v


class TickersRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, description="Yahoo symbols, e.g. ['XLK', 'GOLD.PA', '^GSPC']")
    refresh: bool = Field(False, description="Ignore the details cached by the backend")

    @field_validator('tickers')
    @classmethod
    def strip(cls, v: List[str]) -> List[str]:
        # Yahoo symbols are kept as typed ('BRK-B', 'EURUSD=X', '^GSPC')
        return list(dict.fromkeys(t.strip() for t in v if t.strip()))


class TickerCheckRequest(BaseModel):
    ticker: str = Field(..., min_length=1)
    asset_class: Optional[str] = Field(None, description="Asset class chosen by the user (default: from Yahoo)")
