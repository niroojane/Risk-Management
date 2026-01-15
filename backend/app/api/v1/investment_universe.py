"""
Investment Universe API endpoints
Provides market data and metrics for cryptocurrency assets
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime

from ...models.schemas.investment_universe import (
    MarketCapRequest,
    MarketCapResponse,
)
from ...models.entities.investment_universe import MarketCapItem
from ...core.dependencies import BinanceServiceDep
from ...core.exceptions import ExternalAPIError

router = APIRouter(prefix="/investment-universe", tags=["Investment Universe"])


@router.post("/market-cap", response_model=MarketCapResponse)
async def get_market_cap(
    request: MarketCapRequest,
    binance_service: BinanceServiceDep
) -> MarketCapResponse:
    """
    Get top N cryptocurrencies by market capitalization

    Returns a list of cryptocurrencies sorted by market cap, including:
    - Symbol and name
    - Current price
    - Circulating supply
    - Market capitalization

    Requires: BINANCE_API_KEY and BINANCE_API_SECRET environment variables
    """
    if binance_service is None:
        raise HTTPException(
            status_code=503,
            detail="Binance API credentials not configured. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
        )

    try:
        # Fetch market cap data from Binance
        result = await binance_service.get_market_cap(
            quote=request.quote.value,
            use_cache=True
        )

        # Convert to MarketCapItem entities
        market_cap_items = []
        for item in result["data"][:request.top_n]:
            market_cap_items.append(
                MarketCapItem(
                    symbol=item["Ticker"],
                    long_name=item["Long name"],
                    base_asset=item["Short Name"],
                    quote_asset=item["Quote Short Name"],
                    price=float(item["Close"]),
                    supply=float(item["Supply"]),
                    market_cap=float(item["Market Cap"])
                )
            )

        return MarketCapResponse(
            success=True,
            data=market_cap_items,
            message=f"Top {request.top_n} cryptocurrencies by market cap",
            timestamp=datetime.utcnow()
        )

    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
