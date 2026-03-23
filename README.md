# python-fastapi-poc

A full-stack home automation routines application built as a reference project.
It combines a synchronous FastAPI backend, PostgreSQL, APScheduler-backed routine
execution, Google OAuth2 login, a Vue 3 SPA with PrimeVue + Tailwind, and a
layered testing setup spanning pytest, Vitest, and Playwright.

## Quick Start

### 1. Install local dependencies

```bash
brew install pyenv poetry just node
```

Docker Desktop must also be installed and running.

### 2. Install Python and backend dependencies

```bash
pyenv install $(cat .python-version)
poetry config virtualenvs.in-project true
poetry install
```

### 3. Install frontend dependencies

```bash
cd frontend && npm ci && cd ..
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Minimal local `.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sequences_db
JWT_SECRET_KEY=change-me-to-a-long-random-secret
ADMIN_PASSWORD_HASH=$2b$12$...
ENABLE_PASSWORD_AUTH=true
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
REDIS_URL=redis://localhost:6379/0
```

To enable Google OAuth2 login, also set:

```env
GOOGLE_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<your-client-secret>
```

See [docs/google-oauth-setup.md](docs/google-oauth-setup.md) for the full setup.

To enable Loki log shipping, set:

```env
LOKI_URL=http://localhost:3100
```

### 5. Start platform services and run migrations

```bash
just platform-up
just bootstrap
```

`platform-up` starts PostgreSQL, Redis, Prometheus, Loki, and Grafana.
`bootstrap` waits for PostgreSQL and applies Alembic migrations.

### 6. Start the app

```bash
just dev-up
```

Useful follow-up commands:

```bash
just dev-logs
just dev-down
```

## Local URLs

| URL | Description |
|-----|-------------|
| <http://localhost:5173> | Vue frontend |
| <http://localhost:8000/docs> | Swagger UI |
| <http://localhost:8000/redoc> | ReDoc |
| <http://localhost:8000/health> | Health check |
| <http://localhost:8000/metrics> | Prometheus metrics |
| <http://localhost:9090> | Prometheus |
| <http://localhost:3100/ready> | Loki readiness |
| <http://localhost:3000> | Grafana (`admin` / `admin`) |

## Running Tests

```bash
just backend-test
just backend-test-cov
just backend-perf
just frontend-test
just frontend-e2e
just frontend-check
just ci
```

Test reporting:

```bash
just backend-test-report
just frontend-test-report
just frontend-e2e-report
just report
just clean-reports
```

## Common Commands

| Command | Description |
|---------|-------------|
| `just dev-up` | Start backend + frontend in background |
| `just dev-down` | Stop backend + frontend |
| `just dev-logs` | Tail app logs |
| `just backend-dev` | Run FastAPI with reload |
| `just backend-check` | Ruff + format check + basedpyright |
| `just backend-test` | Run backend integration tests |
| `just backend-perf` | Run backend performance tests |
| `just backend-e2e` | Run observability E2E tests |
| `just frontend-dev` | Run Vite dev server |
| `just frontend-lint` | Run frontend ESLint |
| `just frontend-check` | Run frontend lint + build |
| `just frontend-test` | Run frontend Vitest suite |
| `just frontend-e2e` | Run frontend Playwright suite |
| `just platform-up` | Start PostgreSQL, Redis, and monitoring |
| `just platform-down` | Stop platform services |
| `just bootstrap` | Start DB and apply migrations |
| `just ci` | Full pre-PR gate |

## API Surface

### Core

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | — | Liveness check |
| `GET` | `/metrics` | — | Prometheus metrics |

### Auth and Users

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/auth/token` | — | Password grant for local dev/tests |
| `GET` | `/auth/google/login` | — | Start Google OAuth2 flow |
| `GET` | `/auth/google/callback` | — | Google callback; redirects to SPA with JWT fragment |
| `GET` | `/users/` | Bearer | List known users |
| `GET` | `/users/me` | Bearer | Current user profile |

### Routines

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/routines/` | — | List routines |
| `POST` | `/routines/` | Bearer | Create routine |
| `GET` | `/routines/{id}` | — | Get routine detail |
| `PUT` | `/routines/{id}` | Bearer | Update routine |
| `DELETE` | `/routines/{id}` | Bearer | Delete routine |
| `GET` | `/routines/{id}/actions` | — | List routine actions |
| `POST` | `/routines/{id}/actions` | Bearer | Create action inside a routine |
| `POST` | `/routines/{id}/run` | Bearer | Trigger immediate execution |

### Actions and Executions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `PUT` | `/actions/{id}` | Bearer | Update action |
| `DELETE` | `/actions/{id}` | Bearer | Delete action |
| `GET` | `/executions/active` | — | List currently running executions |
| `GET` | `/executions/history` | — | List recent execution history |

## Authentication

The app supports two auth paths:

- Google OAuth2 is the primary browser login flow.
- `POST /auth/token` exists for local development, automation, and Playwright.

Example password-grant flow:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -d "username=admin&password=<your-password>" | jq -r .access_token)

curl -X POST http://localhost:8000/routines/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Morning Lights","schedule_type":"manual","is_active":true}'
```

## Project Structure

```text
.
├── alembic/
├── backend/
│   ├── main.py
│   ├── auth_routes.py
│   ├── user_routes.py
│   ├── routine_routes.py
│   ├── routine_services.py
│   ├── execution_engine.py
│   ├── scheduler.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   ├── security.py
│   ├── google_oauth.py
│   └── redis_client.py
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── features/
│   │   ├── stores/
│   │   ├── views/
│   │   ├── components/
│   │   ├── test/
│   │   └── __tests__/
│   ├── e2e/
│   └── package.json
├── tests/
│   ├── test_auth.py
│   ├── test_google_oauth.py
│   ├── test_health.py
│   ├── test_metrics.py
│   ├── test_routines.py
│   ├── test_users.py
│   ├── e2e/
│   └── perf/
├── monitoring/
├── docs/
├── scripts/
├── docker-compose.yml
├── justfile
└── pyproject.toml
```

## Further Reading

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | System architecture and major design decisions |
| [docs/frontend.md](docs/frontend.md) | Frontend architecture, routes, and test setup |
| [docs/how-to-add-a-crud-feature.md](docs/how-to-add-a-crud-feature.md) | Repo-specific guide for adding a new CRUD feature end to end |
| [docs/testing.md](docs/testing.md) | Test strategy and pyramid |
| [docs/google-oauth-setup.md](docs/google-oauth-setup.md) | Google OAuth2 setup and troubleshooting |
| [docs/python-toolchain.md](docs/python-toolchain.md) | Python, Poetry, and IDE tooling |

## Architecture Notes

- Sync FastAPI handlers are used intentionally so blocking DB work runs in FastAPI's thread pool instead of on the event loop.
- Backend updates now preserve scheduler invariants transactionally; invalid routine state is rejected before commit.
- Routine execution is launched through an explicit execution boundary in `backend/execution_engine.py`, not route-level ad hoc thread creation.
- The frontend uses PrimeVue in unstyled mode, Tailwind CSS, Pinia for auth state, and TanStack Query for server-state management.
- Frontend contract tests use generated OpenAPI types plus MSW, so most UI behavior is tested below the browser layer.
- Playwright remains intentionally light and smoke-oriented; the repo follows a test pyramid with a somewhat thick middle.
