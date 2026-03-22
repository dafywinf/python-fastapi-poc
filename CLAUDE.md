# Project Instructions

## Global Standards

@.claude/standards/GIT_STANDARDS.md
@.claude/standards/PYTHON_STANDARDS.md

## External Skills

- **Python:** `fullstack-dev-skills:python-pro` for general implementation
- **FastAPI:** `fullstack-dev-skills:fastapi-expert` for endpoint and schema work

## Tech Stack

- **Framework:** FastAPI (sync, threaded — use `def` not `async def`)
- **Python:** 3.12 via pyenv (`.python-version`)
- **Dependencies:** Poetry with in-project `.venv`
- **Database:** PostgreSQL via psycopg2-binary
- **ORM:** SQLAlchemy (synchronous sessions)
- **Migrations:** Alembic (`backend/models.py` is the source of truth)
- **Task runner:** `just` (see `justfile`)

## Architectural Rules

- **Sync-first:** Route handlers use `def` so FastAPI offloads them to its external thread pool, keeping the event loop free from blocking I/O.
- **Dependency injection:** `get_session` manages the SQLAlchemy session lifecycle (Unit of Work pattern). Override it in tests via `app.dependency_overrides`.
- **Real DB in tests:** Tests run against a real PostgreSQL container via `testcontainers` — no SQLite, no mocking the database layer.
- **Exception handling:** Decorate handlers with `@handle_exception(logger)` to ensure full tracebacks are captured via `logger.exception`.
- **Environment:** `.venv` must live inside the project directory (`poetry config virtualenvs.in-project true`).
- **Configuration:** All env config via `backend/config.py` (`pydantic-settings BaseSettings`) — never `os.environ` directly.

## Work Process

- **Task Tracking:** Always refer to `TASK_PLAN.md` for the current project state and upcoming phases.
- **Updates:** After completing a significant sub-task, update the relevant checkbox in `TASK_PLAN.md`.
- **Context:** Before starting a new phase, run `ls -R` to verify the filesystem matches the expected state in the plan.

## Project Structure

```
.
├── alembic/            # Migration environment & versions
├── backend/
│   ├── main.py         # App entry point & logging config
│   ├── config.py       # pydantic-settings — single source of env config
│   ├── models.py       # SQLAlchemy models (source of truth)
│   ├── schemas.py      # Pydantic V2 DTOs
│   ├── database.py     # Engine & session factory
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
