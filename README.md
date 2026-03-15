# python-fastapi-poc

A full-stack sequence management application — synchronous FastAPI backend with SQLAlchemy + PostgreSQL + Alembic, a Vue 3 + TypeScript SPA frontend, and a full Prometheus + Loki + Grafana observability stack.

---

## Quick Start

### 1. Install system dependencies (macOS)

```bash
brew install pyenv poetry just node
```

Docker Desktop must also be installed and running.

### 2. Install the correct Python version

```bash
pyenv install $(cat .python-version)
```

### 3. Configure Poetry to create the virtualenv inside the project

```bash
poetry config virtualenvs.in-project true
```

### 4. Install backend dependencies

```bash
poetry install
```

### 5. Install frontend dependencies

```bash
cd frontend && npm ci && cd ..
```

### 6. Configure environment variables

The `.env` file is pre-configured for the Docker Compose database. A minimal `.env` looks like:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sequences_db
JWT_SECRET_KEY=change-me-to-a-long-random-secret
ADMIN_PASSWORD_HASH=$2b$12$...  # generate with: python -c "import bcrypt; print(bcrypt.hashpw(b'your-password', bcrypt.gensalt()).decode())"
```

To enable Loki log shipping, uncomment `LOKI_URL` in `.env` **after** starting the monitoring stack:

```env
LOKI_URL=http://localhost:3100
```

Leave `LOKI_URL` unset (the default) to disable log shipping — the app and all tests start cleanly without it.

### 7. Start all platform services and run migrations

```bash
just platform-up
just bootstrap
```

`platform-up` starts PostgreSQL, Prometheus, Loki, and Grafana. `bootstrap` waits for the database to be healthy then applies all Alembic migrations.

### 8. Start the full development stack

```bash
just dev-up
```

This starts the backend (port 8000) and frontend (port 5173) in the background and confirms both are healthy. Logs are written to `/tmp/backend.log` and `/tmp/frontend.log`.

```bash
just dev-logs   # tail both logs (Ctrl-C to stop)
just dev-down   # stop backend + frontend
```

| URL | Description |
|-----|-------------|
| <http://localhost:5173> | **Vue 3 SPA — main UI** |
| <http://localhost:8000/docs> | Interactive Swagger UI |
| <http://localhost:8000/redoc> | ReDoc documentation |
| <http://localhost:8000/health> | Liveness check |
| <http://localhost:8000/metrics> | Prometheus metrics |
| <http://localhost:9090> | Prometheus |
| <http://localhost:3100/ready> | Loki readiness check |
| <http://localhost:3000> | Grafana (admin / admin) |

---

## Running Tests

```bash
# Backend integration tests (real PostgreSQL via testcontainers)
just backend-test

# Backend tests with coverage report
just backend-test-cov

# Performance tests (event-loop blocking demo, ~20s, requires Docker)
just backend-perf

# Frontend Vitest unit + component tests (jsdom, mocked API — no backend needed)
just frontend-test

# Frontend Playwright E2E tests (real Chromium + real backend — requires just dev-up)
just frontend-e2e

# TypeScript type-check + build (frontend)
just frontend-check

# Full pre-PR gate — all of the above
just ci
```

### Allure Reports

```bash
# Run everything then open a single combined report (requires platform-up + dev-up)
just report

# Per-suite reports (uses results already on disk from the last run)
just backend-test-report    # backend integration + perf + obs E2E
just frontend-test-report   # Vitest unit/component
just frontend-e2e-report    # Playwright browser E2E

# Clear all results directories without running tests
just clean-reports
```

---

## All Commands

| Command | Description |
|---------|-------------|
| `just dev-up` | Start backend + frontend in background; confirms both healthy |
| `just dev-down` | Stop backend + frontend |
| `just dev-logs` | Tail `/tmp/backend.log` and `/tmp/frontend.log` |
| `just backend-dev` | Start the FastAPI backend only (foreground) |
| `just backend-dev-stop` | Stop the FastAPI backend |
| `just backend-check` | Ruff lint + basedpyright type-check |
| `just backend-test` | Run the backend integration test suite |
| `just backend-test-cov` | Run backend tests with a terminal coverage report |
| `just backend-perf` | Run performance tests (event-loop blocking demo, requires Docker) |
| `just frontend-dev` | Start the Vite frontend dev server (port 5173) |
| `just frontend-dev-stop` | Stop the Vite dev server |
| `just frontend-check` | TypeScript type-check + production build |
| `just frontend-test` | Run frontend Vitest unit/component tests with Allure results |
| `just frontend-e2e-install` | Install Playwright Chromium browser binary (run once) |
| `just frontend-e2e` | Run Playwright browser E2E tests (requires `just dev-up`) |
| `just backend-test-report` | Run backend tests and open Allure report |
| `just frontend-test-report` | Run Vitest tests and open Allure report |
| `just frontend-e2e-report` | Run Playwright tests and open Allure report (requires `just dev-up`) |
| `just report` | Clean results, run all tests, open combined Allure report (requires platform-up + dev-up) |
| `just clean-reports` | Delete all Allure results directories |
| `just platform-up` | Start all platform services (DB + monitoring stack) |
| `just platform-down` | Stop all platform services |
| `just obs-up` | Start Prometheus, Loki, and Grafana only |
| `just obs-down` | Stop Prometheus, Loki, and Grafana |
| `just obs-logs` | Tail all monitoring container logs |
| `just loki-logs` | Tail Loki container logs only |
| `just bootstrap` | Start the DB container and apply all migrations |
| `just migrate` | Apply pending Alembic migrations |
| `just makemigrations "message"` | Generate a new migration from model changes |
| `just db-up` | Start the PostgreSQL container |
| `just db-down` | Stop and remove all containers |
| `just db-logs` | Tail PostgreSQL container logs |
| `just ci` | Full pre-PR gate: all checks + all tests (requires platform-up + backend-dev) |

---

## API Endpoints

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| `GET` | `/health` | — | `200` | Liveness check |
| `GET` | `/metrics` | — | `200` | Prometheus metrics |
| `POST` | `/auth/token` | — | `200` / `401` | Obtain a JWT access token |
| `POST` | `/sequences/` | Bearer | `201` / `401` | Create a new Sequence |
| `GET` | `/sequences/` | — | `200` | List all Sequences (public) |
| `GET` | `/sequences/{id}` | — | `200` / `404` | Retrieve a Sequence by ID (public) |
| `PATCH` | `/sequences/{id}` | Bearer | `200` / `401` / `404` | Partially update a Sequence |
| `DELETE` | `/sequences/{id}` | Bearer | `204` / `401` / `404` | Delete a Sequence |

### Authentication

The API uses **OAuth2 Password Bearer** tokens. Obtain a token then include it in write requests:

```bash
# 1. Get a token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -d "username=admin&password=<your-password>" | jq -r .access_token)

# 2. Use the token for write operations
curl -X POST http://localhost:8000/sequences/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Sequence", "description": "optional"}'
```

Read operations (`GET`) are public and do not require a token.

---

## Project Structure

```
.
├── alembic/            # Migration environment & versions
├── backend/
│   ├── main.py         # App entry point, logging config & metrics instrumentation
│   ├── config.py       # pydantic-settings — single source of env config
│   ├── models.py       # SQLAlchemy models (source of truth)
│   ├── schemas.py      # Pydantic V2 DTOs
│   ├── database.py     # Engine & session factory
│   ├── routes.py       # API route handlers (sync def)
│   ├── services.py     # Business logic
│   ├── security.py     # JWT helpers, OAuth2 dependency providers (WriteDep)
│   ├── auth_routes.py  # POST /auth/token — OAuth2 password grant
│   └── exceptions.py   # Exception handling decorator
├── frontend/
│   ├── src/
│   │   ├── api/        # Fetch-based API client (proxied to port 8000)
│   │   ├── types/      # TypeScript DTOs matching backend schemas
│   │   ├── views/      # SequenceListView, SequenceDetailView
│   │   ├── components/ # AppNavbar, AppSidebar
│   │   └── __tests__/  # Vitest unit + component tests (jsdom, mocked API)
│   ├── e2e/            # Playwright browser E2E tests (real Chromium + real backend)
│   │   ├── pages/      # Page Object Model (SequenceListPage, dialogs, …)
│   │   ├── sequences.list.spec.ts
│   │   ├── sequences.crud.spec.ts
│   │   └── sequences.detail.spec.ts
│   ├── playwright.config.ts  # Chromium, allure reporter, webServer block
│   ├── vite.config.ts        # Proxy /sequences → localhost:8000 (with HTML bypass)
│   └── vitest.config.ts
├── monitoring/
│   ├── prometheus/
│   │   └── prometheus.yml          # Scrape config (targets host:8000)
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/        # Auto-provisions Prometheus datasource
│       │   └── dashboards/         # Points Grafana at dashboard JSON dir
│       └── dashboards/
│           ├── fastapi.json        # FastAPI Observability dashboard (RED metrics)
│           └── loki.json           # FastAPI Logs dashboard (LogQL)
├── tests/
│   ├── conftest.py     # Fixtures — testcontainers PostgreSQL, savepoint isolation, TestClient
│   ├── test_health.py
│   ├── test_metrics.py
│   ├── test_sequences.py
│   └── perf/           # Performance tests (marked perf, excluded from default run)
│       ├── helpers.py
│       ├── test_event_loop_blocking.py
│       └── test_db_event_loop_blocking.py
├── docs/
│   ├── architecture.md # System architecture and key decisions
│   └── frontend.md     # Frontend architecture, tech stack, test guide
├── .env                # Database credentials (not committed)
├── .python-version     # pyenv version pin
├── alembic.ini
├── docker-compose.yml  # PostgreSQL, Prometheus, Loki, Grafana (monitoring profile)
├── justfile            # Task runner — use `just ci` as pre-PR gate
└── pyproject.toml
```

---

## Further Reading

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System architecture, key decisions, C4 diagrams |
| [Frontend](docs/frontend.md) | SPA architecture, tech stack, Playwright E2E guide |
| [Testing Strategy](docs/testing.md) | All test layers — philosophy, data strategy, Allure, CI mapping |
| [Python Toolchain](docs/python-toolchain.md) | How pyenv, Poetry, `.venv`, and your IDE relate |

---

## Architecture Notes

- **Sync-first**: Handlers use `def` (not `async def`) so FastAPI offloads them to its external thread pool, keeping the event loop free from blocking I/O.
- **Dependency injection**: `get_session` manages the SQLAlchemy session lifecycle (Unit of Work pattern). Overridden in tests via `app.dependency_overrides`.
- **Real DB in tests**: Tests run against a real PostgreSQL container via `testcontainers` — no SQLite, no mocking the database layer.
- **Exception handling**: `@handle_exception(logger)` captures full tracebacks via `logger.exception`.
- **Migrations**: Alembic autogenerate — edit `backend/models.py`, then run `just makemigrations "describe change"` followed by `just migrate`.
- **Observability**: `prometheus-fastapi-instrumentator` exposes RED metrics at `/metrics`. Prometheus scrapes every 15s; the FastAPI Observability dashboard is pre-provisioned. Structured JSON logs are shipped directly to Loki via `python-logging-loki` and queryable in the FastAPI Logs Grafana dashboard.
- **Frontend**: Vite dev server proxies `/sequences` and `/health` to the backend at port 8000, so both run independently and no CORS config is needed in development.
- **Authentication**: JWT Bearer tokens via `python-jose` (HS256). Write endpoints (`POST`/`PATCH`/`DELETE`) require a valid token; `GET` endpoints are public. Credentials are config-driven (`JWT_SECRET_KEY`, `ADMIN_PASSWORD_HASH`) — no database user table in the MVP.
