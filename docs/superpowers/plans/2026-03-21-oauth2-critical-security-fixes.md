# OAuth2 Critical Security Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two critical OAuth2 security issues: JWT token delivered via URL query param (leaks to logs/headers), and an in-memory CSRF state store that breaks under multi-worker deployments.

**Architecture:** Replace `?token=` with `#token=` in the post-OAuth redirect so the token never reaches servers. Replace `dict[str, float]` state store with Redis using `SETEX`/`GETDEL` for atomic, TTL-managed, multi-worker-safe state. Frontend reads from `window.location.hash` and immediately clears the fragment from history.

**Tech Stack:** FastAPI (sync), redis-py 5, fakeredis 2.20 (tests), Vue 3 + TypeScript, pytest + allure, poetry, just

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `docker-compose.yml` | Modify | Add `redis:7-alpine` service |
| `justfile` | Modify | Add `redis-up` recipe; wire into `platform-up` |
| `pyproject.toml` | Modify | Add `redis ^5.0` (prod), `fakeredis ^2.20` (dev) |
| `backend/config.py` | Modify | Add `redis_url: str` setting |
| `backend/redis_client.py` | Create | Lazy Redis singleton; `get_redis()` |
| `backend/google_oauth.py` | Modify | Remove `state_store` dict; use Redis `SETEX`/`GETDEL` |
| `backend/user_routes.py` | Modify | `?token=` → `#token=`; update docstring |
| `tests/conftest.py` | Modify | Add `fake_redis` fixture (function-scoped) |
| `tests/test_google_oauth.py` | Modify | Remove `state_store` imports; rewrite state tests |
| `frontend/src/views/AuthCallbackView.vue` | Modify | Read from `window.location.hash`; `replaceState`; remove `useRoute` |
| `frontend/src/__tests__/AuthCallbackView.test.ts` | Modify | Update tests to use `window.location.hash` |

---

## Task 1: Add Redis to docker-compose and justfile

**Files:**
- Modify: `docker-compose.yml`
- Modify: `justfile`

No tests for infrastructure. Verify manually.

- [ ] **Step 1: Add Redis service to docker-compose.yml**

Add after the `db` service (before `prometheus`):

```yaml
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
```

- [ ] **Step 2: Add `redis-up` recipe and update `platform-up` in justfile**

Add a new recipe after `db-up`:

```makefile
# Start the Redis container
redis-up:
    docker compose up -d redis
```

Change `platform-up`:

```makefile
# Start all platform services (PostgreSQL + Redis + full monitoring stack)
platform-up: db-up redis-up obs-up
```

- [ ] **Step 3: Start Redis and verify it's healthy**

```bash
just redis-up
docker compose ps redis
# Expected: redis is Up and healthy (may take ~15s for healthcheck to pass)
docker compose exec redis redis-cli ping
# Expected: PONG
```

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml justfile
git commit -m "chore(infra): add Redis service and redis-up recipe"
```

---

## Task 2: Add redis dependency and config

**Files:**
- Modify: `pyproject.toml`
- Modify: `backend/config.py`

- [ ] **Step 1: Add redis and fakeredis via Poetry**

```bash
poetry add "redis^5.0"
poetry add --group dev "fakeredis^2.20"
```

Verify both appear in `pyproject.toml`:
- `[tool.poetry.dependencies]` should contain `redis = "^5.0"`
- `[tool.poetry.group.dev.dependencies]` should contain `fakeredis = "^2.20"`

- [ ] **Step 2: Add `redis_url` to backend/config.py**

Open `backend/config.py`. In the `Settings` class, add after `enable_password_auth`:

```python
redis_url: str = "redis://localhost:6379/0"
```

Also add a docstring entry for the new attribute. The full updated docstring `Attributes` block should include:

```
redis_url: Connection URL for the Redis instance used for OAuth2 state tokens.
    Defaults to localhost:6379 — matches the docker-compose redis service.
    For CI, fakeredis bypasses this URL entirely; no env var is needed.
```

- [ ] **Step 3: Verify config loads**

```bash
.venv/bin/python -c "from backend.config import settings; print(settings.redis_url)"
# Expected: redis://localhost:6379/0
```

- [ ] **Step 4: Run existing tests to confirm nothing is broken**

```bash
just backend-check
# Expected: ruff, basedpyright, all pass with zero errors
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml poetry.lock backend/config.py
git commit -m "chore(deps): add redis and fakeredis; add redis_url config"
```

---

## Task 3: Create Redis client module

**Files:**
- Create: `backend/redis_client.py`

The client is tested indirectly through the OAuth state tests in Task 4. No dedicated unit tests needed — the module is a thin singleton wrapper.

- [ ] **Step 1: Create `backend/redis_client.py`**

```python
"""Redis client singleton for the application."""

import redis as redis_lib

from backend.config import settings

_client: redis_lib.Redis[str] | None = None


def get_redis() -> redis_lib.Redis[str]:
    """Return the shared Redis client, initialising it on first call.

    The initialisation is not protected by a lock. Two threads could
    simultaneously observe ``_client is None`` and each create a client —
    this is a benign race: both produce equivalent connection-pool-backed
    clients and one simply overwrites the other.

    Returns:
        A configured :class:`redis.Redis` instance with decode_responses=True,
        socket_timeout of 1 second, and retry-on-timeout enabled.

    Raises:
        redis.exceptions.ConnectionError: If Redis is unreachable. Callers
            should let this propagate — OAuth flows fail closed (500) rather
            than falling back to an insecure in-memory store.
    """
    global _client
    if _client is None:
        _client = redis_lib.from_url(  # type: ignore[assignment]
            settings.redis_url,
            decode_responses=True,
            socket_timeout=1,
            retry_on_timeout=True,
        )
    return _client
```

Note on `type: ignore[assignment]`: `redis.from_url` with `decode_responses=True` returns `Redis[str]` via overload, but basedpyright's strict mode may not resolve the overload correctly. If basedpyright resolves this cleanly without the comment, remove it.

- [ ] **Step 2: Verify type-check passes**

```bash
just backend-check
# Expected: zero basedpyright errors
```

If basedpyright reports an error on the `from_url` assignment, try replacing with:

```python
_client = redis_lib.Redis[str].from_url(
    settings.redis_url,
    decode_responses=True,
    socket_timeout=1,
    retry_on_timeout=True,
)
```

- [ ] **Step 3: Commit**

```bash
git add backend/redis_client.py
git commit -m "feat(redis): add Redis client singleton with connection hardening"
```

---

## Task 4: Add fakeredis fixture to conftest and rewrite state store tests

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/test_google_oauth.py`

This task follows TDD: write the failing tests first, then implement the Redis state store.

- [ ] **Step 1: Add `fake_redis` fixture to `tests/conftest.py`**

Add these imports at the top of `conftest.py` (after existing imports):

```python
import fakeredis
from backend import redis_client
```

Add this fixture at the bottom of `conftest.py`:

```python
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
    client: fakeredis.FakeRedis = fakeredis.FakeRedis(server=server, decode_responses=True)
    redis_client._client = client  # type: ignore[assignment]
    yield client
    redis_client._client = None
```

- [ ] **Step 2: Run existing tests to confirm fixture doesn't break anything**

```bash
.venv/bin/pytest tests/test_google_oauth.py -v
# Expected: all pass (state_store is still in place at this point)
```

- [ ] **Step 3: Rewrite `tests/test_google_oauth.py` — update imports and TestStateManagement class**

Replace the import block at the top of `tests/test_google_oauth.py`. Change:

```python
from backend.google_oauth import (
    STATE_TTL_SECONDS,
    build_google_redirect_url,
    exchange_code_for_tokens,
    fetch_google_user_info,
    generate_state,
    state_store,
    validate_and_consume_state,
)
```

To:

```python
import threading

import fakeredis

from backend.google_oauth import (
    STATE_TTL_SECONDS,
    build_google_redirect_url,
    exchange_code_for_tokens,
    fetch_google_user_info,
    generate_state,
    validate_and_consume_state,
)
```

Also remove `import time` from the top — it was only used in `TestStateManagement`.

- [ ] **Step 4: Replace `TestStateManagement` class with Redis-backed tests**

Delete the entire `TestStateManagement` class and replace with:

```python
@allure.feature("Google OAuth2")  # pyright: ignore[reportUnknownMemberType]
@allure.story("State Management")  # pyright: ignore[reportUnknownMemberType]
class TestStateManagement:
    def test_generate_state_returns_unique_tokens(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        s1 = generate_state()
        s2 = generate_state()
        assert s1 != s2
        assert len(s1) > 16

    def test_generate_state_stores_key_in_redis(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        state = generate_state()
        assert fake_redis.exists(f"oauth:state:{state}") == 1

    def test_generate_state_key_has_ttl(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        state = generate_state()
        ttl = fake_redis.ttl(f"oauth:state:{state}")
        # TTL should be close to STATE_TTL_SECONDS (allow 5s drift for slow CI)
        assert int(STATE_TTL_SECONDS) - 5 <= ttl <= int(STATE_TTL_SECONDS)

    def test_validate_and_consume_removes_key(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        state = generate_state()
        validate_and_consume_state(state)
        assert fake_redis.exists(f"oauth:state:{state}") == 0

    def test_validate_rejects_unknown_state(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        with pytest.raises(HTTPException) as exc_info:
            validate_and_consume_state("not-a-real-state")
        assert exc_info.value.status_code == 400

    def test_validate_rejects_expired_state(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        import time
        state = generate_state()
        # Advance the server's clock past the state TTL so Redis considers
        # the key expired. fakeredis honours time_func retroactively on reads.
        fake_redis.time_func = lambda: time.time() + STATE_TTL_SECONDS + 1
        with pytest.raises(HTTPException) as exc_info:
            validate_and_consume_state(state)
        assert exc_info.value.status_code == 400

    def test_concurrent_consumption_only_one_succeeds(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        """GETDEL is atomic — only one thread can consume a state token."""
        state = generate_state()
        results: list[bool] = []
        lock = threading.Lock()

        def try_consume() -> None:
            try:
                validate_and_consume_state(state)
                with lock:
                    results.append(True)
            except HTTPException:
                with lock:
                    results.append(False)

        t1 = threading.Thread(target=try_consume)
        t2 = threading.Thread(target=try_consume)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results.count(True) == 1
        assert results.count(False) == 1
```

- [ ] **Step 5: Run the new tests — expect failures (state_store still in use)**

```bash
.venv/bin/pytest tests/test_google_oauth.py::TestStateManagement -v
# Expected: most tests FAIL — generate_state still writes to dict, not Redis
```

- [ ] **Step 6: Implement Redis state store in `backend/google_oauth.py`**

Remove these lines from the top of `google_oauth.py`:

```python
import time
```

```python
STATE_TTL_SECONDS: float = 600.0  # 10 minutes

# In-memory CSRF state store: {state_token: created_at_monotonic}
# Single-worker POC only — not safe under multi-worker deployments.
state_store: dict[str, float] = {}
```

Replace with:

```python
STATE_TTL_SECONDS: float = 600.0  # 10 minutes — must not exceed this value
```

Add the import for `get_redis` near the top (after the `httpx` import):

```python
from backend.redis_client import get_redis
```

Replace the module docstring state management note:

```python
"""Google OAuth2 protocol helpers.

Single-responsibility module for all Google OAuth2 logic. All outbound HTTP
calls use ``httpx`` in sync mode to match the project's sync handler
architecture.

OAuth2 CSRF state tokens are stored in Redis using SETEX (write with TTL)
and GETDEL (atomic read-and-delete). This is safe for multi-worker deployments.
STATE_TTL_SECONDS defines the maximum replay window for a stolen state token
and must not exceed 600 seconds.
"""
```

Replace `generate_state()`:

```python
def generate_state() -> str:
    """Generate a cryptographically random CSRF state token and store it in Redis.

    The token is stored with a TTL of :data:`STATE_TTL_SECONDS`. Tokens are
    consumed atomically by :func:`validate_and_consume_state` — replay is
    impossible even under concurrent load.

    Returns:
        A URL-safe random string used as the OAuth2 ``state`` parameter.
    """
    state = secrets.token_urlsafe(32)
    get_redis().setex(f"oauth:state:{state}", int(STATE_TTL_SECONDS), "1")
    return state
```

Replace `validate_and_consume_state()`:

```python
def validate_and_consume_state(state: str) -> None:
    """Validate and atomically consume a CSRF state token from Redis.

    Uses GETDEL — a single atomic Redis command that reads the key and
    deletes it in one operation. This prevents replay: if two concurrent
    requests arrive with the same token, only one will get a non-None result.

    Args:
        state: The ``state`` query parameter received in the OAuth2 callback.

    Raises:
        HTTPException: 400 if the state is unknown, expired, or already consumed.
    """
    value = get_redis().getdel(f"oauth:state:{state}")
    if value is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
```

- [ ] **Step 7: Run the tests — expect pass**

```bash
.venv/bin/pytest tests/test_google_oauth.py -v
# Expected: all tests PASS
```

If `test_validate_rejects_expired_state` fails, investigate whether `fake_redis.time_func` applies retroactively in the installed version. If not, use this alternative test body instead:

```python
def test_validate_rejects_expired_state(
    self, fake_redis: fakeredis.FakeRedis
) -> None:
    # Write a key with TTL=1 and sleep 2s (last resort if time_func unavailable)
    state = secrets.token_urlsafe(32)
    fake_redis.setex(f"oauth:state:{state}", 1, "1")
    import time
    time.sleep(2)
    with pytest.raises(HTTPException) as exc_info:
        validate_and_consume_state(state)
    assert exc_info.value.status_code == 400
```

- [ ] **Step 8: Run full type-check and linting**

```bash
just backend-check
# Expected: zero errors
```

- [ ] **Step 9: Commit**

```bash
git add tests/conftest.py tests/test_google_oauth.py backend/google_oauth.py
git commit -m "feat(security): replace in-memory OAuth state store with Redis SETEX/GETDEL"
```

---

## Task 5: Fix JWT delivery — backend sends fragment

**Files:**
- Modify: `backend/user_routes.py`

The change is a single character (`?` → `#`), plus a docstring update. Write the test first.

- [ ] **Step 1: Locate the relevant test file**

There is no existing test for the redirect URL format in the callback. It belongs in a new test class in `tests/test_google_oauth.py` or alongside the Google callback tests. Add it to `tests/test_google_oauth.py`.

- [ ] **Step 2: Write a failing integration test for the fragment redirect**

In `tests/test_google_oauth.py`, add a new import at the top:

```python
from unittest.mock import patch
```

Add a new test class after `TestStateManagement`:

```python
@allure.feature("Google OAuth2")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Callback")  # pyright: ignore[reportUnknownMemberType]
class TestGoogleCallbackRedirect:
    def test_callback_redirects_with_fragment_not_query(
        self, client: TestClient, fake_redis: fakeredis.FakeRedis
    ) -> None:
        """JWT must be in the URL fragment (#token=) not the query string (?token=)."""
        state = generate_state()
        mock_tokens = {"access_token": "google-access-token"}
        mock_user_info = {
            "sub": "google-123",
            "email": "user@example.com",
            "name": "Test User",
            "picture": None,
        }

        with (
            patch("backend.user_routes.exchange_code_for_tokens", return_value=mock_tokens),
            patch(
                "backend.user_routes.fetch_google_user_info",
                return_value=MagicMock(
                    google_id="google-123",
                    email="user@example.com",
                    name="Test User",
                    picture=None,
                ),
            ),
        ):
            response = client.get(
                f"/auth/google/callback?code=auth-code&state={state}",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        location = response.headers["location"]
        assert "#token=" in location, f"Expected fragment token, got: {location}"
        assert "?token=" not in location, f"Token must not be in query string: {location}"
```

Ensure the import line at the top of `tests/test_google_oauth.py` reads:

```python
from unittest.mock import MagicMock, patch
```

Both `MagicMock` and `patch` are needed. `MagicMock` was already present; `patch` was added in Task 4 Step 3.

- [ ] **Step 3: Run the test — expect failure**

```bash
.venv/bin/pytest tests/test_google_oauth.py::TestGoogleCallbackRedirect -v
# Expected: FAIL — location still contains ?token=
```

- [ ] **Step 4: Fix `backend/user_routes.py`**

On the redirect line (currently `?token=`), change to `#token=`:

```python
# Before
frontend_callback = f"{settings.frontend_url}/auth/callback?token={jwt_token}"

# After
frontend_callback = f"{settings.frontend_url}/auth/callback#token={jwt_token}"
```

Also update the `google_callback` docstring `Returns` section. Change:

```
Returns:
    A redirect to the frontend /auth/callback page with the JWT in ``?token=``.
```

To:

```
Returns:
    A redirect to the frontend /auth/callback page with the JWT in the URL
    fragment ``#token=`` — fragments are not transmitted to servers and do not
    appear in access logs or Referer headers.
```

- [ ] **Step 5: Run the test — expect pass**

```bash
.venv/bin/pytest tests/test_google_oauth.py::TestGoogleCallbackRedirect -v
# Expected: PASS
```

- [ ] **Step 6: Run all backend tests**

```bash
.venv/bin/pytest -v
# Expected: all pass
```

- [ ] **Step 7: Commit**

```bash
git add backend/user_routes.py tests/test_google_oauth.py
git commit -m "fix(security): deliver JWT via URL fragment instead of query parameter"
```

---

## Task 6: Fix frontend — read token from hash and clear history

**Files:**
- Modify: `frontend/src/views/AuthCallbackView.vue`
- Modify: `frontend/src/__tests__/AuthCallbackView.test.ts`

- [ ] **Step 1: Update `AuthCallbackView.test.ts` — expect hash-based token**

Replace the entire test file content:

```typescript
import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import AuthCallbackView from '../views/AuthCallbackView.vue'

const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
  }
})()
Object.defineProperty(global, 'localStorage', { value: localStorageMock })

// Track replaceState calls to verify the fragment is cleared
const replaceStateSpy = vi.spyOn(window.history, 'replaceState')

describe('AuthCallbackView', () => {
  beforeEach(() => {
    localStorageMock.clear()
    replaceStateSpy.mockClear()
    vi.resetModules()
  })

  it('stores token from URL fragment in localStorage and navigates to /', async () => {
    // Simulate the browser having a fragment set by the OAuth callback redirect
    Object.defineProperty(window, 'location', {
      value: { ...window.location, hash: '#token=test-jwt-token', pathname: '/auth/callback' },
      writable: true,
    })

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth/callback', component: AuthCallbackView },
        { path: '/', component: { template: '<div>home</div>' } },
      ],
    })
    await router.push('/auth/callback')

    mount(AuthCallbackView, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(localStorageMock.getItem('access_token')).toBe('test-jwt-token')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('clears the URL fragment from history after extracting the token', async () => {
    Object.defineProperty(window, 'location', {
      value: { ...window.location, hash: '#token=test-jwt-token', pathname: '/auth/callback' },
      writable: true,
    })

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth/callback', component: AuthCallbackView },
        { path: '/', component: { template: '<div>home</div>' } },
      ],
    })
    await router.push('/auth/callback')

    mount(AuthCallbackView, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(replaceStateSpy).toHaveBeenCalledWith(null, '', '/auth/callback')
  })

  it('navigates to / even when no token is present', async () => {
    Object.defineProperty(window, 'location', {
      value: { ...window.location, hash: '', pathname: '/auth/callback' },
      writable: true,
    })

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth/callback', component: AuthCallbackView },
        { path: '/', component: { template: '<div>home</div>' } },
      ],
    })
    await router.push('/auth/callback')

    mount(AuthCallbackView, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(localStorageMock.getItem('access_token')).toBeNull()
    expect(router.currentRoute.value.path).toBe('/')
  })
})
```

- [ ] **Step 2: Run the frontend tests — expect failures**

```bash
just frontend-test
# Expected: "stores token from URL fragment" FAIL — component still reads route.query.token
```

- [ ] **Step 3: Update `AuthCallbackView.vue`**

Replace the entire `<script setup>` block:

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { setToken } = useAuth()

onMounted(() => {
  const hash = window.location.hash.slice(1) // remove leading '#'
  const params = new URLSearchParams(hash)
  const token = params.get('token')
  // Clear the fragment from the current history entry immediately.
  // This prevents the token from persisting in browser history and removes
  // it from the address bar before router.push() adds a new history entry.
  window.history.replaceState(null, '', window.location.pathname)
  if (token) {
    setToken(token)
  }
  void router.push('/')
})
</script>
```

Note: `useRoute` is no longer imported — the component reads from the browser API directly.

- [ ] **Step 4: Run the frontend tests — expect pass**

```bash
just frontend-test
# Expected: all AuthCallbackView tests PASS
```

- [ ] **Step 5: Run full frontend checks**

```bash
just frontend-check
# Expected: ESLint and TypeScript build pass with zero errors
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/AuthCallbackView.vue frontend/src/__tests__/AuthCallbackView.test.ts
git commit -m "fix(security): read OAuth JWT from URL fragment and clear history entry"
```

---

## Task 7: Final verification

- [ ] **Step 1: Run the full CI gate**

Ensure Redis and the DB are running first:

```bash
just platform-up
just dev-up
```

Then:

```bash
just ci
# Expected: all checks pass — ruff, basedpyright, pytest, frontend lint/build/test, e2e
```

- [ ] **Step 2: Manual smoke test**

1. Open `http://localhost:5173`
2. Click "Sign in with Google" (or navigate to the login page)
3. Complete the OAuth flow
4. Verify the address bar shows `/` with no `#token=` fragment after redirect completes
5. Verify you are authenticated (user profile visible or sequences table loads)

- [ ] **Step 3: Verify Redis is being used**

```bash
docker compose exec redis redis-cli monitor
# In another terminal, trigger a Google login
# Expected: SETEX oauth:state:<token> 600 1 appears in the monitor output
```

- [ ] **Step 4: Commit any final fixes, then review pre-PR checklist**

Follow GIT_STANDARDS.md:

```bash
# Check all logs are clean
just dev-logs  # scan for errors
docker compose logs --tail=20

# Squash commits into one logical commit before raising PR
git rebase -i origin/main
# Mark all commits except the first as 'squash', write a single message:
# fix(security): replace in-memory OAuth state with Redis; deliver JWT via fragment
```
