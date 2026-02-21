"""Simple in-memory rate limiting middleware."""

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class RateLimiter:
    """In-memory rate limiter using sliding window with timestamps.

    No Redis needed — sufficient for single-instance deployment.
    """

    def __init__(self) -> None:
        # Key: (restaurant_id, bucket) → list of timestamps
        self._requests: dict[tuple[int, str], list[float]] = defaultdict(list)

    def _cleanup(self, key: tuple[int, str], window_seconds: int) -> None:
        """Remove expired timestamps."""
        now = time.time()
        cutoff = now - window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def check(
        self,
        restaurant_id: int,
        bucket: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        """Check rate limit. Raises 429 if exceeded."""
        key = (restaurant_id, bucket)
        self._cleanup(key, window_seconds)

        if len(self._requests[key]) >= max_requests:
            retry_after = int(window_seconds - (time.time() - self._requests[key][0]))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Trop de requêtes. Réessaie dans {max(retry_after, 1)} secondes.",
                headers={"Retry-After": str(max(retry_after, 1))},
            )

        self._requests[key].append(time.time())


# Singleton instance
rate_limiter = RateLimiter()


# --- Rate limit presets ---
RATE_LIMITS = {
    "ai": {"max_requests": 10, "window_seconds": 60},       # 10/min for AI endpoints
    "upload": {"max_requests": 30, "window_seconds": 3600},  # 30/hour for uploads
}


def check_ai_rate_limit(restaurant_id: int) -> None:
    """Check rate limit for AI endpoints (onboarding extract + suggest)."""
    rate_limiter.check(restaurant_id, "ai", **RATE_LIMITS["ai"])


def check_upload_rate_limit(restaurant_id: int) -> None:
    """Check rate limit for upload endpoints."""
    rate_limiter.check(restaurant_id, "upload", **RATE_LIMITS["upload"])
