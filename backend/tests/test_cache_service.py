"""
Tests for CacheService
Tests essentiels pour le cache en mémoire avec TTL
"""
import pytest
import asyncio


@pytest.mark.asyncio
async def test_cache_basic_operations(cache_service):
    """
    Test les opérations de base : set, get, delete
    Couvre le happy path principal
    """
    # Set : stocker une valeur
    await cache_service.set("test_key", {"data": "test_value"})

    # Get : récupérer la valeur
    value = await cache_service.get("test_key")
    assert value == {"data": "test_value"}

    # Delete : supprimer la valeur
    deleted = await cache_service.delete("test_key")
    assert deleted is True

    # Vérifier que la valeur a disparu
    value = await cache_service.get("test_key")
    assert value is None

    # Test différents types de données
    await cache_service.set("int_key", 42)
    await cache_service.set("list_key", [1, 2, 3])
    await cache_service.set("dict_key", {"a": 1, "b": 2})

    assert await cache_service.get("int_key") == 42
    assert await cache_service.get("list_key") == [1, 2, 3]
    assert await cache_service.get("dict_key") == {"a": 1, "b": 2}


@pytest.mark.asyncio
async def test_cache_ttl_expiration(cache_service):
    """
    Test l'expiration automatique avec TTL
    Critique car c'est la fonctionnalité principale du cache
    """
    # Stocker avec TTL court (1 seconde)
    await cache_service.set("expiring_key", "value", ttl=1)

    # Immédiatement après, la valeur existe
    value = await cache_service.get("expiring_key")
    assert value == "value"

    # Attendre l'expiration
    await asyncio.sleep(1.5)

    # Après expiration, la valeur doit être None
    value = await cache_service.get("expiring_key")
    assert value is None

    # Test avec plusieurs TTL différents
    await cache_service.set("short_ttl", "value1", ttl=1)
    await cache_service.set("long_ttl", "value2", ttl=10)

    await asyncio.sleep(1.5)

    # short_ttl a expiré, long_ttl existe encore
    assert await cache_service.get("short_ttl") is None
    assert await cache_service.get("long_ttl") == "value2"


@pytest.mark.asyncio
async def test_cache_handles_missing_keys(cache_service):
    """
    Test la gestion des clés inexistantes
    Important pour éviter les erreurs en production
    """
    # Get d'une clé qui n'existe pas
    value = await cache_service.get("non_existent_key")
    assert value is None

    # Delete d'une clé qui n'existe pas
    deleted = await cache_service.delete("non_existent")
    assert deleted is False

    # Exists pour clé existante vs non-existante
    await cache_service.set("exists_key", "value")
    assert await cache_service.exists("exists_key") is True
    assert await cache_service.exists("non_existent") is False


@pytest.mark.asyncio
async def test_cache_statistics(cache_service):
    """
    Test le tracking des statistiques (hits/misses/hit rate)
    Utile pour le monitoring en production
    """
    # Reset pour test propre
    cache_service.reset_stats()

    # Effectuer des opérations
    await cache_service.set("key1", "value1")
    await cache_service.set("key2", "value2")

    await cache_service.get("key1")  # hit
    await cache_service.get("key1")  # hit
    await cache_service.get("non_existent")  # miss

    # Vérifier les stats
    stats = cache_service.get_stats()

    assert stats["sets"] == 2
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["total_requests"] == 3
    assert stats["hit_rate_percent"] == pytest.approx(66.67, rel=0.1)
