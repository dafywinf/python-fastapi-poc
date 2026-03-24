# Security Review: `feat/security-harden-v2`

**Review Date:** 2026-03-24
**Branch:** `feat/security-harden-v2`
**Scope:** Full diff vs `main` — 19 files, +1275 / -409 lines
**Status:** Review complete. Findings to address before merge.

---

## Executive Summary

This branch implements a substantial and well-considered security hardening of the OAuth2 / JWT authentication system. The overall design is sound: HttpOnly cookie delivery eliminates the previously exposed JWT in the URL fragment and localStorage; PKCE (S256) significantly reduces the risk of authorization code interception; refresh token rotation with Redis-backed atomicity prevents replay; and the revocation check fails-closed rather than open. The test coverage for the new controls is notably thorough.

However, several concrete security deficiencies remain, ranging from a **High** risk state-management atomicity gap to several **Medium** issues involving cookie security under HTTP, rate limiter bypass, and a missing CSRF control on the logout endpoint. There are no hardcoded secrets, and no critical vulnerabilities were identified.

**Overall Risk Rating: Medium** (after addressing the High and critical-path Medium findings)

---

## Findings Table

| ID | Severity | Title | Status |
|----|----------|-------|--------|
| SEC-01 | High | PKCE state and verifier written in two non-atomic Redis operations | Open |
| SEC-02 | Medium | `access_token` cookie sets `Secure=True` while `enforce_https` defaults to `False` | Open |
| SEC-03 | Medium | Rate limiter uses source IP from `X-Forwarded-For` without validating proxy trust | Open |
| SEC-04 | Medium | Logout endpoint has no CSRF protection | Open |
| SEC-05 | Medium | `delete_cookie()` on logout does not mirror all original cookie attributes | Open |
| SEC-06 | Medium | No 401 interceptor — refresh token orphaned, expired tokens cause silent failures | Open |
| SEC-07 | Low | Tokens without `jti` claim bypass revocation check silently | Open |
| SEC-08 | Low | `access_token` SameSite=Lax permits sending on top-level navigational cross-site GETs | Open |
| SEC-09 | Low | `enforce_https=False` default risks silent HTTP production deployment | Open |
| SEC-10 | Low | `_checked` module-level singleton in `useAuth` prevents re-checking after token expiry | Open |
| SEC-11 | Low | `logout()` does not await server response status before clearing local state | Open |
| SEC-12 | Info | CORS `allow_methods=["*"]` is broader than necessary | Open |
| SEC-13 | Info | CORS `allow_headers=["*"]` exposes preflight to any custom header | Open |
| SEC-14 | Info | `WWW-Authenticate: Bearer` on cookie-auth 401 is misleading | Open |
| SEC-15 | Info | Redis singleton race documented as benign | Accepted |

---

## Detailed Findings

### SEC-01 — High: PKCE state and verifier written in two non-atomic Redis operations

**File:** `backend/google_oauth.py`, `generate_state()` — two separate `setex` calls

**Description:**
`generate_state()` stores the CSRF state token and the PKCE code verifier with two separate `setex` calls. If the process crashes or Redis evicts a key between the two writes, the state token will be stored without a corresponding verifier. The callback will consume the state (GETDEL) but `consume_pkce_verifier` will return None → 400, silently breaking the user's login.

Additionally, `validate_and_consume_state` and `consume_pkce_verifier` in the callback are two separate GETDEL operations — not jointly atomic.

**Remediation:** Use a Redis pipeline or `MULTI/EXEC` to write both keys atomically:
```python
pipe = get_redis().pipeline(transaction=True)
pipe.setex(state_key, STATE_TTL_SECONDS, "1")
pipe.setex(pkce_key, STATE_TTL_SECONDS, code_verifier)
pipe.execute()
```
Alternatively, store the verifier as the value of the state key (single key = single GETDEL = fully atomic consumption).

**References:** RFC 7636 §7.1

---

### SEC-02 — Medium: `access_token` cookie sets `Secure=True` while `enforce_https` defaults to `False`

**File:** `backend/user_routes.py` (cookie set_cookie calls); `backend/config.py:54`

**Description:**
Both `google_callback` and `refresh_token` set `secure=True` on cookies. But `enforce_https` defaults to `False`, so the server can start over HTTP without any warning. On HTTP, browsers silently drop `Secure` cookies — authentication breaks entirely, and tokens are sent in cleartext.

**Remediation:**
1. Change `enforce_https` default to `True` (opt-out for dev via `ENFORCE_HTTPS=false`).
2. Or conditionally set `secure` based on request scheme: `secure = request.url.scheme == "https"`.
3. Add a startup warning when backend_url is HTTP, even if `enforce_https=False`.

---

### SEC-03 — Medium: Rate limiter uses `X-Forwarded-For` without validating proxy trust

**File:** `backend/rate_limiter.py`; `backend/main.py`

**Description:**
`slowapi`'s `get_remote_address` reads `X-Forwarded-For` if present. `ProxyHeadersMiddleware` is only installed when `trusted_proxy_ips` is non-empty (default: empty). Without the middleware, an attacker can spoof any client IP via `X-Forwarded-For: 1.2.3.4` and completely bypass per-IP rate limits on all auth endpoints.

**Remediation:**
1. Use a custom `key_func` that only trusts `X-Forwarded-For` when `trusted_proxy_ips` is configured, otherwise use `request.client.host` directly.
2. Or add a startup check requiring `trusted_proxy_ips` in production (similar to `enforce_https`).

**References:** OWASP Rate Limiting Bypass; slowapi GitHub #103

---

### SEC-04 — Medium: Logout endpoint has no CSRF protection

**File:** `backend/user_routes.py`, `logout()` handler

**Description:**
`POST /auth/logout` relies on SameSite=Lax on the `access_token` cookie for CSRF protection. SameSite=Lax blocks cross-site POSTs from `fetch`/XHR but does not cover all browser form-POST scenarios. An attacker can force a user to log out (logout CSRF), which could be combined with session-fixation-adjacent attacks.

**Remediation:** Document this as an accepted trade-off, or add a lightweight CSRF double-submit cookie / per-session token for state-changing endpoints.

---

### SEC-05 — Medium: `delete_cookie()` on logout missing `secure=True`

**File:** `backend/user_routes.py`, lines 391–392

**Description:**
```python
response.delete_cookie("access_token", path="/")
response.delete_cookie("refresh_token", path="/auth/refresh")
```
RFC 6265 and strict browsers (Chrome, Firefox) require the `Secure` attribute on the deletion `Set-Cookie` header to match the original. Without `secure=True`, the deletion may be silently ignored on HTTPS, leaving the cookies active until natural expiry. The `jti` revocation provides a partial backstop for `access_token`, but `refresh_token` has no such fallback.

**Remediation:**
```python
response.delete_cookie("access_token", path="/", secure=True, samesite="lax")
response.delete_cookie("refresh_token", path="/auth/refresh", secure=True, samesite="strict")
```

---

### SEC-06 — Medium: No 401 interceptor — refresh token mechanism is orphaned

**File:** `frontend/src/api/client.ts`; `frontend/src/composables/useAuth.ts`

**Description:**
The refresh token endpoint (`POST /auth/refresh`) is implemented but no code path automatically calls it when the access token expires. `checkAuth()`'s `_checked` guard short-circuits after the first call, so a naturally expired access token leaves `isAuthenticated = true` (stale) while API calls return 401.

**Remediation:**
1. Add a 401 interceptor in `apiClient` that calls `/auth/refresh` once and retries the original request.
2. Or reset `_checked = false` on any 401 response so the next navigation re-checks auth state.

---

### SEC-07 — Low: Tokens without `jti` bypass revocation check silently

**File:** `backend/security.py`, revocation block

**Description:**
```python
jti: object = payload.get("jti")
if isinstance(jti, str):
    # revocation check
```
Tokens without a `jti` skip the Redis call entirely and are accepted. Tokens issued before this branch was deployed, or crafted tokens with no `jti`, are never checked for revocation.

**Remediation:** Reject tokens missing `jti` — treat absence as equivalent to revoked:
```python
if not isinstance(jti, str):
    raise credentials_error
```

---

### SEC-08 — Low: SameSite=Lax permits sending on top-level cross-site GET navigations

**File:** `backend/user_routes.py` (cookie attributes)

**Description:**
SameSite=Lax sends the cookie on `<a href>` navigations from third-party sites. Any future GET endpoint that mutates state and relies solely on the cookie for auth would be CSRF-vulnerable. Currently no such endpoints exist, but this is a maintenance risk.

**Remediation:** Document the posture. Enforce that GET endpoints must not mutate state via architecture review.

---

### SEC-09 — Low: `enforce_https=False` default risks silent HTTP production deployment

**File:** `backend/config.py:54`

See SEC-02. Recommend changing default to `True`.

---

### SEC-10 — Low: `_checked` singleton prevents re-auth after token expiry

**File:** `frontend/src/composables/useAuth.ts`

**Description:**
`_checked` is a module-level ref — once `true`, `checkAuth()` is a no-op for the lifetime of the page. Natural access token expiry (~30 min) does not reset it. Users experience 401 errors with no re-auth flow.

**Remediation:** Reset `_checked = false` on any 401 from the API client (pairs with SEC-06 fix).

---

### SEC-11 — Low: `logout()` clears local state even on server 5xx

**File:** `frontend/src/composables/useAuth.ts`

**Description:**
If `POST /auth/logout` returns 503 (Redis down), the frontend still clears `_user` and navigates to `/`. The access token cookie and `jti` revocation may not have been processed. Token expires naturally within `access_token_expire_minutes`.

**Remediation:** Check `response.ok` and show a user-visible error on 5xx; consider a retry.

---

### SEC-12 — Info: CORS `allow_methods=["*"]`

**File:** `backend/main.py`

**Remediation:** Use explicit list: `["GET", "POST", "PUT", "DELETE", "OPTIONS"]`

---

### SEC-13 — Info: CORS `allow_headers=["*"]`

**File:** `backend/main.py`

**Remediation:** Use explicit list: `["Content-Type"]` (Authorization header no longer needed with cookie auth).

---

### SEC-14 — Info: `WWW-Authenticate: Bearer` on cookie-auth 401 is misleading

**File:** `backend/security.py`

**Remediation:** Remove the `WWW-Authenticate` header, or change to `Cookie realm="protected"`.

---

### SEC-15 — Info: Redis singleton write-write race (accepted)

**File:** `backend/redis_client.py`

The comment correctly describes this as a benign race under CPython's GIL. Each worker process maintains its own connection pool singleton. No security implication. **Accepted.**

---

## Prioritised Remediation Plan

### Block merge
1. **SEC-01** — Atomise PKCE Redis writes with a pipeline
2. **SEC-03** — Fix rate limiter IP spoofing bypass

### Before production
3. **SEC-02 / SEC-09** — Change `enforce_https` default to `True`
4. **SEC-05** — Add `secure=True, samesite=` to `delete_cookie()` calls
5. **SEC-07** — Reject tokens missing `jti` at decode time

### Short-term backlog
6. **SEC-06 / SEC-10** — Implement 401 interceptor + reset `_checked` on expiry
7. **SEC-04** — Document or implement CSRF posture for logout
8. **SEC-11 / SEC-12 / SEC-13 / SEC-14** — Minor hardening cleanup

---

## What Is Well-Implemented

- **PKCE S256 derivation** — correct per RFC 7636 Appendix B
- **HttpOnly + Secure cookies** — both access and refresh tokens
- **Refresh token path-scoping** — `path="/auth/refresh"` correctly limits exposure
- **Refresh token rotation** — GETDEL atomicity prevents replay
- **Revocation fail-closed** — Redis unavailability raises 503, not 200
- **Log-before-raise** — `oauth.token.revoked` emitted before `credentials_error`
- **`jti` entropy** — `secrets.token_urlsafe(16)` = 128 bits
- **ExtraClaims runtime backstop** — `_ALLOWED_EXTRA_CLAIMS` frozenset as defence-in-depth
- **Startup guards** — Redis ping + HTTPS URL check
- **Rate limiter disabled in tests** — `RATELIMIT_ENABLED=false` via pytest-env is correct
- **Token exposure elimination** — URL fragment and localStorage removed
