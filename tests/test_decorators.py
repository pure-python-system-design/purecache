"""High-quality tests for purecache.decorators.

Follows Arrange-Act-Assert and the testing pyramid.
Uses a fake in-memory backend to test decorator behavior without depending on LRUCache.
"""

import pytest
from purecache.decorators import cache, generate_key

# --- Fake backend for decorator tests ---


class FakeBackend:
    """In-memory backend that records get/put and stores by key."""

    _instances: list["FakeBackend"] = []

    def __init__(self, **kwargs: object) -> None:
        FakeBackend._instances.append(self)
        self._store: dict[str, object] = {}
        self.get_calls: list[str] = []
        self.put_calls: list[tuple[str, object]] = []

    async def get(self, key: str) -> object | None:
        self.get_calls.append(key)
        return self._store.get(key)

    async def put(self, key: str, value: object) -> None:
        self.put_calls.append((key, value))
        self._store[key] = value


@pytest.fixture(autouse=True)
def clear_fake_backend_instances() -> None:
    """Reset so each test gets a clean list of created backends."""
    FakeBackend._instances.clear()
    yield
    FakeBackend._instances.clear()


def _get_backend() -> FakeBackend:
    """Return the backend instance created by the cache decorator."""
    assert FakeBackend._instances, "No FakeBackend instance created (cache not used?)"
    return FakeBackend._instances[-1]


# --- Unit: generate_key ---


def test_generate_key_returns_str() -> None:
    # Act
    key = generate_key((1, 2), {"a": 3})

    # Assert
    assert isinstance(key, str)
    assert len(key) == 64
    assert all(c in "0123456789abcdef" for c in key)


def test_generate_key_same_args_same_key() -> None:
    # Arrange
    args = (1, "x")
    kwargs = {"a": 10, "b": 20}

    # Act
    key1 = generate_key(args, kwargs)
    key2 = generate_key(args, kwargs)

    # Assert
    assert key1 == key2


def test_generate_key_different_args_different_key() -> None:
    # Act
    key1 = generate_key((1, 2), {})
    key2 = generate_key((2, 1), {})

    # Assert
    assert key1 != key2


def test_generate_key_different_kwargs_different_key() -> None:
    # Act
    key1 = generate_key((), {"a": 1})
    key2 = generate_key((), {"a": 2})

    # Assert
    assert key1 != key2


def test_generate_key_kwargs_order_independent() -> None:
    """Same kwargs in different order produce the same key."""
    # Act
    key1 = generate_key((), {"a": 1, "b": 2})
    key2 = generate_key((), {"b": 2, "a": 1})

    # Assert
    assert key1 == key2


def test_generate_key_positional_order_matters() -> None:
    # Act
    key1 = generate_key((1, 2), {})
    key2 = generate_key((2, 1), {})

    # Assert
    assert key1 != key2


def test_generate_key_empty_args_empty_kwargs() -> None:
    # Act
    key = generate_key((), {})

    # Assert
    assert isinstance(key, str)
    assert len(key) == 64


def test_generate_key_empty_stable() -> None:
    """Empty args and kwargs produce stable key across calls."""
    # Act
    key1 = generate_key((), {})
    key2 = generate_key((), {})

    # Assert
    assert key1 == key2


def test_generate_key_handles_none_value() -> None:
    # Act
    key = generate_key((None,), {"x": None})

    # Assert
    assert isinstance(key, str)
    assert len(key) == 64


def test_generate_key_handles_list_and_dict() -> None:
    # Act
    key = generate_key(([1, 2],), {"k": {"nested": True}})

    # Assert
    assert isinstance(key, str)
    assert len(key) == 64


def test_generate_key_same_nested_structure_same_key() -> None:
    # Act
    key1 = generate_key(({"a": [1, 2]},), {})
    key2 = generate_key(({"a": [1, 2]},), {})

    # Assert
    assert key1 == key2


# --- Unit: cache decorator (with FakeBackend) ---


async def test_cache_miss_returns_func_result() -> None:
    """On cache miss, wrapper returns the result of the wrapped function."""

    # Arrange
    async def fn(x: int) -> int:
        return x + 1

    wrapped = cache(fn, FakeBackend)

    # Act
    result = await wrapped(10)

    # Assert
    assert result == 11


async def test_cache_miss_calls_backend_get_then_put() -> None:
    """On cache miss, backend get is called, then put with key and result."""

    # Arrange
    async def fn(x: int) -> int:
        return x + 1

    wrapped = cache(fn, FakeBackend)

    # Act
    await wrapped(5)

    # Assert
    backend = _get_backend()
    assert len(backend.get_calls) == 1
    assert len(backend.put_calls) == 1
    assert backend.put_calls[0][1] == 6


async def test_cache_hit_returns_cached_value_without_calling_func() -> None:
    """On cache hit, returns cached value and does not call the function again."""
    # Arrange
    call_count = 0

    async def fn(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    wrapped = cache(fn, FakeBackend)
    await wrapped(7)

    # Act
    result = await wrapped(7)

    # Assert
    assert result == 14
    assert call_count == 1


async def test_cache_hit_calls_backend_get_only() -> None:
    """On cache hit, backend get is called once; put is not called again."""

    # Arrange
    async def fn(x: int) -> int:
        return x

    wrapped = cache(fn, FakeBackend)
    await wrapped(1)
    await wrapped(1)

    # Assert
    backend = _get_backend()
    assert len(backend.get_calls) == 2
    assert len(backend.put_calls) == 1


async def test_cache_different_args_different_keys() -> None:
    """Different (args, kwargs) produce different keys and separate cache entries."""

    # Arrange
    async def fn(x: int) -> int:
        return x

    wrapped = cache(fn, FakeBackend)
    await wrapped(1)
    await wrapped(2)

    # Assert
    backend = _get_backend()
    assert len(backend.put_calls) == 2
    assert backend.put_calls[0][0] != backend.put_calls[1][0]


async def test_cache_same_args_same_key() -> None:
    """Same (args, kwargs) produce same key so second call is a hit."""

    # Arrange
    async def fn(x: int) -> int:
        return x

    wrapped = cache(fn, FakeBackend)
    key_first = generate_key((1,), {})
    await wrapped(1)

    backend = _get_backend()
    key_used = backend.put_calls[0][0]

    # Assert
    assert key_used == key_first


async def test_cache_preserves_function_name() -> None:
    """Wrapped function preserves __name__ of the original (via functools.wraps)."""

    # Arrange
    async def my_async_func() -> str:
        return "ok"

    wrapped = cache(my_async_func, FakeBackend)

    # Assert
    assert wrapped.__name__ == "my_async_func"


async def test_cache_with_kwargs_uses_key_from_both_args_and_kwargs() -> None:
    """Cache key is derived from both positional and keyword arguments."""

    # Arrange
    async def fn(a: int, b: int) -> int:
        return a + b

    wrapped = cache(fn, FakeBackend)
    await wrapped(1, 2)
    await wrapped(1, b=2)

    # Assert: (1, 2) vs (1,), {b:2} are different
    backend = _get_backend()
    keys = [put[0] for put in backend.put_calls]
    assert len(keys) == 2
    assert keys[0] != keys[1]


# --- Integration: cache with falsy values ---


async def test_cache_stores_falsy_value_then_returns_on_hit() -> None:
    """Cached value 0 (or other falsy) is returned on second call without calling func.

    Decorator should use 'is not None' (or equivalent) so falsy values are cached.
    """
    # Arrange
    call_count = 0

    async def fn() -> int:
        nonlocal call_count
        call_count += 1
        return 0

    wrapped = cache(fn, FakeBackend)
    first = await wrapped()

    # Act
    second = await wrapped()

    # Assert: both return 0; func must be called only once (cache hit on second call)
    assert first == 0
    assert second == 0
    assert call_count == 1
