import time
import hashlib
from typing import Any, Optional
from threading import Lock


class MemoryCache:
    """
    Thread-safe in-memory cache with TTL expiration.

    Usage:
        from app.utils.cache import cache

        ## Set with default TTL (15 minutes)
        cache.set("my_key", {"data": "value"})

        ## Set with custom TTL (in seconds)
        cache.set("my_key", {"data": "value"}, ttl=3600)  # 1 hour

        ## Get (returns None if expired or not found)
        data = cache.get("my_key")

        ## Generate cache key from multiple values
        key = cache.make_key("youtube", url, region)
    """

    def __init__(self, default_ttl: int = 900, max_size: int = 1000):
        """
        Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 900 = 15 minutes)
            max_size: Maximum number of items to store (default: 1000)
        """
        self._cache: dict[str, tuple[Any, float, int]] = {}  # key -> (value, timestamp, ttl)
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                return None

            value, timestamp, ttl = self._cache[key]

            if time.time() - timestamp >= ttl:
                # Expired, remove it
                del self._cache[key]
                return None

            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        if ttl is None:
            ttl = self._default_ttl

        with self._lock:
            # Cleanup if we're at max size
            if len(self._cache) >= self._max_size:
                self._cleanup_expired()

                # If still at max size, remove oldest entries
                if len(self._cache) >= self._max_size:
                    self._remove_oldest(len(self._cache) - self._max_size + 1)

            self._cache[key] = (value, time.time(), ttl)

    def delete(self, key: str) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cached data."""
        with self._lock:
            self._cache.clear()

    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key) is not None

    def size(self) -> int:
        """Return current number of cached items."""
        with self._lock:
            return len(self._cache)

    def cleanup(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            return self._cleanup_expired()

    def _cleanup_expired(self) -> int:
        """Remove expired entries (internal, no lock)."""
        current_time = time.time()
        expired_keys = [
            k for k, (_, ts, ttl) in self._cache.items()
            if current_time - ts >= ttl
        ]
        for k in expired_keys:
            del self._cache[k]
        return len(expired_keys)

    def _remove_oldest(self, count: int) -> None:
        """Remove oldest entries (internal, no lock)."""
        if count <= 0:
            return

        # Sort by timestamp and remove oldest
        sorted_items = sorted(
            self._cache.items(),
            key=lambda x: x[1][1]  # Sort by timestamp
        )

        for key, _ in sorted_items[:count]:
            del self._cache[key]

    @staticmethod
    def make_key(*args) -> str:
        """
        Generate a cache key from multiple values.

        Args:
            *args: Values to include in the key

        Returns:
            MD5 hash string as cache key
        """
        key_string = ":".join(str(arg) for arg in args)
        return hashlib.md5(key_string.encode()).hexdigest()


# Global cache instance with default settings
cache = MemoryCache(default_ttl=900, max_size=1000)
