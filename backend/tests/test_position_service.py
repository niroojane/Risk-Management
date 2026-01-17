"""Tests for PositionService"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_binance_client(mock_binance_credentials):
    """Mock BinanceClient for testing"""
    from app.services.binance import BinanceClient

    client = BinanceClient(
        api_key=mock_binance_credentials["api_key"],
        api_secret=mock_binance_credentials["api_secret"],
        cache=None,
        enable_rate_limiting=False,
    )

    return client


@pytest.fixture
def position_service(mock_binance_client):
    """Fixture providing PositionService instance"""
    from app.services.binance import PositionService

    return PositionService(mock_binance_client)


@pytest.fixture
def mock_kline_data():
    """Mock kline data from Binance API"""
    return [
        [
            1704067200000,  # Open Time
            "42000.50",     # Open
            "43500.00",     # High
            "41800.00",     # Low
            "43200.75",     # Close
            "1250000.00",   # Volume
            1704153599999,  # Close Time
            "52500000.00",  # Quote Asset Volume
            125000,         # Number of Trades
            "625000.00",    # Taker Buy Base Volume
            "26250000.00",  # Taker Buy Quote Volume
            "0"             # Ignore
        ],
        [
            1704153600000,
            "43200.75",
            "44000.00",
            "42500.00",
            "43800.25",
            "1300000.00",
            1704239999999,
            "55000000.00",
            130000,
            "650000.00",
            "27500000.00",
            "0"
        ]
    ]


@pytest.fixture
def mock_snapshot_data():
    """Mock account snapshot data from Binance API"""
    return {
        "code": 200,
        "msg": "",
        "snapshotVos": [
            {
                "updateTime": 1704067200000,
                "type": "spot",
                "data": {
                    "totalAssetOfBtc": "0.5",
                    "balances": [
                        {"asset": "BTC", "free": "0.12", "locked": "0.00"},
                        {"asset": "ETH", "free": "1.5", "locked": "0.00"},
                    ]
                }
            },
            {
                "updateTime": 1704153600000,
                "type": "spot",
                "data": {
                    "totalAssetOfBtc": "0.52",
                    "balances": [
                        {"asset": "BTC", "free": "0.13", "locked": "0.00"},
                        {"asset": "ETH", "free": "1.6", "locked": "0.00"},
                    ]
                }
            }
        ]
    }


@pytest.mark.asyncio
async def test_position_service_initialization(position_service):
    """Test PositionService initialization"""
    assert position_service._client is not None


@pytest.mark.asyncio
async def test_get_historical_prices(position_service, mock_kline_data):
    """Test get_historical_prices method"""
    with patch.object(
        position_service._client,
        '_run_in_executor',
        new_callable=AsyncMock,
        return_value=mock_kline_data
    ):
        result = await position_service.get_historical_prices(
            symbols=["BTCUSDT"],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 3),
            use_cache=False
        )

        assert result is not None
        assert "symbols" in result
        assert "data" in result
        assert len(result["data"]) == 1
        assert result["data"][0]["symbol"] == "BTCUSDT"
        assert "klines" in result["data"][0]
        assert len(result["data"][0]["klines"]) == 2


@pytest.mark.asyncio
async def test_get_historical_prices_parallel(position_service, mock_kline_data):
    """Test get_historical_prices parallelization with multiple symbols"""
    with patch.object(
        position_service._client,
        '_run_in_executor',
        new_callable=AsyncMock,
        return_value=mock_kline_data
    ):
        result = await position_service.get_historical_prices(
            symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 3),
            use_cache=False
        )

        assert len(result["data"]) == 3
        assert result["data"][0]["symbol"] == "BTCUSDT"
        assert result["data"][1]["symbol"] == "ETHUSDT"
        assert result["data"][2]["symbol"] == "BNBUSDT"


@pytest.mark.asyncio
async def test_get_historical_quantities(position_service, mock_snapshot_data):
    """Test get_historical_quantities method"""
    with patch.object(
        position_service._client,
        '_run_in_executor',
        new_callable=AsyncMock,
        return_value=mock_snapshot_data
    ):
        result = await position_service.get_historical_quantities(
            end_date=datetime(2024, 1, 3),
            limit=30,
            use_cache=False
        )

        assert result is not None
        assert "data" in result
        assert len(result["data"]) == 2
        assert "balances" in result["data"][0]
        assert len(result["data"][0]["balances"]) == 2
        assert result["data"][0]["balances"][0]["asset"] == "BTC"
        assert result["data"][0]["balances"][0]["total"] == 0.12


@pytest.mark.asyncio
async def test_get_historical_positions(position_service, mock_kline_data, mock_snapshot_data):
    """Test get_historical_positions method (quantities × prices)"""
    with patch.object(
        position_service._client,
        '_run_in_executor',
        new_callable=AsyncMock
    ) as mock_executor:
        mock_executor.side_effect = [
            mock_kline_data,  # BTC prices
            mock_kline_data,  # ETH prices
            mock_snapshot_data  # Quantities
        ]

        result = await position_service.get_historical_positions(
            symbols=["BTCUSDT", "ETHUSDT"],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 3),
            use_cache=False
        )

        assert result is not None
        assert "data" in result
        assert len(result["data"]) > 0

        for position in result["data"]:
            assert "date" in position
            assert "symbol" in position
            assert "position" in position
            assert position["symbol"] in ["BTCUSDT", "ETHUSDT"]
