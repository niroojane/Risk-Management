"""Tests for BinanceClient"""
import pytest
import pandas as pd


@pytest.mark.asyncio
async def test_binance_service_initialization(mock_binance_credentials, cache_service):
    """Test BinanceClient initialization with rate limiter and cache"""
    from app.services.binance import BinanceClient

    client = BinanceClient(
        api_key=mock_binance_credentials["api_key"],
        api_secret=mock_binance_credentials["api_secret"],
        cache=cache_service,
        enable_rate_limiting=True,
    )

    assert client._cache is not None
    assert client._rate_limiter is not None
    assert client.spot is not None

    client_no_limit = BinanceClient(
        api_key=mock_binance_credentials["api_key"],
        api_secret=mock_binance_credentials["api_secret"],
        cache=None,
        enable_rate_limiting=False,
    )

    assert client_no_limit._rate_limiter is None


@pytest.mark.asyncio
async def test_binance_service_dataframe_conversion(mock_binance_credentials):
    """Test DataFrame → JSON conversion"""
    from app.services.binance import BinanceClient

    client = BinanceClient(
        api_key=mock_binance_credentials["api_key"],
        api_secret=mock_binance_credentials["api_secret"],
        cache=None,
        enable_rate_limiting=False,
    )

    df = pd.DataFrame({
        'symbol': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
        'price': [50000.0, 3000.0, 1.5],
        'volume': [1000.0, 5000.0, 10000.0],
    })

    result = client._dataframe_to_dict(df)

    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]['symbol'] == 'BTCUSDT'
    assert result[0]['price'] == 50000.0
    assert result[1]['symbol'] == 'ETHUSDT'


@pytest.mark.asyncio
async def test_binance_service_rate_limiter_stats(mock_binance_credentials):
    """Test rate limiter statistics"""
    from app.services.binance import BinanceClient

    client = BinanceClient(
        api_key=mock_binance_credentials["api_key"],
        api_secret=mock_binance_credentials["api_secret"],
        cache=None,
        enable_rate_limiting=True,
    )

    stats = client.get_rate_limiter_stats()
    assert "available_weight" in stats
    assert "max_weight" in stats
    assert stats["max_weight"] == 1200

    client_no_limit = BinanceClient(
        api_key=mock_binance_credentials["api_key"],
        api_secret=mock_binance_credentials["api_secret"],
        cache=None,
        enable_rate_limiting=False,
    )

    stats_disabled = client_no_limit.get_rate_limiter_stats()
    assert stats_disabled == {"rate_limiting": "disabled"}


@pytest.mark.asyncio
async def test_price_frame_requests_whole_utc_days_end_included():
    """Daily candles are UTC days: chunks run from 00:00 UTC of the start date to the end of
    the end date (today's open candle included), with no gap or overlap between chunks"""
    from datetime import datetime, timezone
    from app.services.binance.price_service import PriceService

    calls = []

    class StubClient:
        spot = None

        async def _run_in_executor(self, func, spot, symbols, start_ms, end_ms):
            calls.append((start_ms, end_ms))
            return pd.DataFrame({'BTCUSDT': [1.0]}, index=['2026-01-01'])

        async def fetch_with_cache(self, cache_key, api_call, weight, ttl, use_cache):
            return await api_call()

    def utc_ms(*day):
        return int(datetime(*day, tzinfo=timezone.utc).timestamp() * 1000)

    service = PriceService(StubClient())
    await service.get_price_frame(['BTCUSDT'], datetime(2026, 1, 1), datetime(2026, 1, 10, 15, 30))
    assert calls == [(utc_ms(2026, 1, 1), utc_ms(2026, 1, 11) - 1)]

    calls.clear()
    await service.get_price_frame(['BTCUSDT'], datetime(2026, 1, 1), datetime(2026, 4, 15))
    assert sorted(calls) == [(utc_ms(2026, 1, 1), utc_ms(2026, 4, 1) - 1),
                             (utc_ms(2026, 4, 1), utc_ms(2026, 4, 16) - 1)]
