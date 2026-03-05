# 🗄️ purecache

[![CI](https://img.shields.io/github/actions/workflow/status/pure-python-system-design/purecache/ci.yml?branch=main&label=CI)](https://github.com/pure-python-system-design/purecache/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/purecache?color=blue)](https://pypi.org/project/purecache/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-mkdocs%20material-9cf)](https://pure-python-system-design.github.io/purecache/)

Async-native in-memory cache with pluggable eviction backends — pure Python 3.12+, zero dependencies.

Just `asyncio`, `collections.OrderedDict`, and the irrational urge to understand what happens inside the black box.

Part of the [pure-python-system-design](https://github.com/pure-python-system-design) project.

---

## 📦 Installation

```bash
pip install purecache
```

Or with uv:

```bash
uv add purecache
```

Python 3.12+ required.

---

## ⚡ Quick Start

### Direct backend usage

```python
from purecache.backends.lru import LRUCache

cache = LRUCache(capacity=128)

await cache.put("user:42", {"name": "Alice"})
value = await cache.get("user:42")  # {"name": "Alice"}
value = await cache.get("missing")  # None
```

### Decorator

```python
from purecache.decorators import cache
from purecache.backends.lru import LRUCache

@cache(backend=LRUCache, capacity=128)
async def get_user(user_id: str) -> dict:
    return await fetch_from_db(user_id)

# First call — executes get_user, caches result
user = await get_user("42")

# Second call — returns cached result, skips get_user
user = await get_user("42")
```

Cache keys are derived automatically from the function's arguments using `pickle` + SHA-256 — positional args keep their order, keyword args are sorted by name.

---

## 🧠 Backends

| Backend       | Eviction Policy       | Time | Memory | Best For               |
| ------------- | --------------------- | ---- | ------ | ---------------------- |
| `LRUCache`    | Least Recently Used   | O(1) | O(n)   | General purpose        |
| `LFUCache`    | Least Frequently Used | O(1) | O(n)   | Skewed access patterns |
| `TTLCache`    | Time-based expiry     | O(1) | O(n)   | Sessions, tokens       |
| `LRUTTLCache` | LRU + TTL combined    | O(1) | O(n)   | Production default     |

All backends implement the `ICacheBackend` protocol — swap them without touching your application code.

---

## 🔌 Framework Examples

The decorator integrates naturally with any async framework:

```python
# FastAPI
from fastapi import FastAPI
from purecache.decorators import cache
from purecache.backends.lru import LRUCache

app = FastAPI()

@app.get("/user/{user_id}")
@cache(backend=LRUCache, capacity=512)
async def get_user(user_id: str):
    return await fetch_user_from_db(user_id)
```

TODO: Add more examples for aiohttp, Django, Flask, Litestar, and Sanic in [`examples/`](examples/).

---

## 📐 Architecture

```
cache() decorator
  └── ICacheBackend (protocol)
        ├── LRUCache    — OrderedDict + move_to_end
        ├── LFUCache    — key_map + freq_map + min_freq pointer
        ├── TTLCache    — dict + expiry timestamps
        └── LRUTTLCache — LRU + TTL combined
```

The `cache()` decorator handles key generation and cache lookup. The backend handles storage and eviction. Swap the backend, keep everything else.

---

## ⚠️ Known Limitations

- **Caching `None`**: The decorator uses `if cached_res is not None` as the cache-hit check. Functions that legitimately return `None` will always miss — the value won't be cached. Use a sentinel-aware backend or wrap the return value if needed.

---

## 📋 Requirements

- Python 3.12+
- Courage

---

## 🧪 Development

```bash
uv sync
pre-commit install

uv run pytest
uv run ruff check .
uv run mypy src/
uv run mkdocs serve
```

---

## 📖 Documentation

Full docs at **https://pure-python-system-design.github.io/purecache/**

---

More designs to come, if the pizza supply holds.
