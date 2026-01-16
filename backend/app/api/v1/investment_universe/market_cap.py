"""Investment Universe API endpoints"""
from fastapi import APIRouter

from ....schemas.investment_universe import MarketCapRequest, MarketCapResponse
from ....controllers.investment_universe import MarketCapController
from ....core.dependencies import MarketDataServiceDep
from ....core.exceptions import ServiceUnavailableError

router = APIRouter(prefix="/investment-universe", tags=["Investment Universe"])


@router.post("/market-cap", response_model=MarketCapResponse)
async def get_market_cap(
    request: MarketCapRequest, market_data_service: MarketDataServiceDep
) -> MarketCapResponse:
    """Get top N cryptocurrencies by market capitalization"""
    if market_data_service is None:
        raise ServiceUnavailableError(
            message="Binance service not configured",
            detail="Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file",
        )

    controller = MarketCapController(market_data_service)
    return await controller.get_market_cap(request)
