"""Investment Universe - Prices API endpoints"""
from fastapi import APIRouter

from ....schemas.investment_universe import PricesRequest, PricesResponse
from ....controllers.investment_universe import PricesController
from ....core.dependencies import UniverseDataServiceDep
from ....core.exceptions import ServiceUnavailableError

router = APIRouter()


@router.post("/prices", response_model=PricesResponse)
async def get_prices(
    request: PricesRequest, universe_data_service: UniverseDataServiceDep
) -> PricesResponse:
    """Get historical prices for multiple symbols within a date range"""
    if universe_data_service is None:
        raise ServiceUnavailableError(
            message="Binance service not configured",
            detail="Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file",
        )

    controller = PricesController(universe_data_service)
    return await controller.get_prices(request)
