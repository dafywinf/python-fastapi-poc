# Python Development Standards

## Style & Formatting

- Formatter/Linter: Ruff (88 chars line length).
- Naming: `snake_case` for functions/variables, `PascalCase` for classes.
- Documentation: Google-style docstrings on all public functions and classes.

## Type Hinting (Mandatory)

- No `Any`. Use explicit types for all parameters and return values.
- Use `ParamSpec` + `TypeVar` (not `TypeVar F` bound to `Callable[..., Any]`) when writing typed decorators — preserves the wrapped function's full signature.
- Use Pydantic V2 for all data validation and DTO schemas.
- Use `pydantic-settings` (`BaseSettings`) for environment configuration — never read from `os.environ` directly.

## Library Choices

| Concern | Library | Notes |
|---------|---------|-------|
| Web framework | `fastapi ^0.115` | Sync handlers (`def`, not `async def`) |
| ASGI server | `uvicorn[standard]` | `[standard]` enables uvloop + httptools |
| ORM | `sqlalchemy ^2.0` | Synchronous sessions; use `select()` not legacy `.query()` |
| Migrations | `alembic ^1.14` | `backend/models.py` is source of truth |
| DB driver | `psycopg2-binary` | Sync driver — correct for sync architecture |
| Validation | `pydantic ^2.10` | V2 only; `ConfigDict(from_attributes=True)` for ORM models |
| Config | `pydantic-settings ^2.6` | `BaseSettings` with `env_file=".env"` |
| Linter | `ruff ^0.8` | Replaces flake8 + isort + black |
| Type checker | `basedpyright ^1.38` | Strict mode; replaces mypy |
| Test runner | `pytest ^8.3` | |
| Coverage | `pytest-cov ^6.0` | Minimum 80% for new features |
| HTTP client | `httpx ^0.28` | Used by FastAPI TestClient |
| Test reporting | `allure-pytest ^2.13` | Reports locally via `just backend-test-report` |
| Integration DB | `testcontainers[postgres] ^4.14` | Real PostgreSQL in tests — no mocking, no SQLite |

## SQLAlchemy 2.0 Patterns

- Use `Mapped` and `mapped_column` for model definitions.
- Use `select()` for queries — **never** the legacy `.query()` API.
- Use `session.get(Model, pk)` for primary key lookups.
- Use `session.refresh(instance)` after `commit()` to reload server-generated fields.

```python
# Correct
from sqlalchemy import select
results = list(session.execute(select(Sequence).order_by(Sequence.created_at.desc())).scalars())
instance = session.get(Sequence, sequence_id)

# Wrong — legacy API
session.query(Sequence).filter_by(id=sequence_id).first()
```

## FastAPI Patterns

- Route handlers must use `def` (not `async def`) so FastAPI offloads them to the thread pool.
- Use `Annotated` + `Depends` for all dependency injection.
- Extract repeated lookups (e.g. fetch-or-404) into a named dependency — do not repeat the pattern inline across handlers.
- Decorate all handlers with `@handle_exception(logger)` from `backend/exceptions.py`.

```python
# 404 dependency pattern
def _get_sequence_or_404(sequence_id: int, session: SessionDep) -> Sequence:
    sequence = get_sequence(session, sequence_id)
    if sequence is None:
        raise HTTPException(status_code=404, detail=f"Sequence {sequence_id} not found")
    return sequence

SequenceDep = Annotated[Sequence, Depends(_get_sequence_or_404)]
```

## Configuration

- All settings live in `backend/config.py` as a `BaseSettings` subclass.
- The singleton `settings` object is imported wherever config is needed.
- `alembic/env.py` must prefer `os.environ.get("DATABASE_URL")` over `settings.database_url` so that testcontainers can override the URL at test time.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()  # pyright: ignore[reportCallIssue]
```

## Testing (Pytest + Allure + Testcontainers)

The test suite follows the testing pyramid with two layers:

- **`tests/unit/`** — No database. Tests pure logic, schemas, auth helpers, OAuth utilities. Safe to run anywhere including the devcontainer. Run with `just backend-test-fast`.
- **`tests/integration/`** — Requires PostgreSQL via `testcontainers`. Tests endpoints, CRUD, migrations, and DB constraints. **Host only** — no Docker socket inside the devcontainer. Run with `just backend-test`.

Rules:
- **Real database for integration tests** — never SQLite, never mocked sessions for tests in `tests/integration/`.
- Place new tests in the correct folder — no explicit marker needed, the path determines the layer.
- Each integration test is wrapped in a transaction rolled back on teardown (`join_transaction_mode="create_savepoint"`); tests are fully isolated without truncation.
- All test classes must be decorated with `@allure.feature` and `@allure.story` at the **class level** (applies to all methods).
- Use `allure.step` context managers for complex multi-step assertions.
- Performance tests live in `tests/perf/`, are marked `@pytest.mark.perf`, and are excluded from the default `pytest` run.

```python
@allure.feature("Sequences")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Create")       # pyright: ignore[reportUnknownMemberType]
class TestCreateSequence:
    def test_creates_sequence_with_all_fields(self, client: TestClient) -> None:
        ...
```

## Pre-PR Gate

Run **one command** before every commit and before raising a PR:

```bash
just ci   # ruff + basedpyright + pytest (unit/integration with allure) + perf tests + e2e tests (with allure)
```

Preconditions for `just ci`:
- Run on the **host** (not inside the devcontainer) — testcontainers needs Docker
- `just platform-up` must be running (PostgreSQL, Prometheus, Grafana)
- `just dev-up` must be running (backend + frontend — required for e2e tests)

Never invoke the underlying tools (`ruff`, `basedpyright`, `pytest`) directly — use `just` so the recipes stay in sync.

## Tooling

- **Dependency management:** Poetry. Venv location is context-dependent:
  - **Host (macOS):** `POETRY_VIRTUALENVS_IN_PROJECT=true` → `.venv/` in project root
  - **Devcontainer (Linux):** `POETRY_VIRTUALENVS_IN_PROJECT=false` → venv in Poetry cache, `.venv/` does NOT exist
- **Task runner:** `just` (see `justfile` for all recipes).
- **Static analysis:** basedpyright strict mode — zero errors required.

## Virtual Environment Execution

Always use `just` recipes — never call `.venv/bin/pytest` or `.venv/bin/basedpyright` directly. The `.venv/` directory does not exist inside the devcontainer (venv is in Poetry cache there), so direct `.venv/bin/*` calls will fail in that context. Using `just` works correctly in both environments.

```bash
just ci                    # full pre-PR suite
just backend-test          # backend tests only
just backend-check         # lint + type check only
```

Do not use `source .venv/bin/activate` — Claude Code runs each shell command in a fresh shell, so activation does not persist.
