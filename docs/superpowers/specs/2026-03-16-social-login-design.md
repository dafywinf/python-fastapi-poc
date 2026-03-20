# Social Login Design — Google OAuth2 + User Management

**Date:** 2026-03-16
**Status:** Approved
**Phase:** 5 (extends Phase 4 — Data & Interaction Split)

---

## Overview

Replace the single hardcoded admin user with Google OAuth2 social login. Any user who authenticates via Google gains write access to sequences. A `users` table persists Google profile data, and a new Users page in the frontend shows who has logged in.

The existing password-based `/auth/token` endpoint is retained in the codebase but only registered when `ENABLE_PASSWORD_AUTH=true`, allowing the existing test suite to continue running without modification.

---

## Goals

- Users log in via Google (Authorization Code Flow — server-side token exchange)
- Authenticated users can create, edit, and delete sequences (same access model as today)
- Google profile (id, email, name, picture) is persisted to a `users` table on first login
- A `/users` page in the Vue SPA lists all users who have logged in (deliberate: public read access — see note in API section)
- The Navbar shows the logged-in user's avatar + email, with a Logout action
- No new production Python dependencies beyond promoting `httpx` from dev to production
- The test suite continues to work without a real Google account

---

## OAuth2 Flow (Authorization Code — Backend-Driven)

```
1. User clicks "Sign in with Google" in the SPA
2. LoginPage sets window.location.href = '/auth/google/login'
   (must be a top-level navigation, NOT fetch/XHR — a fetch call would be blocked by CORS
    and cannot follow the cross-origin redirect to Google)
3. Backend generates a random state (secrets.token_urlsafe), stores it with timestamp,
   returns RedirectResponse(302) to Google consent screen
4. User authenticates with Google
5. Google redirects to GET /auth/google/callback?code=…&state=…
6. Backend verifies state (rejects unknown or expired states with HTTP 400)
7. Backend POSTs code to Google token endpoint (https://oauth2.googleapis.com/token)
   using httpx in sync mode: httpx.post(...)  — NOT the async client
8. Backend GETs user profile from Google userinfo API (https://www.googleapis.com/oauth2/v3/userinfo)
   using httpx in sync mode: httpx.get(...)
9. Backend upserts user in the `users` table (insert on first login, update name/picture on subsequent)
10. Backend issues its own JWT (subject = user email, same algorithm/expiry as today)
11. Backend redirects to {settings.frontend_url}/auth/callback?token=<jwt>
12. Vue /auth/callback page reads token from URL, saves to localStorage under key 'access_token',
    navigates to /
```

**State management:** In-memory dict `{state: created_at_timestamp}`. States expire after 10 minutes and are removed when validated. Abandoned OAuth flows (user navigates away after step 2) leave their state in the dict until it expires on the next validation attempt — no background cleanup is performed. Memory growth from abandoned states is negligible and acceptable for a POC.

**Deployment constraint:** The in-memory state store is not safe under multi-worker deployments (each worker has its own dict). This is a deliberate POC-only choice — the backend must be run with a single worker (`uvicorn ... --workers 1`, which is the default for `just backend-dev`).

**Security:** Client secret never touches the browser. CSRF prevented by state parameter validation. No PKCE required (server-side flow with client secret).

**Known limitation:** The JWT is passed as `?token=<jwt>` in the redirect URL. This exposes the token in browser history, server access logs, and the `Referer` header of any subsequent navigations. This is a deliberate POC trade-off. In production this would be mitigated by using a short-lived one-time code exchanged for the JWT via a POST, or by setting the token in an HttpOnly cookie instead.

---

## Data Model

### New table: `users`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | Integer | Primary key | Auto-increment |
| `google_id` | String | Unique, not null | Stable Google account identifier |
| `email` | String | Unique, not null | JWT subject; displayed in UI |
| `name` | String | Not null | Display name from Google profile |
| `picture` | String | Nullable | Avatar URL from Google profile (Google CDN URLs rotate; the upsert on each login keeps this current) |
| `created_at` | DateTime(tz) | Server default now() | First login timestamp |

A new Alembic migration creates this table.

---

## Backend Components

### New files

**`backend/google_oauth.py`**
Single-responsibility module for all Google OAuth2 protocol logic. All httpx calls use sync mode (no `AsyncClient`) to match the project's sync handler architecture:
- `build_google_redirect_url(state: str) -> str` — constructs the Google authorization URL
- `exchange_code_for_tokens(code: str) -> dict[str, str]` — POSTs to Google token endpoint via `httpx.post(...)`
- `fetch_google_user_info(access_token: str) -> GoogleUserInfo` — GETs profile from userinfo API via `httpx.get(...)`
- `generate_state() -> str` — creates and stores a new state token with current timestamp
- `validate_and_consume_state(state: str) -> None` — raises `HTTPException(400)` if unknown or expired; removes state on success

**`backend/user_routes.py`**
FastAPI router with four endpoints:
- `GET /auth/google/login` — generates state, returns `RedirectResponse` to Google
- `GET /auth/google/callback` — validates state, exchanges code, upserts user, issues JWT, returns `RedirectResponse` to frontend
- `GET /users/` — returns list of all users (public — see API Endpoints note)
- `GET /users/me` — returns the authenticated user's profile (requires valid JWT)

**`GET /users/me` dependency pattern:** `WriteDep` and `get_optional_user` return the JWT subject as a `str` (user email for Google-issued tokens). `GET /users/me` needs the full `User` ORM object, so it uses a dedicated dependency layered on top:

```python
def _get_current_user(email: WriteDep, session: SessionDep) -> User:
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

CurrentUserDep = Annotated[User, Depends(_get_current_user)]
```

This keeps `security.py` unchanged — `WriteDep` continues to return a `str` email.

### Modified files

| File | Change |
|---|---|
| `backend/models.py` | Add `User` ORM model (SQLAlchemy 2.0 `Mapped`/`mapped_column` pattern) |
| `backend/schemas.py` | Add `UserResponse` DTO: `id`, `email`, `name`, `picture`, `created_at`. Used for both `GET /users/` list items and `GET /users/me` response — single DTO, no separate `UserMeResponse`. |
| `backend/config.py` | Add `google_client_id: str = ""`, `google_client_secret: str = ""`, `frontend_url: str = "http://localhost:5173"`, `backend_url: str = "http://localhost:8000"`, `enable_password_auth: bool = False`. Make `admin_username: str = "admin"` and `admin_password_hash: str = ""` optional (give them defaults) so the app starts without these set when `enable_password_auth=False`. `google_client_id` and `google_client_secret` use empty string defaults so the app imports cleanly in tests without these env vars set — they are only needed at runtime when the Google endpoints are actually called. The Google redirect URI is derived as `f"{settings.backend_url}/auth/google/callback"` and must match the URI registered in Google Cloud Console. |
| `backend/main.py` | Register `user_router`; register `auth_router` only when `settings.enable_password_auth` is True. **Implementation note:** `settings` is a module-level singleton in `config.py`. The conditional `if settings.enable_password_auth: app.include_router(auth_router)` in `main.py` reads the value at import time. `pytest-env` sets `os.environ` before pytest collects tests, which is before `conftest.py` creates the `TestClient` (which triggers the import of `main.py`). This works correctly provided `backend.main` is not imported at module level in `conftest.py` — it isn't currently (the `client` fixture creates `TestClient` inside the fixture function body). |
| `backend/security.py` | JWT subject is now user email (was hardcoded admin username); `WriteDep` and `get_optional_user` unchanged — they still return `str` |
| `pyproject.toml` | Move `httpx` from dev to production dependencies; add `pytest-env` as a dev dependency |

### JWT subject across password grant and Google OAuth

The `POST /auth/token` password grant issues a JWT with `subject = form_data.username` (e.g. `"admin"`). Google OAuth issues a JWT with `subject = user_email`. These are different strings.

For backend unit tests that only test sequences or write access (`WriteDep`), the subject value does not matter — any valid JWT works.

For backend tests of `GET /users/me`, the test must seed a `User` row whose `email` matches the JWT subject. Test fixtures for `/users/me` should insert a `User` directly via the DB session (not via the Google OAuth flow) with `email="admin"` (matching the password grant subject), or use a dedicated test JWT with a known email and a matching seeded `User` row.

Playwright E2E tests inject a JWT from `POST /auth/token` (subject=`"admin"`) into localStorage and test authenticated UI state (Create button visible, email in Navbar). They do not call `GET /users/me`.

---

## Frontend Components

### New pages

| Route | Component | Purpose |
|---|---|---|
| `/login` | `LoginPage.vue` | "Sign in with Google" button — sets `window.location.href = '/auth/google/login'` (top-level navigation, not fetch) |
| `/auth/callback` | `AuthCallbackPage.vue` | Reads `?token=` from URL, saves to localStorage under key `'access_token'`, redirects to `/` |
| `/users` | `UsersPage.vue` | Table of all users: avatar, name, email, joined date |

### New composable

**`frontend/src/composables/useAuth.ts`**
Single source of truth for authentication state. Uses a `ref<string | null>` (not a plain computed reading `localStorage` directly) so that writes made in the same component lifecycle (e.g. `AuthCallbackPage` calling `setToken()`) are immediately reactive:

```typescript
const _token = ref<string | null>(localStorage.getItem('access_token'))

function setToken(t: string): void {
  localStorage.setItem('access_token', t)
  _token.value = t
}

function logout(): void {
  localStorage.removeItem('access_token')
  _token.value = null
  router.push('/')
}
```

Exposed interface:
- `isAuthenticated: ComputedRef<boolean>` — true if `_token.value` is non-null and `exp` claim > now
- `user: ComputedRef<{ email: string; name: string } | null>` — decoded from `_token.value` payload
- `token: ComputedRef<string | null>` — raw JWT string
- `setToken(t: string): void` — used by `AuthCallbackPage` after reading the token from the URL
- `login(): void` — navigates to `/login`
- `logout(): void` — clears ref + localStorage, navigates to `/`

The `ref`-backed approach makes the composable straightforwardly testable in Vitest — set `_token.value`, assert `isAuthenticated` updates without re-mounting.

The localStorage key `'access_token'` matches the key already used by `frontend/src/api/sequences.ts` — no change to the existing API client key.

### Modified components

| Component | Change |
|---|---|
| `Navbar.vue` | Show user avatar + email + Logout when `isAuthenticated`; show "Sign in with Google" button when not. Add Users nav link. |
| `SequencesPage.vue` | Show Create / Edit / Delete actions only when `isAuthenticated` |
| `frontend/src/api/sequences.ts` | Already reads `localStorage.getItem('access_token')` — confirm it attaches the header on all mutating requests (POST, PATCH, DELETE). Refactor to read from `useAuth().token` for consistency. |

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/auth/google/login` | Public | Generate state, redirect to Google |
| `GET` | `/auth/google/callback` | Public | Exchange code, upsert user, issue JWT, redirect to frontend |
| `GET` | `/users/` | Public (deliberate) | List all users who have logged in. Exposes names and emails of all accounts — acceptable for an internal POC. |
| `GET` | `/users/me` | JWT required | Return the authenticated user's full `UserResponse` |
| `POST` | `/auth/token` | N/A (test only) | Password grant — only registered when `ENABLE_PASSWORD_AUTH=true` |

---

## Configuration

New environment variables (added to `.env`):

```
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
ENABLE_PASSWORD_AUTH=true   # set true for local dev so Playwright E2E and manual testing work
```

Fields with defaults do not need to be set in `.env` unless overriding. `google_client_id` and `google_client_secret` default to `""` and only cause errors if the Google OAuth endpoints are actually called with empty values — the rest of the app (health, sequences, auth token) continues to work without them.

The Google redirect URI registered in Google Cloud Console must be `http://localhost:8000/auth/google/callback` (matching `BACKEND_URL`).

### Enabling password auth for tests

**Backend unit/integration tests:** `pytest-env` sets env vars before test collection. Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
env = ["ENABLE_PASSWORD_AUTH=true"]
```

This works because `conftest.py` creates `TestClient` inside the fixture function body (not at module level), so `backend.main` is imported after `pytest-env` has set the env var — the conditional router registration sees `enable_password_auth=True`.

**Playwright E2E tests:** Run against the live backend started by `just dev-up`. With `ENABLE_PASSWORD_AUTH=true` in `.env` (as recommended above for local dev), the password endpoint is available. The Playwright tests call `POST /auth/token` to obtain a JWT, then inject it into localStorage.

---

## Testing Strategy

### Backend (pytest + testcontainers — real PostgreSQL)

| Test | Approach |
|---|---|
| `GET /auth/google/login` | Assert 302 redirect; `Location` header contains `accounts.google.com`; `state` query param present |
| `GET /auth/google/callback` — success | Patch `httpx.post` (token exchange) and `httpx.get` (userinfo) with `unittest.mock.patch`; assert user upserted in DB; assert `Location` header in 302 redirect contains JWT |
| `GET /auth/google/callback` — invalid state | Assert 400 response |
| `GET /auth/google/callback` — expired state | Assert 400 response |
| `GET /users/` | Seed user rows via DB session; assert response list matches |
| `GET /users/me` | Seed a `User` row with `email="admin"` via DB session; pass JWT with `subject="admin"` from `POST /auth/token`; assert correct `UserResponse` returned |
| Existing auth tests | Unchanged — `ENABLE_PASSWORD_AUTH=true` via `pytest-env` keeps `/auth/token` registered |

Google API calls are patched with `unittest.mock.patch` — no new test dependencies beyond `pytest-env`.

### Frontend (Vitest + Playwright)

| Test | Approach |
|---|---|
| `useAuth` composable | Vitest unit tests — set `_token` ref directly, assert `isAuthenticated`, JWT decode, expiry detection |
| `AuthCallbackPage` | Vitest — mount with `?token=<jwt>` query param, call `setToken`, assert `'access_token'` in localStorage, navigation triggered |
| Playwright E2E login | Call `POST /auth/token` to get a JWT; inject via `page.evaluate(() => localStorage.setItem('access_token', token))`; assert Create button visible, user email in Navbar |
| Playwright users page | Navigate to `/users`; assert table renders at least one user row |

The Playwright suite never contacts Google — it uses the password endpoint to obtain a real JWT from the running backend and injects it directly into localStorage.

---

## Task Plan Updates

This design covers the remaining Phase 4 items:
- [ ] Login Flow UI and JWT persistence in localStorage
- [ ] Edit Mode with conditional rendering based on auth state

And introduces Phase 5:
- [ ] Google OAuth2 backend (`google_oauth.py` + `user_routes.py`)
- [ ] User model + Alembic migration
- [ ] `pytest-env` dev dependency + `pyproject.toml` env config
- [ ] `admin_username` / `admin_password_hash` / `google_client_id` / `google_client_secret` made optional with defaults in `config.py`
- [ ] Frontend login flow (`LoginPage`, `AuthCallbackPage`, `useAuth` composable)
- [ ] Users page
- [ ] Navbar auth state
- [ ] Sequences page conditional edit UI
- [ ] Tests (backend unit + Vitest + Playwright E2E)
