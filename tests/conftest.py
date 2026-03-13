"""Shared pytest fixtures for the test suite.

Uses an in-memory SQLite database so tests are fully self-contained and
require no running PostgreSQL instance.  The `get_session` FastAPI
dependency is overridden on each test via the `client` fixture.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_session
from backend.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """Create a single in-memory SQLite engine for the entire test session."""
    _engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=_engine)
    yield _engine
    Base.metadata.drop_all(bind=_engine)
    _engine.dispose()


@pytest.fixture()
def db_session(engine):
    """Provide a transactional session that is rolled back after each test.

    This keeps tests isolated without recreating the schema on every run.
    """
    connection = engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = TestingSessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """Return a TestClient that uses the transactional test session."""

    def override_get_session():
        try:
            yield db_session
        finally:
            pass  # rollback handled by db_session fixture

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
