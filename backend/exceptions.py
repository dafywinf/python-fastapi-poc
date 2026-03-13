"""Exception handling utilities."""

import functools
import logging
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from fastapi import HTTPException

P = ParamSpec("P")
R = TypeVar("R")


def handle_exception(
    logger: logging.Logger,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator factory that logs unhandled exceptions with full tracebacks.

    HTTPExceptions are re-raised as-is so FastAPI can convert them to the
    correct HTTP response.  All other exceptions are logged with
    ``logger.exception`` (which captures the full traceback) and then
    re-raised so the framework's default 500 handler takes over.

    Args:
        logger: The logger to emit the exception record on.

    Returns:
        A decorator that wraps the target function with exception handling.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception:
                logger.exception("Unhandled exception in %s", func.__name__)
                raise

        return wrapper

    return decorator
