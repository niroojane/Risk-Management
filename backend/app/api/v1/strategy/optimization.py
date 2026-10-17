"""Strategy - Portfolio optimization API endpoints"""
from fastapi import APIRouter

from ....schemas.strategy import OptimizationRequest, OptimizationResponse
from ....schemas.workspace import BacktestRequest, ViewResponse
from ....controllers.strategy import StrategyController
from ....core.dependencies import RequiredPriceServiceDep

router = APIRouter()


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize(request: OptimizationRequest, price_service: RequiredPriceServiceDep) -> OptimizationResponse:
    """Optimal long-only allocation for each objective under weight and risk constraints"""
    return await StrategyController(price_service).optimize(request)


@router.post("/backtest", response_model=ViewResponse)
async def backtest(request: BacktestRequest, price_service: RequiredPriceServiceDep) -> ViewResponse:
    """Rolling optimization of a core strategy blended with tactical overlays (Fund / Core / Overlay)"""
    return await StrategyController(price_service).backtest(request)
