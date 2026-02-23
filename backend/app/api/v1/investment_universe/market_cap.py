"""Investment Universe - Market Cap API endpoints"""
from fastapi import APIRouter

from ....schemas.investment_universe import MarketCapRequest, MarketCapResponse
from ....controllers.investment_universe import MarketCapController
from ....core.dependencies import MarketCapServiceDep

router = APIRouter()


@router.post("/market-cap", response_model=MarketCapResponse)
async def get_market_cap(
    request: MarketCapRequest, market_cap_service: MarketCapServiceDep
) -> MarketCapResponse:
    """Get all cryptocurrencies by market capitalization (sorted by market cap DESC)"""
    controller = MarketCapController(market_cap_service)
    return await controller.get_market_cap(request)
