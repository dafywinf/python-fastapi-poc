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

- **Real database only** — tests run against a real PostgreSQL container via `testcontainers`. Never use SQLite or mock the database.
- Each test is wrapped in a transaction rolled back on teardown (`join_transaction_mode="create_savepoint"`); tests are fully isolated without truncation.
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
          # Precondition: just platform-up && just backend-dev must be running
```

Never invoke the underlying tools (`ruff`, `basedpyright`, `pytest`) directly — use `just` so the recipes stay in sync.

## Tooling

- **Dependency management:** Poetry (`poetry config virtualenvs.in-project true` — `.venv` lives inside the project).
- **Task runner:** `just` (see `justfile` for all recipes).
- **Static analysis:** basedpyright strict mode — zero errors required.

## Virtual Environment Execution

- **Do not use `source .venv/bin/activate`** — Claude Code runs each shell command in a fresh shell, so activation does not persist between tool calls.
- **Always invoke via `just`** or use the absolute venv path:

```bash
just ci                         # preferred — runs the full pre-PR suite
.venv/bin/pytest tests/         # fallback if running a subset directly
.venv/bin/basedpyright .
```
