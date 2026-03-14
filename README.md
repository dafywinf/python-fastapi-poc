# python-fastapi-poc

A FastAPI application for managing **Sequence** entities — synchronous, threaded architecture using FastAPI + SQLAlchemy + PostgreSQL + Alembic, with Prometheus + Grafana observability.

---

## Quick Start

### 1. Install system dependencies (macOS)

```bash
brew install pyenv poetry just
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

### 4. Install project dependencies

```bash
poetry install
```

### 5. Configure environment variables

The `.env` file is pre-configured for the Docker Compose database:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sequences_db
```

Edit `.env` if you need different credentials or a remote host.

### 6. Start all platform services and run migrations

```bash
just platform-up
just bootstrap
```

`platform-up` starts PostgreSQL, Prometheus, and Grafana. `bootstrap` waits for the database to be healthy then applies all Alembic migrations.

### 7. Start the development server

```bash
just dev
```

| URL | Description |
|-----|-------------|
| <http://localhost:8000/docs> | Interactive Swagger UI |
| <http://localhost:8000/redoc> | ReDoc documentation |
| <http://localhost:8000/health> | Liveness check |
| <http://localhost:8000/metrics> | Prometheus metrics |
| <http://localhost:9090> | Prometheus |
| <http://localhost:3000> | Grafana (anonymous viewer, no login) |

---

## Running Tests

Tests run against a real PostgreSQL container via `testcontainers` — no SQLite, no mocking.

```bash
# Run the full test suite
just test

# Run with a coverage report
just test-cov

# Run performance tests (binds real ports, takes ~20s, requires Docker)
just perf
```

---

## All Commands

| Command | Description |
|---------|-------------|
| `just dev` | Start the development server with hot-reload |
| `just platform-up` | Start all platform services (DB + Prometheus + Grafana) |
| `just platform-down` | Stop all platform services |
| `just obs-up` | Start Prometheus and Grafana only |
| `just obs-down` | Stop Prometheus and Grafana |
| `just obs-logs` | Tail monitoring container logs |
| `just test` | Run the test suite |
| `just test-cov` | Run tests with a terminal coverage report |
| `just perf` | Run performance tests (event-loop blocking demo, requires Docker) |
| `just bootstrap` | Start the DB container and apply all migrations |
| `just migrate` | Apply pending Alembic migrations |
| `just makemigrations "message"` | Generate a new migration from model changes |
| `just db-up` | Start the PostgreSQL container |
| `just db-down` | Stop and remove all containers |
| `just db-logs` | Tail PostgreSQL container logs |
| `just ci` | Full pre-PR gate: lint + type-check + tests + perf |

---

## API Endpoints

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `GET` | `/health` | `200` | Liveness check |
| `GET` | `/metrics` | `200` | Prometheus metrics |
| `POST` | `/sequences/` | `201` | Create a new Sequence |
| `GET` | `/sequences/` | `200` | List all Sequences |
| `GET` | `/sequences/{id}` | `200` / `404` | Retrieve a Sequence by ID |
| `PATCH` | `/sequences/{id}` | `200` / `404` | Partially update a Sequence |
| `DELETE` | `/sequences/{id}` | `204` / `404` | Delete a Sequence |

### Example: create a Sequence

```bash
curl -X POST http://localhost:8000/sequences/ \
  -H "Content-Type: application/json" \
  -d '{"name": "My Sequence", "description": "optional"}'
```

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
│   └── exceptions.py   # Exception handling decorator
├── monitoring/
│   ├── prometheus/
│   │   └── prometheus.yml          # Scrape config (targets host:8000)
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/        # Auto-provisions Prometheus datasource
│       │   └── dashboards/         # Points Grafana at dashboard JSON dir
│       └── dashboards/
│           └── fastapi.json        # FastAPI Observability dashboard (ID 16110)
├── tests/
│   ├── conftest.py     # Fixtures — testcontainers PostgreSQL, savepoint isolation, TestClient
│   ├── test_health.py
│   ├── test_metrics.py
│   ├── test_sequences.py
│   └── perf/           # Performance tests (marked perf, excluded from default run)
│       ├── helpers.py
│       ├── test_event_loop_blocking.py
│       └── test_db_event_loop_blocking.py
├── .env                # Database credentials (not committed)
├── .python-version     # pyenv version pin
├── alembic.ini
├── docker-compose.yml  # PostgreSQL, Prometheus, Grafana (monitoring profile)
├── justfile            # Task runner — use `just ci` as pre-PR gate
└── pyproject.toml
```

---

## Further Reading

| Document | Description |
|----------|-------------|
| [Python Toolchain](docs/python-toolchain.md) | How pyenv, Poetry, `.venv`, and your IDE relate — including what each command writes to your machine |

---

## Architecture Notes

- **Sync-first**: Handlers use `def` (not `async def`) so FastAPI offloads them to its external thread pool, keeping the event loop free from blocking I/O.
- **Dependency injection**: `get_session` manages the SQLAlchemy session lifecycle (Unit of Work pattern). Overridden in tests via `app.dependency_overrides`.
- **Real DB in tests**: Tests run against a real PostgreSQL container via `testcontainers` — no SQLite, no mocking the database layer.
- **Exception handling**: `@handle_exception(logger)` captures full tracebacks via `logger.exception`.
- **Migrations**: Alembic autogenerate — edit `backend/models.py`, then run `just makemigrations "describe change"` followed by `just migrate`.
- **Observability**: `prometheus-fastapi-instrumentator` exposes RED metrics at `/metrics`. Prometheus scrapes every 15s; the FastAPI Observability Grafana dashboard (ID 16110) is pre-provisioned.
