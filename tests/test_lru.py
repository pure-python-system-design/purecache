"""High-quality specification tests for LRUCache.

Follows Arrange-Act-Assert and the testing pyramid:
- Unit: single operation, one assertion focus.
- Integration: multiple operations, eviction + ordering behavior.
"""

import pytest

from purecache.backends.lru import LRUCache


@pytest.fixture
def cache() -> LRUCache:
    """Fresh LRUCache with capacity 3 per test."""
    return LRUCache(3)


# --- Unit: get behavior ---


async def test_get_missing_returns_none(cache: LRUCache) -> None:
    """get for a key that was never put returns None."""
    # Arrange: empty cache (fixture)

    # Act
    result = await cache.get("missing")

    # Assert
    assert result is None


async def test_get_after_put_returns_value(cache: LRUCache) -> None:
    """After put(key, value), get(key) returns that value."""
    # Arrange
    await cache.put("a", 42)

    # Act
    result = await cache.get("a")

    # Assert
    assert result == 42


async def test_get_after_overwrite_returns_latest_value(cache: LRUCache) -> None:
    """Two puts for same key; get returns the last value."""
    # Arrange
    await cache.put("a", 1)
    await cache.put("a", 2)

    # Act
    result = await cache.get("a")

    # Assert
    assert result == 2


# --- Unit: put behavior (no eviction) ---


async def test_put_stores_value_by_key(cache: LRUCache) -> None:
    """put stores value; get with same key returns it."""
    # Arrange: empty cache

    # Act
    await cache.put("x", 10)

    # Assert
    assert await cache.get("x") == 10


async def test_put_multiple_keys_stores_independently(cache: LRUCache) -> None:
    """Several string keys store and retrieve independently."""
    # Arrange
    await cache.put("x", 10)
    await cache.put("y", 20)
    await cache.put("z", 30)

    # Act
    x_val = await cache.get("x")
    y_val = await cache.get("y")
    z_val = await cache.get("z")

    # Assert
    assert x_val == 10
    assert y_val == 20
    assert z_val == 30


# --- Unit: value types (Any) ---


async def test_put_get_int_value(cache: LRUCache) -> None:
    # Arrange
    await cache.put("k", 1)

    # Act
    result = await cache.get("k")

    # Assert
    assert result == 1


async def test_put_get_str_value(cache: LRUCache) -> None:
    # Arrange
    await cache.put("k", "hello")

    # Act
    result = await cache.get("k")

    # Assert
    assert result == "hello"


async def test_put_get_dict_value(cache: LRUCache) -> None:
    # Arrange
    await cache.put("k", {"nested": True})

    # Act
    result = await cache.get("k")

    # Assert
    assert result == {"nested": True}


async def test_put_get_none_value(cache: LRUCache) -> None:
    # Arrange
    await cache.put("k", None)

    # Act
    result = await cache.get("k")

    # Assert
    assert result is None


async def test_put_get_object_value(cache: LRUCache) -> None:
    # Arrange
    obj = object()
    await cache.put("k", obj)

    # Act
    result = await cache.get("k")

    # Assert
    assert result is obj


async def test_put_get_empty_string_key(cache: LRUCache) -> None:
    """Empty string key is allowed."""
    # Arrange
    await cache.put("", "empty")

    # Act
    result = await cache.get("")

    # Assert
    assert result == "empty"


# --- Unit: capacity 1 ---


async def test_capacity_one_put_get_returns_value() -> None:
    """LRUCache(1): single put then get returns value."""
    # Arrange
    cache = LRUCache(1)
    await cache.put("first", 1)

    # Act
    result = await cache.get("first")

    # Assert
    assert result == 1


async def test_capacity_one_second_put_evicts_first() -> None:
    """LRUCache(1): second put evicts first key."""
    # Arrange
    cache = LRUCache(1)
    await cache.put("first", 1)
    await cache.put("second", 2)

    # Act
    first_result = await cache.get("first")
    second_result = await cache.get("second")

    # Assert
    assert first_result is None
    assert second_result == 2


# --- Integration: eviction and LRU order ---


async def test_eviction_removes_oldest_when_at_capacity(cache: LRUCache) -> None:
    """When at capacity, put of new key evicts the least recently used (oldest)."""
    # Arrange: fill to capacity
    await cache.put("a", 1)
    await cache.put("b", 2)
    await cache.put("c", 3)

    # Act
    await cache.put("d", 4)

    # Assert: first key evicted, others and new key present
    assert await cache.get("a") is None
    assert await cache.get("b") == 2
    assert await cache.get("c") == 3
    assert await cache.get("d") == 4


async def test_get_touches_and_protects_from_eviction(cache: LRUCache) -> None:
    """get(key) refreshes order; that key is not evicted on next insert."""
    # Arrange
    await cache.put("a", 1)
    await cache.put("b", 2)
    await cache.put("c", 3)
    await cache.get("a")

    # Act
    await cache.put("d", 4)

    # Assert: b evicted (second-oldest), a protected by get
    assert await cache.get("a") == 1
    assert await cache.get("b") is None
    assert await cache.get("c") == 3
    assert await cache.get("d") == 4


async def test_put_refreshes_order(cache: LRUCache) -> None:
    """Overwriting existing key with put counts as recent; not evicted next."""
    # Arrange
    await cache.put("a", 1)
    await cache.put("b", 2)
    await cache.put("c", 3)
    await cache.put("a", 10)

    # Act
    await cache.put("d", 4)

    # Assert: b evicted, a refreshed by overwrite
    assert await cache.get("a") == 10
    assert await cache.get("b") is None
    assert await cache.get("c") == 3
    assert await cache.get("d") == 4


async def test_repeated_put_same_key_keeps_latest_until_evicted(
    cache: LRUCache,
) -> None:
    """Repeated put to same key keeps latest; eviction when others fill capacity."""
    # Arrange
    for i in range(10):
        await cache.put("same", i)

    # Act & Assert: same key still present with latest value
    assert await cache.get("same") == 9

    # Act: fill capacity with other keys
    await cache.put("b", 2)
    await cache.put("c", 3)
    await cache.put("d", 4)

    # Assert: same evicted, others present
    assert await cache.get("same") is None
    assert await cache.get("b") == 2
    assert await cache.get("c") == 3
    assert await cache.get("d") == 4


async def test_sequential_put_get_ordering(cache: LRUCache) -> None:
    """Multiple await get/put in sequence behave correctly (no shared state bugs)."""
    # Arrange & Act: interleaved put/get
    await cache.put("k1", 1)
    v1 = await cache.get("k1")
    await cache.put("k2", 2)
    v2 = await cache.get("k2")
    await cache.put("k3", 3)
    v3 = await cache.get("k3")

    # Assert
    assert v1 == 1
    assert v2 == 2
    assert v3 == 3

    # Act: overflow
    await cache.put("k4", 4)

    # Assert: k1 evicted (oldest), k2,k3,k4 present
    assert await cache.get("k1") is None
    assert await cache.get("k2") == 2
    assert await cache.get("k3") == 3
    assert await cache.get("k4") == 4
