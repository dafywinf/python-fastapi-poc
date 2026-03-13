"""FastAPI application entry point."""

import logging
import logging.config

from fastapi import FastAPI

from backend.routes import router

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "root": {"handlers": ["console"], "level": "INFO"},
    }
)

app = FastAPI(
    title="Sequence Manager",
    description="A simple FastAPI application for managing Sequence entities.",
    version="0.1.0",
)

app.include_router(router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return service liveness status.

    Returns:
        A dict with a status key.
    """
    return {"status": "ok"}
