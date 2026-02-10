"""Investment Universe - Market Data API endpoints"""
from fastapi import APIRouter

from ....schemas.investment_universe import PricesRequest, PricesResponse
from ....controllers.investment_universe import MarketDataController
from ....core.dependencies import MarketDataServiceDep
from ....core.exceptions import ServiceUnavailableError

router = APIRouter()


@router.post("/market-data", response_model=PricesResponse)
async def get_market_data(
    request: PricesRequest, market_data_service: MarketDataServiceDep
) -> PricesResponse:
    """Get market data snapshot (prices + returns) for multiple symbols"""
    if market_data_service is None:
        raise ServiceUnavailableError(
            message="Binance service not configured",
            detail="Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file",
        )

    controller = MarketDataController(market_data_service)
    return await controller.get_market_data(request)
