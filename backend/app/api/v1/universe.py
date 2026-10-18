"""Investment Universe routes: /investment-universe/..."""
from fastapi import APIRouter

from app.controllers.universe import AssetMetricsController, MarketCapController, PricesController
from app.core.dependencies import MarketDataServiceDep, PriceServiceDep, RequiredPriceServiceDep
from app.core.exceptions import ServiceUnavailableError
from app.schemas.universe import (
    AssetMetricsRequest,
    AssetMetricsResponse,
    MarketCapRequest,
    MarketCapResponse,
    PricesRequest,
    PricesResponse,
)

router = APIRouter(prefix="/investment-universe", tags=["Investment Universe"])


@router.post("/market-cap", response_model=MarketCapResponse)
async def get_market_cap(
    request: MarketCapRequest, market_data_service: MarketDataServiceDep
) -> MarketCapResponse:
    """Get all cryptocurrencies by market capitalization (sorted by market cap DESC)"""
    if market_data_service is None:
        raise ServiceUnavailableError(
            message="Binance service not configured",
            detail="Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file",
        )

    controller = MarketCapController(market_data_service)
    return await controller.get_market_cap(request)


@router.post("/prices", response_model=PricesResponse)
async def get_prices(
    request: PricesRequest, price_service: PriceServiceDep
) -> PricesResponse:
    """Get historical prices for multiple symbols within a date range"""
    if price_service is None:
        raise ServiceUnavailableError(
            message="Binance service not configured",
            detail="Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file",
        )

    controller = PricesController(price_service)
    return await controller.get_prices(request)


@router.post("/asset-metrics", response_model=AssetMetricsResponse)
async def get_asset_metrics(request: AssetMetricsRequest, price_service: RequiredPriceServiceDep) -> AssetMetricsResponse:
    """Returns, volatilities, parametric CVaR and max drawdown per symbol"""
    return await AssetMetricsController(price_service).get_asset_metrics(request)
