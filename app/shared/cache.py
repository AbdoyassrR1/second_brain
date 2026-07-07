#!/usr/bin/python3
"""Redis cache utility for the application."""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RedisCache:
    """Simple Redis cache wrapper with JSON serialization."""

    def __init__(self, client, default_timeout: int = 300):
        self._client = client
        self._default_timeout = default_timeout

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache. Returns None if not found."""
        if self._client is None:
            return None                                                                                                                                                                                                                                                                 
        try:
            value = self._client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception:
            logger.exception("Cache get failed for key: %s", key)
            return None

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Set a value in cache with optional timeout (seconds)."""
        if self._client is None:
            return False
        try:
            serialized = json.dumps(value, default=str)
            return bool(self._client.setex(key, timeout or self._default_timeout, serialized))
        except Exception:
            logger.exception("Cache set failed for key: %s", key)
            return False

    def delete(self, *keys: str) -> int:
        """Delete one or more keys from cache."""
        if self._client is None:
            return 0
        try:
            return self._client.delete(*keys)
        except Exception:
            logger.exception("Cache delete failed for keys: %s", keys)
            return 0

    def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        if self._client is None:
            return False
        try:
            return bool(self._client.exists(key))
        except Exception:
            return False

    def flush(self) -> bool:
        """Flush the current Redis database."""
        if self._client is None:
            return False
        try:
            return bool(self._client.flushdb())
        except Exception:
            logger.exception("Cache flush failed")
            return False
