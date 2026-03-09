import asyncio

import pytest

from purecache.backends.lru import LRUCache


@pytest.fixture
def cache() -> LRUCache:
    """Fresh LRUCache(3) per test."""
    return LRUCache(3)


def test_capacity_zero_raises() -> None:
    with pytest.raises(ValueError, match="capacity must be >= 1"):
        LRUCache(0)


def test_capacity_negative_raises() -> None:
    with pytest.raises(ValueError, match="capacity must be >= 1"):
        LRUCache(-5)


def test_initial_len_is_zero(cache: LRUCache) -> None:
    assert len(cache) == 0


def test_len_grows_with_put(cache: LRUCache) -> None:
    asyncio.run(cache.put("a", 1))
    assert len(cache) == 1


def test_len_does_not_exceed_capacity(cache: LRUCache) -> None:
    async def _fill() -> None:
        for i in range(10):
            await cache.put(f"k{i}", i)

    asyncio.run(_fill())
    assert len(cache) == 3


@pytest.mark.asyncio
async def test_get_missing_returns_none(cache: LRUCache) -> None:
    assert await cache.get("missing") is None


@pytest.mark.asyncio
async def test_get_after_put_returns_value(cache: LRUCache) -> None:
    await cache.put("a", 42)
    assert await cache.get("a") == 42


@pytest.mark.asyncio
async def test_get_after_overwrite_returns_latest(cache: LRUCache) -> None:
    await cache.put("a", 1)
    await cache.put("a", 2)
    assert await cache.get("a") == 2


@pytest.mark.asyncio
async def test_get_does_not_affect_len(cache: LRUCache) -> None:
    await cache.put("a", 1)
    await cache.get("a")
    assert len(cache) == 1


@pytest.mark.asyncio
async def test_put_none_value_is_a_hit_not_a_miss(cache: LRUCache) -> None:
    """Caching None must be distinguishable from a cache miss.

    Without a _MISSING sentinel, get() returns None for both cases —
    this test would pass for the wrong reason.  We verify the key is
    actually present via __len__ to make intent explicit.
    """
    await cache.put("k", None)

    result = await cache.get("k")

    assert result is None
    assert len(cache) == 1  # key exists — this is a hit, not a miss


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        3.14,
        "",
        "hello",
        [],
        [1, 2, 3],
        {},
        {"nested": True},
        False,
        True,
    ],
)
async def test_put_get_roundtrip(cache: LRUCache, value: object) -> None:
    await cache.put("k", value)
    assert await cache.get("k") == value


@pytest.mark.asyncio
async def test_put_get_preserves_object_identity(cache: LRUCache) -> None:
    """get() returns the exact object that was put, not a copy."""
    obj = object()
    await cache.put("k", obj)
    assert await cache.get("k") is obj


@pytest.mark.asyncio
async def test_empty_string_is_a_valid_key(cache: LRUCache) -> None:
    await cache.put("", "empty-key")
    assert await cache.get("") == "empty-key"


@pytest.mark.asyncio
async def test_capacity_one_stores_single_value() -> None:
    cache = LRUCache(1)
    await cache.put("a", 1)
    assert await cache.get("a") == 1


@pytest.mark.asyncio
async def test_capacity_one_second_put_evicts_first() -> None:
    cache = LRUCache(1)
    await cache.put("first", 1)
    await cache.put("second", 2)

    assert await cache.get("first") is None
    assert await cache.get("second") == 2


@pytest.mark.asyncio
async def test_eviction_removes_lru_key_on_overflow(cache: LRUCache) -> None:
    """Inserting beyond capacity evicts the least recently used key."""
    await cache.put("a", 1)
    await cache.put("b", 2)
    await cache.put("c", 3)

    await cache.put("d", 4)  # triggers eviction of "a"

    assert await cache.get("a") is None
    assert await cache.get("b") == 2
    assert await cache.get("c") == 3
    assert await cache.get("d") == 4


@pytest.mark.asyncio
async def test_get_promotes_key_protecting_it_from_eviction(cache: LRUCache) -> None:
    """get() refreshes recency — the accessed key is not evicted next."""
    await cache.put("a", 1)
    await cache.put("b", 2)
    await cache.put("c", 3)
    await cache.get("a")  # "a" becomes MRU; "b" is now LRU

    await cache.put("d", 4)  # should evict "b"

    assert await cache.get("a") == 1
    assert await cache.get("b") is None
    assert await cache.get("c") == 3
    assert await cache.get("d") == 4


@pytest.mark.asyncio
async def test_put_update_promotes_key_protecting_it_from_eviction(
    cache: LRUCache,
) -> None:
    """Overwriting an existing key via put() also refreshes recency."""
    await cache.put("a", 1)
    await cache.put("b", 2)
    await cache.put("c", 3)
    await cache.put("a", 99)  # "a" re-inserted at MRU; "b" is now LRU

    await cache.put("d", 4)  # should evict "b"

    assert await cache.get("a") == 99
    assert await cache.get("b") is None
    assert await cache.get("c") == 3
    assert await cache.get("d") == 4


@pytest.mark.asyncio
async def test_eviction_order_reflects_access_sequence(cache: LRUCache) -> None:
    """Full access sequence determines eviction order correctly end-to-end."""
    await cache.put("a", 1)  # order: [a]
    await cache.put("b", 2)  # order: [a, b]
    await cache.put("c", 3)  # order: [a, b, c] — full
    await cache.get("a")  # order: [b, c, a]
    await cache.get("b")  # order: [c, a, b]

    await cache.put("d", 4)  # evicts "c" (LRU)

    assert await cache.get("c") is None
    assert await cache.get("a") == 1
    assert await cache.get("b") == 2
    assert await cache.get("d") == 4


@pytest.mark.asyncio
async def test_repeated_put_same_key_tracks_latest_value(cache: LRUCache) -> None:
    """Repeated puts to same key keep latest value and count as one slot."""
    for i in range(10):
        await cache.put("same", i)

    assert await cache.get("same") == 9
    assert len(cache) == 1


@pytest.mark.asyncio
async def test_overwrite_does_not_grow_len(cache: LRUCache) -> None:
    await cache.put("a", 1)
    await cache.put("a", 2)
    assert len(cache) == 1


@pytest.mark.asyncio
async def test_concurrent_puts_do_not_exceed_capacity() -> None:
    """Many concurrent writers must not push size above capacity."""
    cache = LRUCache(10)
    await asyncio.gather(*[cache.put(f"k{i}", i) for i in range(100)])
    assert len(cache) <= 10


@pytest.mark.asyncio
async def test_concurrent_puts_all_values_retrievable_if_recent() -> None:
    """The last N keys written are retrievable (where N = capacity)."""
    cache = LRUCache(50)
    await asyncio.gather(*[cache.put(f"k{i}", i) for i in range(50)])
    results = await asyncio.gather(*[cache.get(f"k{i}") for i in range(50)])
    assert all(v == i for i, v in enumerate(results))


@pytest.mark.asyncio
async def test_concurrent_mixed_reads_writes_no_exception() -> None:
    """Mixed concurrent get/put on same keys must not raise."""
    cache = LRUCache(5)
    for i in range(5):
        await cache.put(f"k{i}", i)

    async def worker(i: int) -> None:
        await cache.get(f"k{i % 5}")
        await cache.put(f"k{i % 5}", i)

    await asyncio.gather(*[worker(i) for i in range(50)])
