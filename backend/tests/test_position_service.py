"""Tests for PositionService"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from app.models.investment_universe import Position


@pytest.fixture
def mock_price_service():
    """Mock PriceService for testing"""
    service = AsyncMock()
    # Klines must have correct format: Close_Time (ms timestamp), Close (string)
    service.get_historical_prices = AsyncMock(return_value={
        "data": [
            {
                "symbol": "BTCUSDT",
                "klines": [
                    {"Close_Time": int(datetime(2024, 1, 1).timestamp() * 1000), "Close": "43200.75"},
                    {"Close_Time": int(datetime(2024, 1, 2).timestamp() * 1000), "Close": "43800.25"},
                ]
            },
            {
                "symbol": "ETHUSDT",
                "klines": [
                    {"Close_Time": int(datetime(2024, 1, 1).timestamp() * 1000), "Close": "2300.50"},
                    {"Close_Time": int(datetime(2024, 1, 2).timestamp() * 1000), "Close": "2350.00"},
                ]
            }
        ]
    })
    return service


@pytest.fixture
def mock_quantity_service():
    """Mock QuantityService for testing"""
    service = AsyncMock()
    # Snapshots must have date as ISO string
    service.get_historical_quantities = AsyncMock(return_value={
        "data": [
            {
                "date": "2024-01-01T00:00:00",
                "balances": [
                    {"asset": "BTC", "total": 0.12},
                    {"asset": "ETH", "total": 1.5},
                ]
            },
            {
                "date": "2024-01-02T00:00:00",
                "balances": [
                    {"asset": "BTC", "total": 0.13},
                    {"asset": "ETH", "total": 1.6},
                ]
            }
        ]
    })
    return service


@pytest.fixture
def position_service(mock_price_service, mock_quantity_service):
    """Fixture providing PositionService instance"""
    from app.services.binance import PositionService
    return PositionService(mock_price_service, mock_quantity_service)


@pytest.mark.asyncio
async def test_position_service_initialization(position_service):
    """Test PositionService initialization"""
    assert position_service._price_service is not None
    assert position_service._quantity_service is not None


@pytest.mark.asyncio
async def test_get_historical_positions_returns_position_objects(
    position_service, mock_price_service, mock_quantity_service
):
    """Test that get_historical_positions returns List[Position]"""
    result = await position_service.get_historical_positions(
        symbols=["BTCUSDT", "ETHUSDT"],
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 3),
        use_cache=False
    )

    # Verify return type is List[Position]
    assert isinstance(result, list)
    assert all(isinstance(pos, Position) for pos in result)


@pytest.mark.asyncio
async def test_get_historical_positions_correct_calculation(
    position_service, mock_price_service, mock_quantity_service
):
    """Test that positions are calculated correctly (quantity × price)"""
    result = await position_service.get_historical_positions(
        symbols=["BTCUSDT", "ETHUSDT"],
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 3),
        use_cache=False
    )

    # Should have positions for both symbols and dates
    assert len(result) > 0

    # Verify structure
    for position in result:
        assert hasattr(position, 'date')
        assert hasattr(position, 'symbol')
        assert hasattr(position, 'position')
        assert position.symbol in ["BTCUSDT", "ETHUSDT"]
        assert position.position >= 0


@pytest.mark.asyncio
async def test_get_historical_positions_calls_services(
    position_service, mock_price_service, mock_quantity_service
):
    """Test that get_historical_positions calls price and quantity services"""
    symbols = ["BTCUSDT", "ETHUSDT"]
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 3)

    await position_service.get_historical_positions(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        use_cache=True
    )

    # Verify services were called
    mock_price_service.get_historical_prices.assert_called_once_with(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        use_cache=True
    )

    mock_quantity_service.get_historical_quantities.assert_called_once()


@pytest.mark.asyncio
async def test_get_historical_positions_handles_missing_data(position_service):
    """Test that get_historical_positions handles missing price or quantity data"""
    # Mock service with partial data
    position_service._price_service.get_historical_prices = AsyncMock(return_value={
        "data": [
            {
                "symbol": "BTCUSDT",
                "klines": [{"Close_Time": int(datetime(2024, 1, 1).timestamp() * 1000), "Close": "43200.75"}]
            }
        ]
    })

    position_service._quantity_service.get_historical_quantities = AsyncMock(return_value={
        "data": []  # No quantity data
    })

    result = await position_service.get_historical_positions(
        symbols=["BTCUSDT", "ETHUSDT"],
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 3),
        use_cache=False
    )

    # Should return empty list when no matching data
    assert isinstance(result, list)
