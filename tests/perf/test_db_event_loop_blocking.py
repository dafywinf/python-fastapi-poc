"""Performance test: sync def vs async def with a real psycopg2 database call.

Demonstrates the event-loop blocking anti-pattern using an actual PostgreSQL
query (`SELECT pg_sleep(0.5)`) rather than `time.sleep`, making the proof
undeniable — a real driver call stalls the event loop just as badly.

Run with:
    just perf

NOT included in the standard `just test` suite — these tests spin up a Docker
container, bind real ports, and take several seconds intentionally.
"""

import os
import pathlib
from collections.abc import Generator

import allure
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer

from tests.perf.helpers import fire_concurrent, start_server, stop_server

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PG_SLEEP = 0.5
CONCURRENT_REQUESTS = 6
SYNC_DB_PORT = 18003
ASYNC_DB_PORT = 18004

# ---------------------------------------------------------------------------
# Two minimal apps — identical route logic, def vs async def
# ---------------------------------------------------------------------------

sync_db_app = FastAPI()
async_blocking_db_app = FastAPI()


def get_perf_session() -> Session:
    """Placeholder dependency — overridden by fixtures before servers start."""
    raise NotImplementedError("dependency not overridden")


@sync_db_app.get("/")
def sync_db_handler(session: Session = Depends(get_perf_session)) -> dict[str, str]:
    """Correct pattern: def handler — FastAPI runs this in a thread pool worker."""
    session.execute(text("SELECT pg_sleep(0.5)"))
    return {"mode": "sync-db"}


@async_blocking_db_app.get("/")
async def async_blocking_db_handler(  # noqa: E501
    session: Session = Depends(get_perf_session),
) -> dict[str, str]:
    """Anti-pattern: async def handler with a blocking psycopg2 call.

    session.execute() blocks the event loop thread, preventing any other
    coroutine from running until the query returns.
    """
    session.execute(
        text("SELECT pg_sleep(0.5)")
    )  # blocks the event loop — do not do this  # noqa: E501
    return {"mode": "async-blocking-db"}


# ---------------------------------------------------------------------------
# Container and engine fixtures (module scope)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pg_container():
    """Spin up a dedicated PostgreSQL container for the perf suite."""
    _docker_sock = pathlib.Path.home() / ".docker/run/docker.sock"
    if _docker_sock.exists() and not os.environ.get("DOCKER_HOST"):
        os.environ["DOCKER_HOST"] = f"unix://{_docker_sock}"

    with PostgresContainer("postgres:16-alpine") as container:
        yield container


@pytest.fixture(scope="module")
def db_engine(pg_container: PostgresContainer):
    """SQLAlchemy engine connected to the perf container.

    pool_size=10 so all 6 concurrent requests get their own connection
    (default pool_size=5 would queue the 6th request, muddying results).
    """
    url = pg_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql://"
    )
    _engine = create_engine(url, pool_size=10, max_overflow=10)
    yield _engine
    _engine.dispose()


# ---------------------------------------------------------------------------
# Server fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sync_db_server(db_engine: Engine) -> Generator[str, None, None]:
    """Start the sync-def app with a real DB session dependency."""
    _SessionLocal = sessionmaker(bind=db_engine)

    def _override() -> Generator[Session, None, None]:
        session = _SessionLocal()
        try:
            yield session
        finally:
            session.close()

    sync_db_app.dependency_overrides[get_perf_session] = _override
    server = start_server(sync_db_app, SYNC_DB_PORT)
    yield f"http://127.0.0.1:{SYNC_DB_PORT}"
    stop_server(server)
    sync_db_app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def async_blocking_db_server(db_engine: Engine) -> Generator[str, None, None]:
    """Start the async-def app with a real DB session dependency."""
    _SessionLocal = sessionmaker(bind=db_engine)

    def _override() -> Generator[Session, None, None]:
        session = _SessionLocal()
        try:
            yield session
        finally:
            session.close()

    async_blocking_db_app.dependency_overrides[get_perf_session] = _override
    server = start_server(async_blocking_db_app, ASYNC_DB_PORT)
    yield f"http://127.0.0.1:{ASYNC_DB_PORT}"
    stop_server(server)
    async_blocking_db_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@allure.feature("Performance")  # pyright: ignore[reportUnknownMemberType]
@allure.story("DB-backed event loop blocking")  # pyright: ignore[reportUnknownMemberType]
@pytest.mark.perf
def test_sync_db_handlers_process_requests_concurrently(sync_db_server: str) -> None:
    """sync def handlers run in the thread pool — DB requests execute in parallel.

    With 6 concurrent requests each calling pg_sleep(0.5), wall-clock time
    should be close to one sleep duration because threads run in parallel.

    Timeline (thread pool, 6 workers):
        t=0.0  req1─────┐
        t=0.0  req2─────┤ all start
        t=0.0  req3─────┤ at the
        t=0.0  req4─────┤ same
        t=0.0  req5─────┤ time
        t=0.0  req6─────┘
        t=0.5  all complete  ← total elapsed ≈ 0.5s
    """
    with allure.step(
        f"Fire {CONCURRENT_REQUESTS} concurrent requests at sync-db server"
    ):  # noqa: E501
        elapsed, status_codes = fire_concurrent(sync_db_server, CONCURRENT_REQUESTS)

    print(f"\n[sync-db]  {CONCURRENT_REQUESTS} concurrent requests: {elapsed:.2f}s")
    print(f"           expected ≈ {PG_SLEEP}s  (parallel — thread pool)")

    assert all(s == 200 for s in status_codes), "All requests should succeed"
    assert elapsed < PG_SLEEP * 3, (
        f"sync-db handlers took {elapsed:.2f}s — expected < {PG_SLEEP * 3:.2f}s. "
        "Thread pool parallelism should make this fast."
    )


@allure.feature("Performance")  # pyright: ignore[reportUnknownMemberType]
@allure.story("DB-backed event loop blocking")  # pyright: ignore[reportUnknownMemberType]
@pytest.mark.perf
def test_async_blocking_db_handlers_serialise_requests(  # noqa: E501
    async_blocking_db_server: str,
) -> None:
    """async def handlers with psycopg2 calls serialise on the event loop.

    The same 6 requests each running pg_sleep(0.5) now execute one at a time
    because the blocking driver call holds the single event loop thread.

    Timeline (single event loop thread):
        t=0.0  req1 starts, blocks event loop
        t=0.5  req1 done, req2 starts, blocks event loop
        t=1.0  req2 done, req3 starts ...
        t=2.5  req6 done  ← total elapsed ≈ 3.0s
    """
    with allure.step(  # noqa: E501
        f"Fire {CONCURRENT_REQUESTS} concurrent requests at async-blocking-db server"
    ):
        elapsed, status_codes = fire_concurrent(
            async_blocking_db_server, CONCURRENT_REQUESTS
        )  # noqa: E501

    print(
        f"\n[async-blocking-db]  {CONCURRENT_REQUESTS} concurrent requests: {elapsed:.2f}s"  # noqa: E501
    )
    print(
        f"                     expected ≈ {PG_SLEEP * CONCURRENT_REQUESTS}s  (serialised)"  # noqa: E501
    )

    assert all(s == 200 for s in status_codes), "All requests should succeed"
    assert elapsed > PG_SLEEP * (CONCURRENT_REQUESTS - 1), (
        f"async-blocking-db handlers took {elapsed:.2f}s — expected > "
        f"{PG_SLEEP * (CONCURRENT_REQUESTS - 1):.2f}s. "
        "Blocking the event loop should force serial execution."
    )


@allure.feature("Performance")  # pyright: ignore[reportUnknownMemberType]
@allure.story("DB-backed event loop blocking")  # pyright: ignore[reportUnknownMemberType]
@pytest.mark.perf
def test_async_blocking_db_is_significantly_slower_than_sync(
    sync_db_server: str, async_blocking_db_server: str
) -> None:
    """Head-to-head: real DB calls prove async anti-pattern is measurably slower.

    This is the test to show a colleague who argues that time.sleep is artificial.
    With a real psycopg2 pg_sleep call the result is the same: blocking the event
    loop serialises what should be parallel work.
    """
    with allure.step("Measure sync-db elapsed time"):
        sync_elapsed, _ = fire_concurrent(sync_db_server, CONCURRENT_REQUESTS)

    with allure.step("Measure async-blocking-db elapsed time"):
        async_elapsed, _ = fire_concurrent(
            async_blocking_db_server, CONCURRENT_REQUESTS
        )  # noqa: E501

    ratio = async_elapsed / sync_elapsed

    print("\n[comparison]")
    print(f"  sync def + pg_sleep  : {sync_elapsed:.2f}s")
    print(f"  async def + pg_sleep : {async_elapsed:.2f}s")
    print(f"  async-db is {ratio:.1f}× slower")

    assert ratio > (CONCURRENT_REQUESTS / 2), (
        f"Expected async-blocking-db to be at least {CONCURRENT_REQUESTS / 2:.0f}× slower "  # noqa: E501
        f"than sync-db, but ratio was only {ratio:.1f}×"
    )
