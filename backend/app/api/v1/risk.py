"""Risk Analysis routes: /risk/... and /metrics/var"""
from fastapi import APIRouter

from app.controllers.risk import RiskController
from app.core.dependencies import AccountServiceDep, RequiredPriceServiceDep
from app.schemas.risk import (
    RiskContributionRequest,
    RiskTrajectoryRequest,
    StressPreviewRequest,
    TrackingErrorViewRequest,
    VaRHistoryRequest,
    VaRRequest,
    VaRResponse,
)
from app.schemas.workspace import ViewResponse

router = APIRouter(prefix="/risk", tags=["Risk Analysis"])
var_router = APIRouter(prefix="/metrics", tags=["Risk Analysis"])


@router.post("/contribution", response_model=ViewResponse)
async def contribution(request: RiskContributionRequest, price_service: RequiredPriceServiceDep) -> ViewResponse:
    """Simulated P&L and ex-ante risk contribution of a fund, excess vs benchmark, ex-ante metrics"""
    return await RiskController(price_service).contribution(request)


@router.post("/trajectory", response_model=ViewResponse)
async def trajectory(request: RiskTrajectoryRequest, price_service: RequiredPriceServiceDep,
                     account_service: AccountServiceDep) -> ViewResponse:
    """Rolling ex-ante volatility of every series and its decomposition"""
    return await RiskController(price_service, account_service).trajectory(request)


@router.post("/tracking-error", response_model=ViewResponse)
async def tracking_error(request: TrackingErrorViewRequest, price_service: RequiredPriceServiceDep,
                         account_service: AccountServiceDep) -> ViewResponse:
    """Rolling ex-ante tracking error of every series and decomposition of every spread"""
    return await RiskController(price_service, account_service).tracking_error(request)


@router.post("/var-history", response_model=ViewResponse)
async def var_history(request: VaRHistoryRequest, price_service: RequiredPriceServiceDep,
                      account_service: AccountServiceDep) -> ViewResponse:
    """Rolling simulated VaR / CVaR of every series and their per-asset VaR / CVaR"""
    return await RiskController(price_service, account_service).var_history(request)


@router.post("/stress-preview", response_model=ViewResponse)
async def stress_preview(request: StressPreviewRequest, price_service: RequiredPriceServiceDep) -> ViewResponse:
    """Means, volatilities and correlations before / after the stress grid and mean shocks"""
    return await RiskController(price_service).stress_preview(request)


@var_router.post("/var", response_model=VaRResponse)
async def get_value_at_risk(request: VaRRequest, price_service: RequiredPriceServiceDep) -> VaRResponse:
    """Historical, parametric and simulated VaR / CVaR of each allocation, with optional backtest"""
    return await RiskController(price_service).value_at_risk(request)
