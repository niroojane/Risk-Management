"""Investment Universe - Prices API endpoints"""
from fastapi import APIRouter

from ....schemas.investment_universe import PricesRequest, PricesResponse
from ....controllers.investment_universe import PricesController
from ....core.dependencies import PriceServiceDep
from ....core.exceptions import ServiceUnavailableError

router = APIRouter()


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
