"""LRU Cache — O(1) implementation.

Based on the stack algorithm framework from:
  "Evaluation Techniques for Storage Hierarchies"
  R. L. Mattson, J. Gecsei, D. R. Slutz, I. L. Traiger
  IBM Systems Journal, 9(2):78-117, 1970
  https://dl.acm.org/doi/10.1147/sj.92.0078
"""

import asyncio
from collections import OrderedDict
from typing import Any

from .utils import _MISSING


class LRUCache:
    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {capacity}")
        self._capacity = capacity
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = asyncio.Lock()

    def __len__(self) -> int:
        # No lock — eventually consistent, safe under asyncio's cooperative scheduling
        return len(self._cache)

    async def get(self, key: str) -> Any:
        # Fast path: unlocked read, miss returns immediately without lock overhead
        value = self._cache.get(key, _MISSING)
        if value is _MISSING:
            return None

        async with self._lock:
            try:
                self._cache.move_to_end(key)  # promote to MRU position
            except KeyError:
                # Evicted between unlocked read and lock acquire,
                # it's a valid race, treat as miss
                return None

        return value

    async def put(self, key: str, value: Any) -> None:
        async with self._lock:
            self._cache.pop(key, None)  # remove existing entry if present
            if len(self._cache) >= self._capacity:
                self._cache.popitem(last=False)  # last=False evicts LRU (head)
            self._cache[key] = value  # insert at MRU position (tail)
