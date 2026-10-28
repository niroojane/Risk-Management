"""Strategy routes: /strategy/..."""
from datetime import datetime, timezone

from fastapi import APIRouter

from app.controllers.strategy import StrategyController
from app.core.dependencies import RequiredPriceServiceDep
from app.core.market import get_profile
from app.schemas.strategy import BacktestRequest, OptimizationRequest, OptimizationResponse
from app.schemas.workspace import ViewResponse

router = APIRouter(prefix="/strategy", tags=["Strategy"])


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize(request: OptimizationRequest, price_service: RequiredPriceServiceDep) -> OptimizationResponse:
    """Optimal long-only allocation for each objective under weight and risk constraints"""
    return await StrategyController(price_service).optimize(request)


@router.get("/regime-scenarios", response_model=ViewResponse)
async def regime_scenarios() -> ViewResponse:
    """Scenarios of the HMM Regime App offered as strategies ('regime:<scenario>'): the built-in
    default and the ones saved in HMM_Scenarios.json (multi-asset profile only, else empty)"""
    rows = StrategyController.regime_scenarios() if get_profile().regime_strategies else []
    return ViewResponse(success=True, data={'scenarios': rows}, message=f"{len(rows)} regime scenario(s)",
                        timestamp=datetime.now(timezone.utc))


@router.post("/backtest", response_model=ViewResponse)
async def backtest(request: BacktestRequest, price_service: RequiredPriceServiceDep) -> ViewResponse:
    """Rolling optimization of a core strategy blended with tactical overlays (Fund / Core / Overlay)"""
    return await StrategyController(price_service).backtest(request)
