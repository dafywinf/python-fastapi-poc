# Reference Architecture Review

Date: 2026-03-24

## Verdict

This repository is strong as a teaching/demo project and is notably better than
the average CRUD sample: it has real database tests, useful docs, strict
backend typing, a frontend contract flow, and deliberate architectural choices.

It is not yet a high-quality reference architecture in the stricter sense of
"safe to copy as a default starting point for production-minded teams." The
main gaps are around failure semantics, identity consistency, runtime job
execution durability, and a few places where the implementation falls short of
the repo's own architectural standards.

## What is already strong

- The backend layering is readable and mostly well-enforced.
- The test strategy is thoughtful and substantially better than the typical
  sample app. The sync-vs-async performance tests are especially valuable.
- The frontend structure has improved beyond page-local state into a clearer
  feature/query/mutation split.
- Documentation quality is high enough that a reader can understand the intent
  of the system without reverse-engineering the code.
- The repo uses real tools instead of toy substitutes: PostgreSQL,
  migrations, Redis for OAuth state, and generated frontend API types.

## Findings

### 1. High: routine creation is not failure-atomic with scheduler registration

`create_routine()` commits the database row before scheduler registration is
attempted, so a scheduler failure leaves persisted state behind even though the
request fails. This is the exact class of inconsistency the update path already
works hard to avoid.

Evidence:

- `backend/routine_services.py:87-92` commits first, then calls
  `register_routine()`.
- `backend/routine_services.py:108-188` contains rollback/restore logic for
  updates, which makes the missing equivalent on create stand out.
- `tests/test_routines.py:420-432` covers rollback only for update, not create.

Why it matters:

- A caller can receive a 500 while the routine still exists in the database.
- The repo documents transaction-safe scheduler coordination as a key design
  property, but create currently violates that property.

### 2. High: feature-gated auth configuration does not fail fast

Password auth can be enabled with an empty `ADMIN_PASSWORD_HASH`, and the login
path then falls through to `bcrypt.checkpw()` with invalid input, which raises a
runtime `ValueError` instead of producing a startup error or a controlled 4xx/5xx.

Evidence:

- `backend/config.py:38-45` allows `admin_password_hash` to default to `""`.
- `backend/auth_routes.py:41-42` always calls `verify_password(...)`.
- `backend/security.py:20-34` passes the hash directly into `bcrypt.checkpw(...)`.
- Local verification: `.venv/bin/python -c "import bcrypt; print(bcrypt.checkpw(b'test', b''))"`
  raises `ValueError: Invalid salt`.

Why it matters:

- Reference architectures should fail fast on invalid configuration.
- This is a sharp edge for local setup, CI variants, and future deployments.

### 3. Medium: the identity model is inconsistent across auth mechanisms

Google login issues JWTs whose `sub` is the user's email, while password auth
issues JWTs whose `sub` is the admin username. The rest of the app describes
and consumes `sub` as an email-backed identity.

Evidence:

- `backend/security.py:62` documents `sub` as the authenticated user's email.
- `backend/user_routes.py:33-50` resolves the current user by `User.email`.
- `backend/user_routes.py:154-156` issues Google JWTs with `subject=user_info.email`.
- `backend/auth_routes.py:49` issues password JWTs with `subject=form_data.username`.
- `tests/test_users.py:272-299` works around this by seeding a `User` row whose
  email is literally `"admin"`.

Why it matters:

- The model is internally inconsistent even if the current tests pass.
- Readers copying this pattern will inherit a muddled principal model.
- `/users/me` semantics depend on test-only conventions rather than a clean,
  single definition of identity.

### 4. Medium: background execution is process-local and not durable enough for a reference architecture

Scheduled jobs and routine runs live inside the API process via APScheduler and
daemon threads. That is acceptable for a demo, but weak as a reference default.

Evidence:

- `backend/scheduler.py:21` creates an in-process `BackgroundScheduler`.
- `backend/scheduler.py:64-69` schedules jobs directly into that process.
- `backend/execution_engine.py:173-205` launches work in daemon threads.

Why it matters:

- In-flight work can disappear on process restart.
- Horizontal scaling produces awkward semantics because each process owns its
  own scheduler and tries to trigger the same jobs.
- There is no durable queue, lease, retry policy, or worker isolation boundary.

This does not make the repo "bad"; it just means it is still a POC-style
runtime architecture rather than a reference implementation for job execution.

### 5. Medium: routines listing will degrade with N+1 queries

The routines list endpoint returns nested actions, but `list_routines()` loads
only `Routine` rows. Serializing each routine's `actions` then lazily loads the
relationship one routine at a time.

Evidence:

- `backend/routine_services.py:56-67` selects `Routine` without
  `selectinload()`/`joinedload()`.
- The response model includes nested actions in `backend/schemas.py`.

Why it matters:

- It is a hidden performance footgun in exactly the kind of code readers are
  likely to copy.
- Reference code should model efficient data access patterns, not just
  functionally correct ones.

### 6. Medium: the frontend sends expired tokens on every request

The auth store can correctly compute that a token is expired, but the API client
still injects the raw token from storage into requests.

Evidence:

- `frontend/src/stores/auth.ts:37-42` computes `isAuthenticated` from `exp`.
- `frontend/src/stores/auth.ts:64-66` hydrates any stored token as-is.
- `frontend/src/api/client.ts:19-33` injects `Authorization` whenever
  `accessToken` exists, without checking `isAuthenticated`.

Why it matters:

- Expired sessions continue to generate avoidable 401 traffic.
- The client never self-heals by clearing invalid auth state.
- As reference code, this teaches "token presence" instead of "token validity."

## Overall assessment

If the bar is "good example project," this repo already qualifies.

If the bar is "reference architecture and implementation," I would currently
rate it as close but not there yet. The core design is solid, but reference
status requires stronger guarantees around config validation, identity
consistency, runtime durability, and failure-atomic workflows.

## Recommended next steps

1. Make routine creation scheduler-safe in the same way routine updates already
   are.
2. Add startup validation for feature-gated settings, especially password auth
   and Google OAuth.
3. Normalize identity semantics so every JWT `sub` means the same thing.
4. Decide whether the repo wants to remain a deliberate single-process demo or
   become a stronger production reference; if the latter, move execution onto a
   durable worker boundary.
5. Eager-load nested routine actions in list endpoints.
6. Clear or ignore expired frontend tokens before attaching auth headers.

## Verification notes

I ran the repo quality gates during this review.

- `just ci` reached and passed:
  backend lint/type checks, frontend lint/build, backend integration tests
  (`91 passed`), and backend performance tests (`6 passed`).
- `just ci` then failed in backend observability E2E because the monitoring
  stack was reachable but the FastAPI app was not listening on
  `http://localhost:8000`, which the E2E tests require.
- Evidence in `tests/e2e/test_observability_stack.py:3-10` already states that
  the live app must be running before those tests execute.

That means the findings above are based on successful static checks, passing
integration/perf coverage, direct code inspection, and the partial live-stack
verification that was possible in the current environment.
