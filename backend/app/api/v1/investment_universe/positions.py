"""Positions API endpoint"""
from fastapi import APIRouter

from ....schemas.investment_universe import PositionsRequest
from ....controllers.investment_universe import PositionsController
from ....core.dependencies import PositionServiceDep
from ....core.exceptions import ServiceUnavailableError

router = APIRouter()


@router.post("/positions")
async def get_positions(
    request: PositionsRequest, position_service: PositionServiceDep
):
    """Get historical positions (quantities × prices) for cryptocurrencies"""
    if position_service is None:
        raise ServiceUnavailableError(
            message="Binance service not configured",
            detail="Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file",
        )

    controller = PositionsController(position_service)
    return await controller.get_positions(request)
