"""Positions API endpoint"""
from fastapi import APIRouter

from ....schemas.investment_universe import PositionsRequest
from ....controllers.investment_universe import PositionsController
from ....core.dependencies import PositionServiceDep

router = APIRouter()


@router.post("/positions")
async def get_positions(
    request: PositionsRequest, position_service: PositionServiceDep
):
    """Get historical positions (quantities × prices) for cryptocurrencies"""
    controller = PositionsController(position_service)
    return await controller.get_positions(request)
