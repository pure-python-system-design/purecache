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


class LRUCache:
    def __init__(self, capacity: int):
        self._capacity = capacity
        self.container: OrderedDict[str, Any] = OrderedDict()
        self._lock = asyncio.Lock()

    def _is_full(self) -> bool:
        return len(self.container) == self._capacity

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            if key in self.container:
                self.container.move_to_end(key, True)
                return self.container.get(key)
        return None

    async def put(self, key: str, value: Any) -> None:
        async with self._lock:
            if (key not in self.container) and (len(self.container) == self._capacity):
                self.container.popitem(last=False)  # remove first item

            self.container[key] = value
            self.container.move_to_end(key, True)  # move to tail
