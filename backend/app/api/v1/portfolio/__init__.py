"""Portfolio Router - views comparing the named portfolio series"""
from fastapi import APIRouter

from ....controllers.portfolio import PortfolioController
from ....core.dependencies import AccountServiceDep, RequiredPriceServiceDep
from ....schemas.workspace import (
    BetaViewRequest,
    CalendarViewRequest,
    PairViewRequest,
    PerformanceViewRequest,
    ViewResponse,
    WorkspaceRequest,
)

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.post("/performance", response_model=ViewResponse)
async def performance(request: PerformanceViewRequest, price_service: RequiredPriceServiceDep,
                      account_service: AccountServiceDep) -> ViewResponse:
    """Cumulative performance, drawdown, rolling volatility, return / risk tables and efficient frontier"""
    return await PortfolioController(price_service, account_service).performance(request)


@router.post("/calendar", response_model=ViewResponse)
async def calendar(request: CalendarViewRequest, price_service: RequiredPriceServiceDep,
                   account_service: AccountServiceDep) -> ViewResponse:
    """Returns, volatility, tracking error and Sharpe ratio of a fund vs a benchmark by year / month"""
    return await PortfolioController(price_service, account_service).calendar(request)


@router.post("/return-analysis", response_model=ViewResponse)
async def return_analysis(request: PairViewRequest, price_service: RequiredPriceServiceDep,
                          account_service: AccountServiceDep) -> ViewResponse:
    """Return contribution, benchmark contribution, active contribution and drawdown contribution"""
    return await PortfolioController(price_service, account_service).return_analysis(request)


@router.post("/beta", response_model=ViewResponse)
async def beta(request: BetaViewRequest, price_service: RequiredPriceServiceDep,
               account_service: AccountServiceDep) -> ViewResponse:
    """Rolling asset betas, weights, portfolio betas and beta contribution vs a benchmark series"""
    return await PortfolioController(price_service, account_service).beta(request)


@router.post("/pnl-analysis", response_model=ViewResponse)
async def pnl_analysis(request: WorkspaceRequest, price_service: RequiredPriceServiceDep,
                       account_service: AccountServiceDep) -> ViewResponse:
    """Portfolio value, cumulative P&L, P&L contribution and cumulative return of the real portfolio"""
    return await PortfolioController(price_service, account_service).pnl_analysis(request)
