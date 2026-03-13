# python-fastapi-poc

A FastAPI application for managing **Sequence** entities — synchronous, threaded architecture using FastAPI + SQLAlchemy + PostgreSQL + Alembic.

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

### 6. Start the database and run migrations

```bash
just bootstrap
```

This starts the PostgreSQL container and waits for it to be healthy before applying all Alembic migrations.

### 7. Start the development server

```bash
just dev
```

| URL | Description |
|-----|-------------|
| <http://localhost:8000/docs> | Interactive Swagger UI |
| <http://localhost:8000/redoc> | ReDoc documentation |
| <http://localhost:8000/health> | Liveness check |

---

## Running Tests

Tests use an in-memory SQLite database — no running PostgreSQL instance required.

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
| `just test` | Run the test suite |
| `just test-cov` | Run tests with a terminal coverage report |
| `just perf` | Run performance tests (event-loop blocking demo, requires Docker) |
| `just bootstrap` | Start the DB container and apply all migrations |
| `just migrate` | Apply pending Alembic migrations |
| `just makemigrations "message"` | Generate a new migration from model changes |
| `just db-up` | Start the PostgreSQL container |
| `just db-down` | Stop and remove the PostgreSQL container |
| `just db-logs` | Tail PostgreSQL container logs |

---

## API Endpoints

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `GET` | `/health` | `200` | Liveness check |
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
│   ├── main.py         # App entry point & logging config
│   ├── models.py       # SQLAlchemy models (source of truth)
│   ├── schemas.py      # Pydantic V2 DTOs
│   ├── database.py     # Engine & session factory
│   ├── routes.py       # API route handlers
│   ├── services.py     # Business logic
│   └── exceptions.py   # Exception handling decorator
├── tests/
│   ├── conftest.py     # Shared fixtures (in-memory DB, TestClient)
│   ├── test_health.py
│   ├── test_sequences.py
│   └── perf/           # Performance tests (excluded from just test)
├── .env                # Database credentials (not committed)
├── .python-version     # Python version for pyenv
├── alembic.ini         # Alembic configuration
├── docker-compose.yml  # PostgreSQL service
├── justfile            # Task runner commands
└── pyproject.toml      # Dependencies & tool configuration
```

---

## Further Reading

| Document | Description |
|----------|-------------|
| [Python Toolchain](docs/python-toolchain.md) | How pyenv, Poetry, `.venv`, and your IDE relate — including what each command writes to your machine |

---

## Architecture Notes

- **Sync-first**: Handlers use `def` (not `async def`) so FastAPI offloads them to its external thread pool, keeping the event loop free from blocking I/O.
- **Dependency injection**: `get_session` manages the SQLAlchemy session lifecycle (Unit of Work pattern) and is overridden in tests with an in-memory session.
- **Exception handling**: `@handle_exception(logger)` captures full tracebacks via `logger.exception`.
- **Migrations**: Alembic autogenerate — edit `backend/models.py`, then run `just makemigrations "describe change"` followed by `just migrate`.
