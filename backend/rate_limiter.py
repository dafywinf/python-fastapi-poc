"""slowapi rate limiter singleton for the application."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    enabled=settings.ratelimit_enabled,
)
