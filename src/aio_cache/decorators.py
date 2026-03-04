import functools
import hashlib
import pickle
from collections.abc import Callable
from typing import Any

from .protocols import ICacheBackend


def generate_key(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """Build a stable cache key from function args and kwargs.

    - Positional args keep their order (order matters).
    - Keyword args are sorted by name so call order does not change the key.
    - Uses pickle to serialize and SHA-256 for a fixed-length key.
    """
    canonical = (args, tuple(sorted(kwargs.items())))
    raw = pickle.dumps(canonical, protocol=pickle.HIGHEST_PROTOCOL)
    return hashlib.sha256(raw).hexdigest()


def cache(
    func: Callable[..., Any],
    backend: Callable[..., ICacheBackend],
    **kwargs: Any,
):
    cache_backend = backend(**kwargs)

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        key = generate_key(args, kwargs)
        cached_res = await cache_backend.get(key)
        if cached_res is not None:
            return cached_res

        res = await func(*args, **kwargs)
        await cache_backend.put(key, res)
        return res

    return wrapper
