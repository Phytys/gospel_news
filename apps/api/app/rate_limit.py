"""Simple in-memory sliding-window rate limiter (no extra dependencies)."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Tuple


class SlidingWindowLimiter:
    """Per-key sliding window counter.

    Keeps at most `max_requests` entries per key within `window_seconds`.
    Thread-safe via a single lock (fine for moderate traffic).
    """

    def __init__(self, max_requests: int = 6, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str) -> Tuple[bool, int]:
        """Return (allowed, seconds_until_next_slot).

        `allowed` is True if the request is within limits.
        """
        now = time.monotonic()
        with self._lock:
            timestamps = self._hits[key]
            cutoff = now - self.window
            timestamps[:] = [t for t in timestamps if t > cutoff]

            if len(timestamps) >= self.max_requests:
                wait = int(timestamps[0] - cutoff) + 1
                return False, max(wait, 1)

            timestamps.append(now)
            return True, 0


ask_limiter = SlidingWindowLimiter(max_requests=6, window_seconds=60)
