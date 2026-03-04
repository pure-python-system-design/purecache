# aio-cache

Async-native in-memory cache with pluggable eviction strategies — pure Python 3.12+, zero dependencies.

[View Source on GitHub](https://github.com/pure-python-system-design/aio-cache){ .md-button }

---

## Quick Start

```python
from aio_cache import Cache, LRUTTLBackend

cache = Cache(backend=LRUTTLBackend(capacity=1000, ttl=300))

await cache.set("user:42", {"name": "Alice"})
value = await cache.get("user:42")   # {"name": "Alice"}
value = await cache.get("missing")   # None
```

## Backends

| Backend                | Eviction            | Time | Best For        |
| ---------------------- | ------------------- | ---- | --------------- |
| [`LRUBackend`](lru.md) | Least Recently Used | O(1) | General purpose |


## Why Build This?

Most developers have used a cache. Few have built one.

The gap matters. When you implement LRU from scratch, you understand *why* `OrderedDict.move_to_end()` exists. When you implement TTL, you confront the choice between lazy expiry (check on access) and eager expiry (background sweep) — and realise both are valid and serve different use cases.

This project exists to close that gap, using nothing but Python's standard library and `asyncio`.
