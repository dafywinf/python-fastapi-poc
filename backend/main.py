"""FastAPI application entry point."""

import logging
import logging.config

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from pythonjsonlogger.json import JsonFormatter

from backend.auth_routes import router as auth_router
from backend.config import settings
from backend.routes import router

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

app = FastAPI(
    title="Sequence Manager",
    description="A simple FastAPI application for managing Sequence entities.",
    version="0.1.0",
)

Instrumentator().instrument(app).expose(app)  # pyright: ignore[reportUnknownMemberType]

app.include_router(auth_router)
app.include_router(router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return service liveness status.

    Returns:
        A dict with a status key.
    """
    return {"status": "ok"}
