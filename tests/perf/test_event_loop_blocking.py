"""Performance test: sync def vs async def with blocking I/O.

Demonstrates what happens when you make route handlers `async def` without
changing the underlying database driver to an async one.  The blocking call
(simulated here with time.sleep, equivalent to psycopg2 executing a query)
ends up on the event loop thread and serialises all concurrent requests.

Run with:
    just perf

NOT included in the standard `just test` suite — these tests bind real ports
and take several seconds intentionally.
"""

import time
from collections.abc import Generator

import pytest
from fastapi import FastAPI

from tests.perf.helpers import fire_concurrent, start_server, stop_server

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BLOCKING_SECONDS = 0.5  # simulates a slow DB query
CONCURRENT_REQUESTS = 6
SYNC_PORT = 18001
ASYNC_PORT = 18002

# ---------------------------------------------------------------------------
# Two minimal apps — identical except for def vs async def
# ---------------------------------------------------------------------------

sync_app = FastAPI()


@sync_app.get("/")
def sync_handler() -> dict[str, str]:
    """Correct pattern: def handler — FastAPI runs this in a thread pool worker."""
    time.sleep(BLOCKING_SECONDS)
    return {"mode": "sync"}


async_blocking_app = FastAPI()


@async_blocking_app.get("/")
async def async_blocking_handler() -> dict[str, str]:
    """Anti-pattern: async def handler with a blocking call.

    time.sleep() blocks the event loop thread, preventing any other coroutine
    from running until it returns.  With psycopg2 this would be a DB query.
    """
    time.sleep(BLOCKING_SECONDS)  # blocks the event loop — do not do this
    return {"mode": "async-blocking"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sync_server() -> Generator[str, None, None]:
    server = start_server(sync_app, SYNC_PORT)
    yield f"http://127.0.0.1:{SYNC_PORT}"
    stop_server(server)


@pytest.fixture(scope="module")
def async_blocking_server() -> Generator[str, None, None]:
    server = start_server(async_blocking_app, ASYNC_PORT)
    yield f"http://127.0.0.1:{ASYNC_PORT}"
    stop_server(server)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.perf
def test_sync_handlers_process_requests_concurrently(sync_server: str) -> None:
    """sync def handlers run in the thread pool — requests execute in parallel.

    With 6 concurrent requests each sleeping 0.5s, the wall-clock time should
    be close to one sleep duration, not six.

    Timeline (thread pool, 4+ workers):
        t=0.0  req1─────┐
        t=0.0  req2─────┤ all start
        t=0.0  req3─────┤ at the
        t=0.0  req4─────┤ same
        t=0.0  req5─────┤ time
        t=0.0  req6─────┘
        t=0.5  all complete  ← total elapsed ≈ 0.5s
    """
    elapsed, status_codes = fire_concurrent(sync_server, CONCURRENT_REQUESTS)

    print(f"\n[sync]  {CONCURRENT_REQUESTS} concurrent requests: {elapsed:.2f}s")
    print(f"        expected ≈ {BLOCKING_SECONDS}s  (parallel execution)")

    assert all(s == 200 for s in status_codes), "All requests should succeed"
    # Should complete in roughly one sleep duration, not N sleeps.
    # Allow 3× headroom for CI/slow machines.
    assert elapsed < BLOCKING_SECONDS * 3, (
        f"sync handlers took {elapsed:.2f}s — expected < {BLOCKING_SECONDS * 3:.2f}s. "
        "Thread pool parallelism should make this fast."
    )


@pytest.mark.perf
def test_async_blocking_handlers_serialise_requests(async_blocking_server: str) -> None:
    """async def handlers with blocking calls serialise on the event loop.

    The same 6 requests each sleeping 0.5s now execute one at a time because
    time.sleep() (or psycopg2) blocks the single event loop thread.

    Timeline (single event loop thread):
        t=0.0  req1 starts, blocks event loop
        t=0.5  req1 done, req2 starts, blocks event loop
        t=1.0  req2 done, req3 starts ...
        t=2.5  req6 done  ← total elapsed ≈ 3.0s
    """
    elapsed, status_codes = fire_concurrent(async_blocking_server, CONCURRENT_REQUESTS)

    print(f"\n[async-blocking]  {CONCURRENT_REQUESTS} concurrent requests: {elapsed:.2f}s")  # noqa: E501
    print(f"                  expected ≈ {BLOCKING_SECONDS * CONCURRENT_REQUESTS}s  (serialised)")  # noqa: E501

    assert all(s == 200 for s in status_codes), "All requests should succeed"
    # Should take at least (N-1) sleep durations — proof of serialisation.
    assert elapsed > BLOCKING_SECONDS * (CONCURRENT_REQUESTS - 1), (
        f"async-blocking handlers took {elapsed:.2f}s — expected > "
        f"{BLOCKING_SECONDS * (CONCURRENT_REQUESTS - 1):.2f}s. "
        "Blocking the event loop should force serial execution."
    )


@pytest.mark.perf
def test_async_blocking_is_significantly_slower_than_sync(
    sync_server: str, async_blocking_server: str
) -> None:
    """Head-to-head comparison — the async anti-pattern is measurably slower.

    This is the test to show a colleague who asks "why not just make everything async?".
    """
    sync_elapsed, _ = fire_concurrent(sync_server, CONCURRENT_REQUESTS)
    async_elapsed, _ = fire_concurrent(async_blocking_server, CONCURRENT_REQUESTS)

    ratio = async_elapsed / sync_elapsed

    print("\n[comparison]")
    print(f"  sync def + blocking call : {sync_elapsed:.2f}s")
    print(f"  async def + blocking call: {async_elapsed:.2f}s")
    print(f"  async is {ratio:.1f}× slower")

    assert ratio > (CONCURRENT_REQUESTS / 2), (
        f"Expected async-blocking to be at least {CONCURRENT_REQUESTS / 2:.0f}× slower "
        f"than sync, but ratio was only {ratio:.1f}×"
    )
