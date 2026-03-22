"""FastAPI application entry point."""

import logging
import logging.config
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from pythonjsonlogger.json import JsonFormatter
from sqlalchemy import select

from backend.config import settings
from backend.exceptions import handle_exception
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
    """Start APScheduler on startup if enabled; shut it down on exit."""
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
