# OAuth2 Security Critical Fixes — Design Spec

**Date:** 2026-03-21
**Branch:** `feat/google-oauth2-social-login`
**Status:** Approved

## Problem Statement

Two critical security issues exist in the Google OAuth2 implementation:

1. **JWT delivered via URL query parameter** — tokens appear in browser history, server access logs, CDN logs, and `Referer` headers, exposing them to inadvertent leakage.
2. **In-memory OAuth CSRF state store** — `state_store: dict[str, float]` is process-local; it breaks under multi-worker deployments and is lost on restart.

---

## Fix 1 — JWT Delivery via URL Fragment

### Approach

Replace the `?token=` query parameter in the post-OAuth redirect with a URL fragment (`#token=`).

```
Before: {frontend_url}/auth/callback?token=eyJ...
After:  {frontend_url}/auth/callback#token=eyJ...
```

### Why Fragments Are Safer

URL fragments are processed entirely in the browser. They are **never transmitted to servers** — they do not appear in:
- HTTP access logs (backend, CDN, reverse proxy)
- `Referer` headers on subsequent navigations
- Server-side request logging

They remain in browser history, which is an accepted residual risk for this delivery method (ref: RFC 9110 §4.1).

### Changes

**Backend — `backend/user_routes.py` (line 111):**

```python
# Before
frontend_callback = f"{settings.frontend_url}/auth/callback?token={jwt_token}"

# After
frontend_callback = f"{settings.frontend_url}/auth/callback#token={jwt_token}"
```

The `google_callback` docstring on the same function must also be updated — the `Returns` line currently states `the JWT in ``?token=``` and must reference `#token=` after the change.

**Frontend — `frontend/src/views/AuthCallbackView.vue`:**

Read token from `window.location.hash` instead of `route.query.token`. Immediately after reading, clear the fragment from the browser's history entry so the token does not persist in history or the address bar. Since `window.location` is a browser global, `useRoute()` is no longer needed for token extraction and can be removed from the component:

```typescript
onMounted(() => {
  const hash = window.location.hash.slice(1)  // remove leading '#'
  const params = new URLSearchParams(hash)
  const token = params.get('token')
  // Clear the fragment from history immediately — prevents token persistence
  // in browser history and removes it from the address bar.
  window.history.replaceState(null, '', window.location.pathname)
  if (token) {
    setToken(token)
  }
  void router.push('/')
})
```

`replaceState` must be called **before** `router.push` so the fragment is erased from the current history entry before navigation occurs. No changes required to `useAuth.ts`, `localStorage` storage, or API clients.

### Trade-offs

| | Query param (current) | Fragment (new) |
|---|---|---|
| Appears in server logs | Yes | No |
| Appears in Referer header | Yes | No |
| Appears in browser history | Yes | Yes (residual) |
| Vue Router readable | Yes | Requires `window.location.hash` |

---

## Fix 2 — Redis-Backed OAuth CSRF State Store

### Approach

Replace the module-level `dict[str, float]` in `google_oauth.py` with Redis-backed state using `SETEX` (write with TTL) and `GETDEL` (atomic read-and-delete). `GETDEL` is available in redis-py ≥ 4.0 and fakeredis ≥ 2.0.

### State TTL Constraint

`STATE_TTL_SECONDS` is set to `600` (10 minutes). This is the maximum acceptable value — it defines the window during which a stolen state token could be replayed. The value must not exceed 600 seconds. For higher-security environments, reduce to 300 seconds (5 minutes). This constant must remain explicitly defined in `google_oauth.py` and must not be made configurable without a corresponding review.

### Infrastructure Additions

**`docker-compose.yml`:** Add a `redis` service.

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

**`justfile`:** Add a `redis-up` recipe and wire it into `platform-up`. The existing `db-up` recipe uses an explicit service name (`docker compose up -d db`), so Redis will not start automatically unless referenced. Update `platform-up`:

```makefile
redis-up:
    docker compose up -d redis

platform-up: db-up redis-up obs-up
```

**`backend/config.py`:** Add `redis_url` setting with a default that matches the docker-compose service:

```python
redis_url: str = "redis://localhost:6379/0"
```

The default covers local development — no `.env` change is required. For CI, `fakeredis` bypasses the real Redis connection entirely (see Testing section), so no `REDIS_URL` environment variable needs to be added to `pyproject.toml`'s `[tool.pytest.ini_options] env` block.

**`pyproject.toml`:** Add `redis` as a production dependency and `fakeredis` as a dev-only dependency:

```toml
[tool.poetry.dependencies]
redis = "^5.0"

[tool.poetry.group.dev.dependencies]
fakeredis = "^2.20"   # ^2.20 minimum for full Redis 7 command coverage
```

### New Module — `backend/redis_client.py`

A lazily-initialised Redis client singleton. Two threads could simultaneously observe `_client is None` and each create a client — this is an accepted benign race, since both threads produce equivalent `Redis` objects (connection-pool backed, thread-safe once created) and one simply overwrites the other. A `threading.Lock` is not required.

```python
"""Redis client singleton for the application."""

import redis as redis_lib

from backend.config import settings

_client: redis_lib.Redis | None = None  # type: ignore[type-arg]


def get_redis() -> redis_lib.Redis:  # type: ignore[type-arg]
    """Return the shared Redis client, initialising it on first call.

    Returns:
        A configured :class:`redis.Redis` instance with decode_responses=True.
    """
    global _client
    if _client is None:
        _client = redis_lib.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=1,        # fail fast — don't hang auth flows
            retry_on_timeout=True,   # retry once on transient network hiccup
        )
    return _client
```

**Failure behaviour:** If Redis is unavailable, `generate_state()` and `validate_and_consume_state()` will raise a `redis.exceptions.ConnectionError`. This propagates as a 500 from the OAuth endpoints — the flow fails closed. No partial authentication is possible without a functioning Redis. This is the correct production behaviour; it is not papered over with a fallback to the in-memory store.

### State Store Operations

**`backend/google_oauth.py` changes:**
- Remove the module-level `state_store: dict[str, float]` declaration
- Remove the `import time` statement (no longer needed)
- Update `generate_state()` and `validate_and_consume_state()`

```python
def generate_state() -> str:
    state = secrets.token_urlsafe(32)
    get_redis().setex(f"oauth:state:{state}", int(STATE_TTL_SECONDS), "1")
    return state


def validate_and_consume_state(state: str) -> None:
    value = get_redis().getdel(f"oauth:state:{state}")
    if value is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
```

TTL enforcement is handled by Redis automatically — no manual expiry check is needed.

### Why `GETDEL` Over `GET` + `DEL`

A `GET` followed by `DEL` is two separate operations. Between them, a second concurrent request with the same state token could `GET` and also succeed — a race that allows state replay. `GETDEL` is atomic at the Redis level: exactly one caller receives a non-None result, and the key is deleted in the same operation.

### Key Naming Convention

All OAuth state keys use the prefix `oauth:state:` to namespace them from future Redis usage (e.g., a JWT revocation blocklist would use `oauth:revoked:`).

---

## Testing Strategy

### fakeredis Fixture

Add `fakeredis ^2.20` as a dev dependency. In `tests/conftest.py`:

```python
import fakeredis
import pytest
from backend import redis_client

@pytest.fixture(scope="function")  # must be function-scoped — FakeServer is stateful
def fake_redis():
    """Provide an isolated in-process Redis for each test.

    A fresh FakeServer is created per test invocation. Sharing a FakeServer
    across tests would cause state bleed between OAuth state tokens.
    Never promote this fixture to session scope.
    """
    server = fakeredis.FakeServer()
    client = fakeredis.FakeRedis(server=server, decode_responses=True)
    redis_client._client = client
    yield client
    redis_client._client = None
```

**Important:** The `FakeServer` instance is the isolation boundary — it must be created fresh inside the fixture body, never at module level or with `scope="session"`. Each test gets its own in-memory Redis state.

### Expired State Test

Rather than sleeping (fragile, slow), use `fakeredis`'s clock override to advance time:

```python
def test_validate_rejects_expired_state(fake_redis):
    import time
    state = generate_state()
    # Advance fakeredis's internal clock past the TTL
    fake_redis.time_func = lambda: time.time() + STATE_TTL_SECONDS + 1
    # Re-set the key with an already-expired TTL (1 second)
    fake_redis.setex(f"oauth:state:{state}", 1, "1")
    # Alternatively: manipulate server time via FakeServer if available
    with pytest.raises(HTTPException) as exc:
        validate_and_consume_state(state)
    assert exc.value.status_code == 400
```

Note: `fakeredis` TTL expiry is time-based internally. If clock manipulation is unavailable in the installed version, use `setex` with TTL=1 and `time.sleep(2)` as a fallback — acceptable only in this one test since it's fast and deterministic.

### Concurrent Consumption Test

`fakeredis` handles concurrent Python threads through its `FakeServer`'s internal locking. Use a shared `FakeServer` across both threads so `GETDEL` atomicity is preserved:

```python
def test_concurrent_state_consumption(fake_redis):
    import threading
    state = generate_state()
    results: list[bool] = []
    lock = threading.Lock()

    def try_consume():
        try:
            validate_and_consume_state(state)
            with lock:
                results.append(True)
        except HTTPException:
            with lock:
                results.append(False)

    t1 = threading.Thread(target=try_consume)
    t2 = threading.Thread(target=try_consume)
    t1.start(); t2.start()
    t1.join(); t2.join()

    assert results.count(True) == 1
    assert results.count(False) == 1
```

Both threads share the same `fake_redis` client (and thus the same `FakeServer`), so `GETDEL` atomicity is exercised correctly.

### Full Test Case List

**`tests/test_google_oauth.py` updates:**
- Remove `from backend.google_oauth import state_store` import
- Remove any `setup_method` / `teardown_method` that called `state_store.clear()`
- Add `fake_redis` fixture parameter to all state-related tests
- `test_generate_state_stores_key_in_redis` — key exists with TTL after `generate_state()`
- `test_validate_and_consume_removes_key` — key absent after successful validation
- `test_validate_rejects_unknown_state` — 400 on unknown token
- `test_validate_rejects_expired_state` — uses clock manipulation (see above)
- `test_concurrent_state_consumption` — two threads, exactly one succeeds

**`frontend/src/__tests__/AuthCallbackView.test.ts`:**
- Update test setup to provide token via `window.location.hash = '#token=...'` rather than mocking `route.query.token`

---

## Files Changed

| File | Change |
|------|--------|
| `backend/user_routes.py` | `?token=` → `#token=`; update `google_callback` docstring |
| `backend/google_oauth.py` | Remove `state_store` dict, `import time`; use Redis via `get_redis()` |
| `backend/redis_client.py` | New — Redis client singleton |
| `backend/config.py` | Add `redis_url: str` setting |
| `docker-compose.yml` | Add `redis:7-alpine` service with healthcheck |
| `justfile` | Add `redis-up` recipe; add to `platform-up` dependencies |
| `pyproject.toml` | Add `redis ^5.0` (prod); `fakeredis ^2.20` (dev group) |
| `frontend/src/views/AuthCallbackView.vue` | Read token from `window.location.hash`; clear fragment via `replaceState`; remove `useRoute()` |
| `tests/conftest.py` | Add `fake_redis` fixture (function-scoped) |
| `tests/test_google_oauth.py` | Remove `state_store` imports; update + extend state tests |
| `frontend/src/__tests__/AuthCallbackView.test.ts` | Update to set `window.location.hash` |

---

## Security Positioning

This change resolves two critical security issues and brings the implementation to an acceptable production baseline. However, the current approach still falls short of OAuth2 best practice for SPAs. The following gaps are acknowledged and must be addressed in a follow-on iteration before this is considered fully hardened.

### Residual risks in this implementation

| Risk | Explanation |
|------|-------------|
| **JWT in fragment still vulnerable to XSS** | Any XSS can read `window.location.hash` before `replaceState` clears it. Fragment protects transport (logs, headers), not execution context. Mitigated but not eliminated. |
| **Token is reusable** | The JWT is not single-use and not bound to a specific session or client fingerprint. A stolen token is valid until expiry. |
| **No PKCE** | The current Authorization Code flow without PKCE is weaker than modern OAuth2 best practice for SPAs (RFC 7636). A code interception attack remains theoretically possible. |
| **Token stored in localStorage** | localStorage is accessible to any same-origin JS. An XSS attack reads the token after it has been stored. HttpOnly cookies would eliminate this vector. |

### Out of Scope (follow-on security hardening)

- **PKCE** (RFC 7636) — replace current flow with Authorization Code + PKCE; removes token-in-URL entirely
- **HttpOnly cookie delivery** — removes token from JS context; eliminates XSS token theft
- **Refresh token rotation + revocation blocklist** — use Redis `oauth:revoked:` namespace
- **Rate limiting** on `/auth/google/login`, `/auth/google/callback`, and `/auth/token`
- **HTTPS enforcement** validation in production config
- **JWT claims whitelisting** — constrain `extra_claims` to a fixed allowlist
- **Redis health check on startup** — fail fast if Redis is unreachable at boot rather than at first auth request
- **Observability** — structured log events for state validation failures, Redis errors, OAuth error rates
