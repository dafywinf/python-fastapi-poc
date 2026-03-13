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
- **Dependency injection:** `get_session` manages the SQLAlchemy session lifecycle (Unit of Work pattern). Override it in tests — never hit a real DB in tests.
- **Exception handling:** Decorate handlers with `@handle_exception(logger)` to ensure full tracebacks are captured via `logger.exception`.
- **Environment:** `.venv` must live inside the project directory (`poetry config virtualenvs.in-project true`).

## Database Schema

Table: `sequences`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer | Primary key |
| `name` | String | Required |
| `description` | String | Nullable |
| `created_at` | DateTime | Server default `now()` |

## Project Structure

```
.
├── alembic/            # Migration environment & versions
├── backend/
│   ├── main.py         # App entry point & logging config
│   ├── models.py       # SQLAlchemy models (source of truth)
│   ├── schemas.py      # Pydantic V2 DTOs
│   ├── database.py     # Engine & session factory
│   ├── routes.py       # API route handlers (sync def)
│   ├── services.py     # Business logic
│   └── exceptions.py   # Exception handling decorator
├── tests/
│   ├── conftest.py     # Fixtures — in-memory SQLite, TestClient
│   ├── test_health.py
│   └── test_sequences.py
├── .env                # Database credentials (not committed)
├── .python-version     # pyenv version pin
├── alembic.ini
├── docker-compose.yml  # PostgreSQL service
├── justfile            # Task runner
└── pyproject.toml
```
