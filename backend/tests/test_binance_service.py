"""
Tests for BinanceService
Tests essentiels pour le wrapper Binance (sans appels API réels)
"""
import pytest
import pandas as pd


@pytest.mark.asyncio
async def test_binance_service_initialization(mock_binance_credentials, cache_service):
    """
    Test l'initialisation du BinanceService
    Vérifie que le service démarre avec rate limiter et cache
    """
    from app.services.binance_service import BinanceService

    # Initialiser avec credentials mockés
    service = BinanceService(
        api_key=mock_binance_credentials["api_key"],
        api_secret=mock_binance_credentials["api_secret"],
        cache=cache_service,
        enable_rate_limiting=True,
    )

    # Vérifier que le service est initialisé
    assert service.api_key == mock_binance_credentials["api_key"]
    assert service.api_secret == mock_binance_credentials["api_secret"]
    assert service._cache is not None
    assert service._rate_limiter is not None

    # Test sans rate limiting
    service_no_limit = BinanceService(
        api_key=mock_binance_credentials["api_key"],
        api_secret=mock_binance_credentials["api_secret"],
        cache=None,
        enable_rate_limiting=False,
    )

    assert service_no_limit._rate_limiter is None


@pytest.mark.asyncio
async def test_binance_service_dataframe_conversion(mock_binance_credentials):
    """
    Test la conversion DataFrame → JSON
    Important car l'API REST retourne du JSON, pas des DataFrames
    """
    from app.services.binance_service import BinanceService

    service = BinanceService(
        api_key=mock_binance_credentials["api_key"],
        api_secret=mock_binance_credentials["api_secret"],
        cache=None,
        enable_rate_limiting=False,
    )

    # Créer un DataFrame de test
    df = pd.DataFrame({
        'symbol': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
        'price': [50000.0, 3000.0, 1.5],
        'volume': [1000.0, 5000.0, 10000.0],
    })

    # Convertir en dict
    result = service._dataframe_to_dict(df)

    # Vérifier le format
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]['symbol'] == 'BTCUSDT'
    assert result[0]['price'] == 50000.0
    assert result[1]['symbol'] == 'ETHUSDT'


@pytest.mark.asyncio
async def test_binance_service_rate_limiter_stats(mock_binance_credentials):
    """
    Test l'accès aux statistiques du rate limiter
    Utile pour monitoring en production
    """
    from app.services.binance_service import BinanceService

    # Avec rate limiting activé
    service = BinanceService(
        api_key=mock_binance_credentials["api_key"],
        api_secret=mock_binance_credentials["api_secret"],
        cache=None,
        enable_rate_limiting=True,
    )

    stats = service.get_rate_limiter_stats()
    assert "available_weight" in stats
    assert "max_weight" in stats
    assert stats["max_weight"] == 1200

    # Sans rate limiting
    service_no_limit = BinanceService(
        api_key=mock_binance_credentials["api_key"],
        api_secret=mock_binance_credentials["api_secret"],
        cache=None,
        enable_rate_limiting=False,
    )

    stats_disabled = service_no_limit.get_rate_limiter_stats()
    assert stats_disabled == {"rate_limiting": "disabled"}
