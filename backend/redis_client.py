"""Redis client singleton for the application."""

import redis as redis_lib

from backend.config import settings

_client: redis_lib.Redis | None = None  # type: ignore[type-arg]


def get_redis() -> redis_lib.Redis:  # type: ignore[type-arg]
    """Return the shared Redis client, initialising it on first call.

    The initialisation is not protected by a lock. Two threads could
    simultaneously observe ``_client is None`` and each create a client —
    this is a benign race: both produce equivalent connection-pool-backed
    clients and one simply overwrites the other.

    Returns:
        A configured :class:`redis.Redis` instance with decode_responses=True
        and a 1-second socket timeout. ``retry_on_timeout`` is intentionally
        omitted — without a capped retry limit it blocks threads indefinitely
        during a Redis outage, exhausting the FastAPI thread pool.

    Raises:
        redis.exceptions.ConnectionError: If Redis is unreachable. Callers
            should let this propagate — OAuth flows fail closed (503) rather
            than falling back to an insecure in-memory store.
    """
    global _client
    if _client is None:
        _client = redis_lib.from_url(  # type: ignore[assignment]
            settings.redis_url,
            decode_responses=True,
            socket_timeout=1,
        )
    return _client
