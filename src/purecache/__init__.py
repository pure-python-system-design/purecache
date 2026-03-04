"""purecache"""

__version__ = "0.1.0"

from .backends import LRUCache
from .decorators import cache

__all__ = ["cache", "LRUCache"]
