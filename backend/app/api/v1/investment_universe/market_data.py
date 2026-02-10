"""Investment Universe - Market Data API endpoints"""
from fastapi import APIRouter

from ....schemas.investment_universe import MarketDataRequest, MarketDataResponse
from ....controllers.investment_universe import MarketDataController
from ....core.dependencies import MarketDataServiceDep
from ....core.exceptions import ServiceUnavailableError

router = APIRouter()


@router.post("/market-data", response_model=MarketDataResponse)
async def get_market_data(
    request: MarketDataRequest, market_data_service: MarketDataServiceDep
) -> MarketDataResponse:
    """Get market data snapshot (prices + returns) for multiple symbols"""
    if market_data_service is None:
        raise ServiceUnavailableError(
            message="Binance service not configured",
            detail="Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file",
        )

    controller = MarketDataController(market_data_service)
    return await controller.get_market_data(request)
