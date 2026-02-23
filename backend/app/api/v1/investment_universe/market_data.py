"""Investment Universe - Market Data API endpoints"""
from fastapi import APIRouter

from ....schemas.investment_universe import MarketDataRequest, MarketDataResponse
from ....controllers.investment_universe import MarketDataController
from ....core.dependencies import MarketDataServiceDep

router = APIRouter()


@router.post("/market-data", response_model=MarketDataResponse)
async def get_market_data(
    request: MarketDataRequest, market_data_service: MarketDataServiceDep
) -> MarketDataResponse:
    """Get market data snapshot (prices + returns) for multiple symbols"""
    controller = MarketDataController(market_data_service)
    return await controller.get_market_data(request)
