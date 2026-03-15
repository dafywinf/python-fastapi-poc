"""Shared pytest fixtures for the test suite.

Uses a real PostgreSQL container (via testcontainers) so tests run against
the same database engine as production.  Alembic migrations are applied
once per session, and each test runs inside a transaction that is rolled
back on teardown to keep tests fully isolated.
"""

import os
import pathlib
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config
from backend.database import get_session
from backend.main import app

# Test password that matches the ADMIN_PASSWORD_HASH set in the root conftest.py.
_TEST_ADMIN_PASSWORD = "testpass"

# Docker Desktop on macOS uses a non-standard socket — set DOCKER_HOST so
# testcontainers can find the daemon without manual environment setup.
_docker_sock = pathlib.Path.home() / ".docker/run/docker.sock"
if _docker_sock.exists() and not os.environ.get("DOCKER_HOST"):
    os.environ["DOCKER_HOST"] = f"unix://{_docker_sock}"

POSTGRES_IMAGE = "postgres:16-alpine"


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """Start a PostgreSQL container for the entire test session."""
    with PostgresContainer(POSTGRES_IMAGE) as container:
        yield container


@pytest.fixture(scope="session")
def engine(postgres_container: PostgresContainer) -> Generator[Engine, None, None]:
    """Create a SQLAlchemy engine and apply Alembic migrations once."""
    database_url: str = postgres_container.get_connection_url()  # pyright: ignore[reportUnknownMemberType]

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
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """Wrap each test in a transaction that is rolled back after the test.

    Uses join_transaction_mode="create_savepoint" so that service-layer
    session.commit() calls only release a SAVEPOINT rather than committing
    the outer transaction, keeping each test fully isolated.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Return a TestClient with the get_session dependency overridden."""

    def override_get_session() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass  # rollback handled by db_session fixture

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_token(client: TestClient) -> str:
    """Obtain a JWT access token by authenticating with the test admin credentials.

    Args:
        client: The test HTTP client (provides the /auth/token endpoint).

    Returns:
        A signed JWT access token string.
    """
    response = client.post(
        "/auth/token",
        data={
            "username": os.environ.get("ADMIN_USERNAME", "admin"),
            "password": _TEST_ADMIN_PASSWORD,
        },
    )
    assert response.status_code == 200, f"Auth failed: {response.text}"
    return str(response.json()["access_token"])


@pytest.fixture()
def auth_headers(auth_token: str) -> dict[str, str]:
    """Return Authorization headers containing a valid Bearer token.

    Args:
        auth_token: A signed JWT access token.

    Returns:
        A dict suitable for use as request headers.
    """
    return {"Authorization": f"Bearer {auth_token}"}
