"""Investment Universe API endpoints"""
from fastapi import APIRouter, HTTPException

from ...schemas.investment_universe import (
    MarketCapRequest,
    MarketCapResponse,
)
from ...controllers.investment_universe import MarketCapController
from ...core.dependencies import BinanceServiceDep
from ...core.exceptions import ExternalAPIError

router = APIRouter(prefix="/investment-universe", tags=["Investment Universe"])


@router.post("/market-cap", response_model=MarketCapResponse)
async def get_market_cap(
    request: MarketCapRequest,
    binance_service: BinanceServiceDep
) -> MarketCapResponse:
    """Get top N cryptocurrencies by market capitalization"""
    # Check service availability
    if binance_service is None:
        raise HTTPException(
            status_code=503,
            detail="Binance API credentials not configured. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
        )

    # Delegate to controller
    try:
        controller = MarketCapController(binance_service)
        return await controller.get_market_cap(request)

    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
