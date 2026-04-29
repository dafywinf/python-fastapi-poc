"""Shared pytest fixtures for the test suite.

Fixtures here are available to all tests (unit, integration, perf, e2e).
Database fixtures live in tests/integration/conftest.py.
"""

import pathlib
from collections.abc import Generator

import allure
import fakeredis
import pytest

from backend import redis_client


def _allure_layer_for_path(path: pathlib.Path) -> tuple[str, str]:
    """Return the test-pyramid layer and suite name for a test file path."""
    path_str = path.as_posix()
    if "tests/perf/" in path_str:
        return ("middle", "Performance")
    if "tests/e2e/" in path_str:
        return ("top", "Live Stack E2E")
    if "tests/unit/" in path_str:
        return ("base", "Unit")
    return ("base", "API Integration")


@pytest.fixture(autouse=True)
def _apply_allure_pyramid_labels(  # pyright: ignore[reportUnusedFunction]
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Apply consistent Allure labels so reports reflect the test pyramid."""
    path = request.path
    layer_name, suite_name = _allure_layer_for_path(path)
    allure.dynamic.parent_suite("Backend")  # pyright: ignore[reportUnknownMemberType]
    allure.dynamic.suite(suite_name)  # pyright: ignore[reportUnknownMemberType]
    allure.dynamic.label("layer", layer_name)  # pyright: ignore[reportUnknownMemberType]
    yield


@pytest.fixture(autouse=True)
def _disable_rate_limiting(  # pyright: ignore[reportUnusedFunction]
) -> Generator[None, None, None]:
    """Keep rate limiting off by default; dedicated tests can re-enable it."""
    from backend.rate_limiter import limiter

    previous_enabled = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = previous_enabled


@pytest.fixture(scope="function")  # must be function-scoped — FakeServer is stateful
def fake_redis() -> Generator[fakeredis.FakeRedis, None, None]:
    """Provide an isolated in-process Redis for each test.

    A fresh FakeServer is created per test invocation. Sharing a FakeServer
    across tests would cause state bleed between OAuth state tokens.
    Never promote this fixture to session scope.

    Yields:
        A :class:`fakeredis.FakeRedis` instance wired into the app's
        :func:`backend.redis_client.get_redis` singleton.
    """
    server = fakeredis.FakeServer()
    client: fakeredis.FakeRedis = fakeredis.FakeRedis(
        server=server, decode_responses=True
    )
    redis_client._client = client  # type: ignore[assignment,reportPrivateUsage]
    yield client
    redis_client._client = None  # type: ignore[reportPrivateUsage]
