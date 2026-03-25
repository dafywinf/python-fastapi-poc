"""Integration test fixtures — requires PostgreSQL via testcontainers."""

import os
from collections.abc import Generator

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config
from backend.config import settings
from backend.database import get_session
from backend.main import app

_TEST_ADMIN_PASSWORD = "testpass"
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
    database_url = database_url.replace("postgresql+psycopg2://", "postgresql://")

    _engine = create_engine(database_url, pool_pre_ping=True)

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
def client(
    db_session: Session, fake_redis: fakeredis.FakeRedis
) -> Generator[TestClient, None, None]:
    """Return a TestClient with the get_session dependency overridden."""
    del fake_redis

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
    from backend.rate_limiter import limiter

    previous_enabled = limiter.enabled
    limiter.enabled = False
    try:
        response = client.post(
            "/auth/token",
            data={
                "username": settings.admin_username,
                "password": _TEST_ADMIN_PASSWORD,
            },
        )
    finally:
        limiter.enabled = previous_enabled
    assert response.status_code == 200, f"Auth failed: {response.text}"
    return str(response.json()["access_token"])


@pytest.fixture()
def auth_headers(auth_token: str) -> dict[str, str]:
    """Return a Bearer Authorization header for token-auth test cases."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture()
def auth_client(client: TestClient, fake_redis: fakeredis.FakeRedis) -> TestClient:
    """Return a TestClient with a valid access_token cookie pre-set.

    The ``fake_redis`` parameter is required even though it is not referenced
    directly: it ensures the FakeRedis fixture is active for the duration of
    the test so that protected endpoints can check token revocation without
    hitting a real Redis instance.

    Args:
        client: The base test HTTP client.
        fake_redis: Fake Redis instance wired into the app's get_redis singleton.

    Returns:
        The same :class:`TestClient` with the ``access_token`` cookie set.
    """
    from backend.security import create_access_token

    token = create_access_token(subject="test@example.com")
    client.cookies.set("access_token", token)
    return client
