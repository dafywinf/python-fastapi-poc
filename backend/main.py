"""FastAPI application entry point."""

import logging
import logging.config
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import redis as redis_lib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pythonjsonlogger.json import JsonFormatter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import Response

from backend.config import settings
from backend.exceptions import handle_exception
from backend.rate_limiter import limiter
from backend.redis_client import get_redis
from backend.routine_routes import (
    actions_router,
    executions_router,
    routines_router,
)
from backend.user_routes import router as user_router

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.json.JsonFormatter",
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            }
        },
        "root": {"handlers": ["console"], "level": "INFO"},
    }
)

_root_logger = logging.getLogger()
logger = logging.getLogger(__name__)

if settings.loki_url is not None:
    try:
        import logging_loki  # pyright: ignore[reportMissingModuleSource]

        loki_handler = logging_loki.LokiHandler(
            url=f"{settings.loki_url}/loki/api/v1/push",
            tags={"application": "fastapi"},
            version="1",
        )
        loki_handler.setFormatter(JsonFormatter())
        _root_logger.addHandler(loki_handler)
        _root_logger.info("Loki log shipping enabled: %s", settings.loki_url)
    except Exception:
        _root_logger.warning(
            "Failed to initialise Loki handler — logs will not be shipped",
            exc_info=True,
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # type: ignore[type-arg]
    """Start APScheduler on startup if enabled; shut it down on exit.

    Also runs startup checks: Redis health ping and HTTPS URL enforcement.
    """
    # --- Redis health check (fail fast on boot) ---
    try:
        get_redis().ping()  # pyright: ignore[reportUnknownMemberType]
    except redis_lib.RedisError as err:
        logger.critical(
            "Redis health check failed at startup",
            extra={
                "event": "redis.health.failed",
                "redis_url": settings.redis_url,
                "error": str(err),
            },
        )
        raise

    # --- Admin password hash validation ---
    if settings.enable_password_auth:
        if not settings.admin_password_hash.startswith(("$2b$", "$2a$")):
            raise RuntimeError(
                "enable_password_auth=True requires ADMIN_PASSWORD_HASH to be a "
                "valid bcrypt hash (must start with $2b$ or $2a$). "
                'Run: python -c "import bcrypt; print('
                "bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())\""
            )

    # --- HTTPS enforcement ---
    if settings.enforce_https:
        for field in ("backend_url", "frontend_url"):
            url = getattr(settings, field)
            if not url.startswith("https://"):
                raise RuntimeError(
                    f"{field} must use HTTPS when enforce_https=True. Got: {url!r}"
                )

    if settings.scheduler_enabled:
        from backend.database import SessionLocal
        from backend.models import Routine
        from backend.scheduler import register_routine, scheduler

        with SessionLocal() as session:
            routines = list(
                session.execute(
                    select(Routine).where(
                        Routine.is_active == True,  # noqa: E712
                        Routine.schedule_type != "manual",
                    )
                ).scalars()
            )
        for routine in routines:
            register_routine(routine)
        scheduler.start()  # pyright: ignore[reportUnknownMemberType]
        app.state.scheduler = scheduler
    yield
    if settings.scheduler_enabled:
        from backend.scheduler import scheduler

        scheduler.shutdown(wait=False)  # pyright: ignore[reportUnknownMemberType]


app = FastAPI(
    title="Home Automation API",
    description=(
        "A FastAPI application for managing home automation routines and actions."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

if settings.trusted_proxy_ips:
    from uvicorn.middleware.proxy_headers import (  # pyright: ignore[reportMissingImports]
        ProxyHeadersMiddleware,  # pyright: ignore[reportUnknownVariableType]
    )

    app.add_middleware(
        ProxyHeadersMiddleware,  # type: ignore[arg-type]
        trusted_hosts=settings.trusted_proxy_ips,
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter


async def _rate_limit_handler(request: Request, exc: Exception) -> Response:
    """Handle rate limit exceeded errors.

    NOTE: Must be async because ``_rate_limit_exceeded_handler`` from slowapi is
    an async callable. This is an intentional exception to the project's
    sync-first rule.

    Args:
        request: The Starlette Request object.
        exc: The RateLimitExceeded exception.

    Returns:
        The response from slowapi's default 429 handler.
    """
    logger.warning(
        "Rate limit exceeded",
        extra={"event": "api.rate_limit.exceeded", "path": request.url.path},
    )
    return _rate_limit_exceeded_handler(request, exc)  # type: ignore[arg-type]


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

Instrumentator().instrument(app).expose(app)  # pyright: ignore[reportUnknownMemberType]

app.include_router(user_router)
app.include_router(routines_router)
app.include_router(actions_router)
app.include_router(executions_router)

if settings.enable_password_auth:
    from backend.auth_routes import router as auth_router

    app.include_router(auth_router)


@app.get("/health", tags=["health"])
@handle_exception(logger)
def health_check() -> dict[str, str]:
    """Return service liveness status.

    Returns:
        A dict with a status key.
    """
    return {"status": "ok"}
