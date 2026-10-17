"""Profile and Yahoo universe routes"""
from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, Query

from ....common import to_payload
from ....core.dependencies import YahooMarketDataDep
from ....core.exceptions import DataValidationError
from ....core.market import MULTI_ASSET, get_currency_settings, get_profile
from ....schemas.profile_schemas import (
    CurrencySettingsModel,
    CurrencyUpdateRequest,
    ProfileModel,
    ProfileResponse,
    TickerCheckRequest,
    TickersRequest,
)
from ....schemas.workspace import ViewResponse
from ....services.yahoo.yahoo_api import QUOTE_TYPE_CLASS

router = APIRouter(tags=["Profile"])


def _profile_model() -> ProfileModel:
    profile = get_profile()
    currency = get_currency_settings()
    classes = sorted({c for classes in [profile.default_universe.keys(), QUOTE_TYPE_CLASS.values()] for c in classes})
    return ProfileModel(
        name=profile.name,
        label=profile.label,
        price_source=profile.price_source,
        benchmark_ticker=profile.benchmark_ticker,
        benchmark_label=profile.benchmark_label,
        cash_assets=list(profile.cash_assets),
        excluded_symbols=list(profile.excluded_symbols),
        include_holdings_in_universe=profile.include_holdings_in_universe,
        data_folder=profile.data_folder,
        default_universe=profile.default_universe,
        asset_classes=classes if profile.name == MULTI_ASSET else [],
        currency=CurrencySettingsModel(base_currency=currency.base_currency,
                                       convert_to_base=currency.convert_to_base,
                                       positions_currency=currency.positions_currency),
    )


def _view(data, message: str) -> ViewResponse:
    return ViewResponse(success=True, data=to_payload(data), message=message, timestamp=datetime.now(timezone.utc))


def _require_multi_asset() -> None:
    if get_profile().name != MULTI_ASSET:
        raise DataValidationError("Yahoo universe endpoints are only available in the multi-asset profile",
                                  detail="Start the backend with start-yahoo.bat (MARKET=multi_asset)")


@router.get("/profile", response_model=ProfileResponse)
async def profile() -> ProfileResponse:
    """Market served by this backend (crypto / multi-asset) and its settings"""
    return ProfileResponse(success=True, data=_profile_model(), timestamp=datetime.now(timezone.utc))


@router.put("/profile/currency", response_model=ProfileResponse)
async def update_currency(request: CurrencyUpdateRequest) -> ProfileResponse:
    """Base currency of the multi-asset prices and values (reload prices afterwards)"""
    _require_multi_asset()
    currency = get_currency_settings()
    if request.base_currency is not None:
        currency.base_currency = request.base_currency
    if request.convert_to_base is not None:
        currency.convert_to_base = request.convert_to_base
    return ProfileResponse(success=True, data=_profile_model(), message="Currency settings updated",
                           timestamp=datetime.now(timezone.utc))


@router.get("/universe/search", response_model=ViewResponse)
async def search(market: YahooMarketDataDep, q: str = Query(..., min_length=1)) -> ViewResponse:
    """Yahoo Finance symbol search: Symbol, Name, Type, Exchange (+ suggested asset class)"""
    _require_multi_asset()
    hits = await market.search(q)
    if not hits.empty:
        hits['Asset Class'] = hits['Type'].map(lambda t: QUOTE_TYPE_CLASS.get(str(t).upper(), 'Other'))
    return _view({'results': hits.set_index('Symbol') if not hits.empty else pd.DataFrame()},
                 f"{len(hits)} result(s) for '{q}'")


@router.post("/universe/details", response_model=ViewResponse)
async def details(request: TickersRequest, market: YahooMarketDataDep) -> ViewResponse:
    """Name, exchange, currency, sector, price, volume, market cap, fund size, expense ratio,
    dividend yield and 52-week range of each ticker (Yahoo Finance)"""
    _require_multi_asset()
    table = await market.details(request.tickers, request.refresh)
    return _view({'details': table}, f"Details of {len(request.tickers)} ticker(s)")


@router.post("/universe/check", response_model=ViewResponse)
async def check(request: TickerCheckRequest, market: YahooMarketDataDep) -> ViewResponse:
    """Can Yahoo price this ticker? Returns its type and asset class before adding it to the universe"""
    _require_multi_asset()
    ticker = request.ticker.strip()
    if not await market.has_prices(ticker):
        raise DataValidationError(f"Yahoo returns no prices for {ticker} -- not added")
    row = (await market.details([ticker])).iloc[0]
    quote_type = row.get('Type') if 'Type' in row else None
    asset_class = request.asset_class or QUOTE_TYPE_CLASS.get(str(quote_type or '').upper(), 'Other')
    return _view({'ticker': ticker, 'type': quote_type, 'asset_class': asset_class,
                  'name': row.get('Name') if 'Name' in row else None},
                 f"{ticker} can be added ({asset_class})")
