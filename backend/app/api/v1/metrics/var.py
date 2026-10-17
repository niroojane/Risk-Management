"""Risk Metrics - Value at Risk API endpoint"""
from fastapi import APIRouter

from ....schemas.metrics import VaRRequest, VaRResponse
from ....controllers.metrics import MetricsController
from ....core.dependencies import RequiredPriceServiceDep

router = APIRouter()


@router.post("/var", response_model=VaRResponse)
async def get_value_at_risk(request: VaRRequest, price_service: RequiredPriceServiceDep) -> VaRResponse:
    """Historical, parametric and simulated VaR / CVaR of each allocation, with optional backtest"""
    return await MetricsController(price_service).get_var(request)
