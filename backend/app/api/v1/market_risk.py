"""Market Risk routes: /market-risk/..."""
from fastapi import APIRouter

from app.controllers.market_risk import MarketRiskController
from app.core.dependencies import AccountServiceDep, RequiredPriceServiceDep
from app.schemas.market_risk import CorrelationViewRequest, MarketDriversRequest, PCAViewRequest
from app.schemas.workspace import ViewResponse

router = APIRouter(prefix="/market-risk", tags=["Market Risk"])


@router.post("/pca-analysis", response_model=ViewResponse)
async def pca_analysis(request: PCAViewRequest, price_service: RequiredPriceServiceDep) -> ViewResponse:
    """Variance explained, eigen weights, eigen index and the assets closest to it"""
    return await MarketRiskController(price_service).get_pca_view(request)


@router.post("/correlation-analysis", response_model=ViewResponse)
async def correlation_analysis(request: CorrelationViewRequest, price_service: RequiredPriceServiceDep) -> ViewResponse:
    """Rolling pair correlation, rolling mean returns, PC1 over time and correlation matrix"""
    return await MarketRiskController(price_service).get_correlation_view(request)


@router.post("/drivers", response_model=ViewResponse)
async def market_drivers(request: MarketDriversRequest, price_service: RequiredPriceServiceDep,
                         account_service: AccountServiceDep) -> ViewResponse:
    """Eigen-portfolio market index, its drivers and risk decomposition vs the workspace series"""
    return await MarketRiskController(price_service, account_service).get_market_drivers(request)
