"""Shared pytest fixtures for the test suite.

Uses a real PostgreSQL container (via testcontainers) so tests run against
the same database engine as production.  Alembic migrations are applied
once per session, and each test runs inside a transaction that is rolled
back on teardown to keep tests fully isolated.
"""

import os
import pathlib

import pytest

# Docker Desktop on macOS uses a non-standard socket — set DOCKER_HOST so
# testcontainers can find the daemon without manual environment setup.
_docker_sock = pathlib.Path.home() / ".docker/run/docker.sock"
if _docker_sock.exists() and not os.environ.get("DOCKER_HOST"):
    os.environ["DOCKER_HOST"] = f"unix://{_docker_sock}"
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from testcontainers.postgres import PostgresContainer

from backend.database import get_session
from backend.main import app

POSTGRES_IMAGE = "postgres:16-alpine"


@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container for the entire test session."""
    with PostgresContainer(POSTGRES_IMAGE) as container:
        yield container


@pytest.fixture(scope="session")
def engine(postgres_container):
    """Create a SQLAlchemy engine and apply Alembic migrations once."""
    database_url = postgres_container.get_connection_url()

    # testcontainers returns a psycopg2+asyncpg URL — normalise to psycopg2
    database_url = database_url.replace("postgresql+psycopg2://", "postgresql://")

    _engine = create_engine(database_url, pool_pre_ping=True)

    # env.py reads DATABASE_URL from os.environ, so point it at the container
    # for the duration of the migration run.
    _original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    if _original_db_url is not None:
        os.environ["DATABASE_URL"] = _original_db_url
    else:
        del os.environ["DATABASE_URL"]

    yield _engine
    _engine.dispose()


@pytest.fixture()
def db_session(engine):
    """Wrap each test in a transaction that is rolled back after the test.

    Uses join_transaction_mode="create_savepoint" so that service-layer
    session.commit() calls only release a SAVEPOINT rather than committing
    the outer transaction, keeping each test fully isolated.
    """
    from sqlalchemy.orm import Session

    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """Return a TestClient with the get_session dependency overridden."""

    def override_get_session():
        try:
            yield db_session
        finally:
            pass  # rollback handled by db_session fixture

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
