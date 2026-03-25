# Project Instructions

## Execution Context

**Check `DEVCONTAINER` before doing anything.**

If `DEVCONTAINER=true`, you are inside the Claude Code isolation container.
This context has **no Docker** — not a configuration choice, but a deliberate
architectural decision after Docker-in-container support proved unreliable.

| Inside devcontainer (`DEVCONTAINER=true`) | On the host |
|---|---|
| `just container-ci` ✓ — **use this** | `just ci` ✓ |
| `just backend-check` ✓ | `just backend-test` ✓ |
| `just backend-test-fast` ✓ | All suites ✓ |
| `just frontend-check` ✓ | |
| `just frontend-test` ✓ | |
| `just backend-test` ✗ — will fail | |
| `just ci` ✗ — will fail | |
| Any `docker` command ✗ — not installed | |

**If you are in the devcontainer and hit a test failure that requires the integration
suite, stop and tell the user to run `just backend-test` from a host terminal.
Do not attempt to work around the Docker constraint.**

The devcontainer is optimised for Claude Code autonomous operation — linting,
type checking, unit tests, and code editing are all fully supported.
See `docs/devcontainer-security.md` for the full architecture and rationale.

---

## Global Standards

@.claude/standards/GIT_STANDARDS.md
@.claude/standards/PYTHON_STANDARDS.md

## External Skills

- **Python:** `fullstack-dev-skills:python-pro` for general implementation
- **FastAPI:** `fullstack-dev-skills:fastapi-expert` for endpoint and schema work

## Tech Stack

- **Framework:** FastAPI (sync, threaded — use `def` not `async def`)
- **Python:** 3.12 via pyenv (`.python-version`)
- **Dependencies:** Poetry (venv location is context-dependent — see Running Tests and Commands)
- **Database:** PostgreSQL via psycopg2-binary
- **ORM:** SQLAlchemy (synchronous sessions)
- **Migrations:** Alembic (`backend/models.py` is the source of truth)
- **Task runner:** `just` (see `justfile`)

## Architectural Rules

- **Sync-first:** Route handlers use `def` so FastAPI offloads them to its external thread pool, keeping the event loop free from blocking I/O.
- **Dependency injection:** `get_session` manages the SQLAlchemy session lifecycle (Unit of Work pattern). Override it in tests via `app.dependency_overrides`.
- **Real DB in tests:** Tests run against a real PostgreSQL container via `testcontainers` — no SQLite, no mocking the database layer.
- **Exception handling:** Decorate handlers with `@handle_exception(logger)` to ensure full tracebacks are captured via `logger.exception`.
- **Environment:** The venv location differs by context — `POETRY_VIRTUALENVS_IN_PROJECT=true` on the host (`.venv/` in project), `false` inside the devcontainer (venv in Poetry cache, NOT in `.venv/`). Never assume `.venv/` exists inside the container.
- **Configuration:** All env config via `backend/config.py` (`pydantic-settings BaseSettings`) — never `os.environ` directly.

## Running Tests and Commands

The test suite is split into two layers:

| Marker | Command | DB needed | Where it runs |
|---|---|---|---|
| `unit` | `just backend-test-fast` | No | Anywhere — devcontainer, host, CI |
| `integration` | `just backend-test` | Yes (testcontainers) | Host only — requires Docker |

**Inside the devcontainer:** run `just backend-check` (lint + type check) and `just backend-test-fast` (unit tests only). This is sufficient for autonomous coding — the unit tests cover all logic that doesn't touch the database.

**Integration tests must run on the host.** The devcontainer has no Docker socket — `testcontainers` cannot start a PostgreSQL container inside it. Always run `just backend-test` and `just ci` from a host terminal.

The two execution contexts have different venv setups:

| Context | `POETRY_VIRTUALENVS_IN_PROJECT` | venv location | Can run tests? |
|---|---|---|---|
| Host (macOS) | `true` | `.venv/` in project root | Yes — Docker available |
| Devcontainer (Linux) | `false` | Poetry cache dir — `.venv/` does NOT exist | Unit tests only |

**Always use `just` recipes, never call tools directly.** Do not call `.venv/bin/pytest` or `.venv/bin/basedpyright` directly — `.venv/` does not exist inside the devcontainer, and direct invocations bypass the justfile recipes.

If a `just` command fails with a Poetry/venv error, **stop and report the error** — do not attempt to work around it by invoking `.venv/bin/*` directly.

## Work Process

- **Task Tracking:** Always refer to `TASK_PLAN.md` for the current project state and upcoming phases.
- **Updates:** After completing a significant sub-task, update the relevant checkbox in `TASK_PLAN.md`.
- **Context:** Before starting a new phase, run `ls -R` to verify the filesystem matches the expected state in the plan.

## Project Structure

```
.
├── .devcontainer/
│   ├── Dockerfile              # Devcontainer image (Python 3.12, tools, zsh)
│   ├── devcontainer.json       # IDE devcontainer config (VS Code, JetBrains)
│   ├── docker-compose.yml      # Compose wrapper for the devcontainer service
│   ├── entrypoint.sh           # UID/GID injection + optional firewall + gosu privilege drop
│   ├── firewall.sh             # Network egress firewall (used in --firewall mode only)
│   └── firewall-allowlist.txt  # Allowed outbound domains for autonomous mode
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
│   ├── conftest.py          # Shared fixtures: fake_redis, allure labels, rate-limit toggle
│   ├── unit/
│   │   └── test_google_oauth.py   # Pure-logic OAuth tests (no DB)
│   ├── integration/
│   │   ├── conftest.py      # DB fixtures: testcontainers PostgreSQL, engine, session, TestClient
│   │   ├── test_auth.py
│   │   ├── test_google_oauth.py   # Callback/observability tests (need DB)
│   │   ├── test_health.py
│   │   ├── test_metrics.py
│   │   ├── test_routines.py
│   │   ├── test_security.py
│   │   └── test_users.py
│   ├── perf/                # Performance tests (marked perf, excluded from default run)
│   └── e2e/                 # End-to-end tests (marked e2e, excluded from default run)
├── .env                # Database credentials (not committed)
├── .python-version     # pyenv version pin
├── alembic.ini
├── docker-compose.yml  # PostgreSQL, Prometheus, Grafana (monitoring profile)
├── justfile            # Task runner — use `just ci` as pre-PR gate
└── pyproject.toml
```
