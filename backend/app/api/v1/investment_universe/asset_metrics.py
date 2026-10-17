"""Investment Universe - Asset Metrics API endpoint"""
from fastapi import APIRouter

from ....schemas.investment_universe import AssetMetricsRequest, AssetMetricsResponse
from ....controllers.investment_universe import AssetMetricsController
from ....core.dependencies import RequiredPriceServiceDep

router = APIRouter()


@router.post("/asset-metrics", response_model=AssetMetricsResponse)
async def get_asset_metrics(request: AssetMetricsRequest, price_service: RequiredPriceServiceDep) -> AssetMetricsResponse:
    """Returns, volatilities, parametric CVaR and max drawdown per symbol"""
    return await AssetMetricsController(price_service).get_asset_metrics(request)
