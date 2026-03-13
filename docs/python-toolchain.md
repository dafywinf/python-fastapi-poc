# Python Toolchain: pyenv, Poetry, and Your IDE

This document explains how pyenv, Poetry, your virtual environment, and your IDE
fit together — and crucially, what each tool touches on your machine.

---

## The Big Picture

There are three distinct layers of Python on your machine.  Each layer is
completely separate, and understanding which layer you are operating in at any
moment prevents almost every "why doesn't this package exist?" problem.

```
┌─────────────────────────────────────────────────────────────┐
│                      YOUR MACHINE                           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  LAYER 1 — System Python                            │   │
│  │  /usr/bin/python3  (macOS ships this, do not touch) │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  LAYER 2 — pyenv  (~/.pyenv/)                       │   │
│  │  Manages multiple Python versions side by side.     │   │
│  │  e.g. 3.11.9, 3.12.3, 3.13.0                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  LAYER 3 — Project .venv  (lives inside the repo)   │   │
│  │  Isolated packages for this project only.           │   │
│  │  Managed by Poetry.                                 │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1: System Python

macOS ships with a Python at `/usr/bin/python3`.  This is used by macOS
internals.  **You should never install packages into it** — doing so can
break OS tooling and the changes bleed across every project on your machine.

```
/usr/bin/python3        ← owned by macOS, leave it alone
/usr/lib/python3/...    ← system packages, do not touch
```

---

## Layer 2: pyenv

pyenv lives entirely in `~/.pyenv/` and intercepts every `python` / `python3`
command via shims.

```
~/.pyenv/
├── shims/
│   ├── python          ← intercepts all `python` calls
│   ├── python3         ← intercepts all `python3` calls
│   └── pip             ← intercepts all `pip` calls
├── versions/
│   ├── 3.11.9/         ← a full Python installation
│   └── 3.12.3/         ← another full Python installation
└── version             ← global default version file
```

### How pyenv picks a version

When you run `python`, pyenv checks in this order:

```
1. PYENV_VERSION env var (if set)
        ↓
2. .python-version file  (walks up from current directory)
        ↓
3. ~/.pyenv/version      (global default)
        ↓
4. System Python         (fallback)
```

This project has a `.python-version` file at the root:

```
$ cat .python-version
3.12
```

So any `python` call inside this directory automatically uses 3.12 — no
activation needed.

### What gets written when you run `pyenv install 3.12.3`

```
~/.pyenv/versions/3.12.3/    ← new directory created here ONLY
    bin/python3.12
    lib/python3.12/
    ...
```

Nothing else on your machine is touched.

---

## Layer 3: Poetry and the Project .venv

Poetry is a dependency manager and packaging tool.  It reads `pyproject.toml`
to know what packages are needed, resolves versions, writes `poetry.lock`, and
installs everything into a virtual environment.

Because this project is configured with:

```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.12"
```

and Poetry is configured globally with:

```bash
poetry config virtualenvs.in-project true
```

Poetry places the virtual environment **inside the project directory**:

```
python-fastapi-poc/
├── .venv/                  ← virtual environment lives here
│   ├── bin/
│   │   ├── python          ← symlink to ~/.pyenv/versions/3.12.x/bin/python
│   │   ├── pip
│   │   ├── uvicorn
│   │   ├── pytest
│   │   └── alembic
│   └── lib/
│       └── python3.12/
│           └── site-packages/
│               ├── fastapi/
│               ├── sqlalchemy/
│               ├── pydantic/
│               └── ...     ← all your project packages live here
├── pyproject.toml
├── poetry.lock
└── ...
```

### What `poetry install` does

```
poetry install
      │
      ├── reads pyproject.toml   (what packages are wanted)
      ├── reads poetry.lock      (exact pinned versions)
      ├── creates .venv/         (if it doesn't exist)
      │       using the Python from pyenv (.python-version)
      └── installs packages into .venv/lib/python3.12/site-packages/
```

**Nothing outside the project directory is written.**

### What `poetry add <package>` does

```
poetry add requests
      │
      ├── resolves the new dependency against existing ones
      ├── updates pyproject.toml  (adds the new requirement)
      ├── updates poetry.lock     (pins the exact version)
      └── installs into .venv/    (same as install)
```

Commit both `pyproject.toml` and `poetry.lock` so every developer gets
identical package versions.

---

## Why You Should Not Run `pip install` Directly

`pip` is not version-aware in the way Poetry is.  When you run `pip install`
you need to be certain *which* pip you are calling.

```
Scenario A — the dangerous case
────────────────────────────────
$ pip install requests
        ↑
        which pip is this?

  If your shell PATH puts ~/.pyenv/shims first (it should),
  pyenv intercepts it and delegates to the active Python's pip.

  But if you have not activated .venv, that pip belongs to the
  pyenv Python itself — NOT your project .venv.

  Result: requests is installed into ~/.pyenv/versions/3.12.x/
          and is now visible to EVERY project using that Python.
          This is "pollution" of the shared pyenv environment.


Scenario B — the safe case
───────────────────────────
$ .venv/bin/pip install requests
        ↑
        explicit path to the project venv pip

  Installs only into .venv/lib/python3.12/site-packages/.
  No other project is affected.
  But Poetry doesn't know about it — it's not in pyproject.toml.
```

**The rule:** always use `poetry add` to install packages.  Never use `pip install`
unless you are explicitly targeting `.venv/bin/pip` for a one-off inspection.

---

## How `just` Avoids the Activation Problem

Each `just` recipe runs in a **fresh shell** — there is no concept of an
"activated" virtual environment persisting between commands.  The `justfile`
solves this by referencing binaries with their full `.venv/bin/` path:

```makefile
venv := ".venv/bin"

dev:
    {{venv}}/uvicorn backend.main:app --reload

test:
    {{venv}}/pytest
```

This means `just test` always uses the project's pytest, regardless of what
is or isn't activated in your terminal.

---

## IDE Integration (PyCharm / IntelliJ)

Your IDE needs to know which Python interpreter to use for:

- Code completion and type checking
- Running/debugging files
- Resolving imports

Point it at `.venv/bin/python` — the interpreter inside the project virtualenv.

```
PyCharm: Preferences → Project → Python Interpreter
         → Add Interpreter → Existing → .venv/bin/python

IntelliJ (with Python plugin):
         File → Project Structure → SDKs → +
         → Python SDK → Existing → .venv/bin/python
```

Once set, the IDE reads packages from `.venv/lib/python3.12/site-packages/`
and resolves all imports correctly.

```
IDE type checker / completion
        │
        └── reads .venv/lib/python3.12/site-packages/
                ├── fastapi/         ✓ resolves FastAPI types
                ├── sqlalchemy/      ✓ resolves ORM types
                └── pydantic/        ✓ resolves Pydantic models
```

---

## Full Map: What Each Command Touches

```
Command                     Writes to                       Pollutes globally?
─────────────────────────────────────────────────────────────────────────────
pyenv install 3.12.3        ~/.pyenv/versions/3.12.3/       No
pyenv global 3.12.3         ~/.pyenv/version                Yes (changes default)
poetry config ...           ~/.config/pypoetry/             Yes (global config)
poetry install              .venv/                          No
poetry add <pkg>            .venv/, pyproject.toml,         No
                            poetry.lock
pip install <pkg>           Depends on active environment   Possibly yes (see above)
.venv/bin/pip install <pkg> .venv/                          No (but not tracked)
just test / just dev        reads .venv/, no writes         No
```

---

## Quick Reference

```
┌──────────────────┬─────────────────────────────────────────────────────┐
│ I want to...     │ Use this                                             │
├──────────────────┼─────────────────────────────────────────────────────┤
│ Use Python 3.12  │ Automatic — .python-version tells pyenv              │
│ Install deps     │ poetry install                                       │
│ Add a package    │ poetry add <package>                                 │
│ Add a dev pkg    │ poetry add --group dev <package>                     │
│ Remove a package │ poetry remove <package>                              │
│ Run tests        │ just test                                            │
│ Run the server   │ just dev                                             │
│ See what's in    │ .venv/bin/pip list                                   │
│ the virtualenv   │                                                      │
└──────────────────┴─────────────────────────────────────────────────────┘
```

---

## Library Choices

This section explains every production and development dependency, what it
does, and why it was chosen over the alternatives.

---

### Web Framework — FastAPI

**What it does:** FastAPI is a modern Python web framework for building HTTP
APIs.  It uses Python type hints to drive automatic request validation,
serialisation, and interactive documentation (Swagger UI / ReDoc).

**Why it is good practice:**

- **Type-driven validation** — request bodies and query parameters are
  declared as Pydantic models; FastAPI validates them before your handler
  runs, so you never write manual parsing code.
- **Automatic OpenAPI docs** — a `/docs` UI is generated from your type hints
  with zero extra work, keeping documentation in sync with the code.
- **Sync handler support** — when a handler is declared with `def` (not
  `async def`) FastAPI automatically offloads it to a thread-pool executor.
  This keeps the event loop free from blocking I/O (database calls, etc.)
  without requiring the entire stack to be async.
- **Mature ecosystem** — widely adopted, well documented, and actively
  maintained with a stable release cadence.

---

### ASGI Server — Uvicorn `[standard]`

**What it does:** Uvicorn is the ASGI server that runs the FastAPI application.
The `[standard]` extra installs `uvloop` (a faster event loop) and `httptools`
(a faster HTTP parser).

**Why it is good practice:**

- **Production-grade performance** — uvloop is a drop-in replacement for
  asyncio's default event loop and is measurably faster under load.
- **Standard extra is safe** — `httptools` and `uvloop` are optional; the
  `[standard]` marker installs them only where the platform supports them,
  so the same `pyproject.toml` works on Linux CI and macOS dev machines.

---

### ORM — SQLAlchemy 2.0

**What it does:** SQLAlchemy is the industry-standard Python ORM.  Version 2.0
introduced a fully typed, declarative mapping API and broke cleanly with the
legacy 1.x patterns.

**Why it is good practice:**

- **Typed models** — `Mapped[T]` and `mapped_column()` give basedpyright full
  visibility into column types, catching type mismatches at analysis time.
- **Explicit query style** — `select()` + `session.execute()` is composable,
  testable, and makes SQL intent obvious.  The legacy `.query()` API is removed
  in 2.0, preventing accidental use of deprecated patterns.
- **Session-as-unit-of-work** — the session tracks changes and flushes them
  as a single atomic unit, reducing accidental partial writes.
- **Database agnostic** — the same ORM code works against PostgreSQL in
  production and (if needed) against other engines in isolated contexts.

---

### Migrations — Alembic

**What it does:** Alembic is the official SQLAlchemy migration tool.  It
generates versioned migration scripts that evolve the database schema
incrementally and reproducibly.

**Why it is good practice:**

- **Schema-as-code** — migrations live in version control alongside the
  application, so every environment (dev, CI, production) can be brought to
  exactly the same schema state by running `alembic upgrade head`.
- **Auto-generation** — `alembic revision --autogenerate` diffs the current
  database against `backend/models.py` and generates the migration script,
  reducing hand-written SQL and the errors that come with it.
- **Rollback support** — every migration has a `downgrade()` function, giving
  a safe path back if a release needs to be reverted.

---

### Database Driver — psycopg2-binary

**What it does:** psycopg2 is the most widely used PostgreSQL adapter for
Python.  The `-binary` variant ships a pre-compiled wheel that includes the
C extension and libpq, so no native build toolchain is needed.

**Why it is good practice:**

- **Synchronous and correct for this architecture** — because route handlers
  use `def` (thread-pool), a blocking synchronous driver is exactly right.
  An async driver (asyncpg) would be wasted complexity here and could
  introduce subtle misuse if mixed with the sync session.
- **Stability** — psycopg2 is battle-tested in production across thousands of
  projects and integrates seamlessly with SQLAlchemy.
- **Binary wheel** — removes the need for `libpq-dev` / `postgresql-client`
  on developer and CI machines, keeping setup fast and reproducible.

---

### Validation & Serialisation — Pydantic V2

**What it does:** Pydantic provides runtime data validation and serialisation
driven by Python type hints.  V2 is a complete rewrite in Rust, making it
significantly faster than V1.

**Why it is good practice:**

- **Single source of truth** — the same model class defines both the API
  contract (what the client sends/receives) and the validation rules, removing
  duplication between schema definitions and validation logic.
- **`ConfigDict(from_attributes=True)`** — allows Pydantic models to be
  constructed directly from SQLAlchemy ORM instances, eliminating manual
  mapping boilerplate between the ORM layer and the API layer.
- **Strict by default** — V2 does not silently coerce types in strict mode,
  so a string `"123"` passed to an `int` field raises a validation error
  rather than silently succeeding.
- **FastAPI native** — FastAPI was designed around Pydantic; all request/
  response validation and OpenAPI schema generation is powered by it.

---

### Environment Configuration — pydantic-settings

**What it does:** pydantic-settings extends Pydantic with a `BaseSettings`
class that reads values from environment variables and `.env` files, then
validates them with the same type-hint machinery as regular Pydantic models.

**Why it is good practice:**

- **Typed configuration** — `database_url: str` in the settings class means
  basedpyright knows the type everywhere it is used.  Missing or wrongly typed
  environment variables are caught at startup, not at the point of use deep in
  a request handler.
- **No `os.environ` scattered through the code** — a single `settings` object
  imported from `backend/config.py` is the only place raw environment access
  happens, making configuration easy to audit and mock.
- **`.env` file support** — developers can keep credentials in a local `.env`
  file (git-ignored) without any extra loading code in the application.

---

### Linter & Formatter — Ruff

**What it does:** Ruff is a fast Python linter and formatter written in Rust.
It replaces flake8, isort, and black with a single tool and a single
configuration block in `pyproject.toml`.

**Why it is good practice:**

- **Speed** — Ruff is orders of magnitude faster than the tools it replaces,
  making it practical to run on every save in the IDE and on every CI push.
- **Consolidation** — one tool, one config, zero conflicts between formatters
  and linters disagreeing on line length or import order.
- **Rule coverage** — the `E`, `F`, `I`, `UP` rule sets cover pycodestyle,
  pyflakes, import ordering, and pyupgrade (modernises syntax automatically),
  providing broad coverage without manual configuration of multiple plugins.

---

### Type Checker — basedpyright

**What it does:** basedpyright is a strict static type checker for Python,
forked from Microsoft's Pyright.  It runs entirely locally (no external
service) and integrates with most editors via the Pylance language server
protocol.

**Why it is good practice:**

- **Strict mode** — with `typeCheckingMode = "strict"`, every untyped function
  parameter, implicit `Any`, and missing return type is a hard error.  This
  forces type discipline consistently across the codebase.
- **Faster feedback than mypy** — basedpyright is significantly faster than
  mypy on large codebases, making it practical to run in the pre-commit gate.
- **Better inference** — basedpyright's type narrowing and generic inference
  are more precise than mypy's in many common patterns (e.g. `TypeGuard`,
  overloaded functions), producing fewer spurious errors.
- **Replaces mypy** — a single type checker avoids the configuration drift and
  false-positive differences that come from running both.

---

### Test Runner — pytest

**What it does:** pytest is the de-facto standard Python test runner.  It
discovers tests automatically, supports fixtures for dependency injection, and
has a rich plugin ecosystem.

**Why it is good practice:**

- **Fixture system** — pytest fixtures (`conftest.py`) allow shared setup
  (database sessions, HTTP clients) to be injected into tests without
  inheritance or manual wiring, keeping tests flat and readable.
- **Parametrise** — `@pytest.mark.parametrize` makes it trivial to run the
  same test against multiple inputs without duplicating test functions.
- **Plugin ecosystem** — `pytest-cov`, `allure-pytest`, and `testcontainers`
  all integrate as pytest plugins, keeping the test command simple.

---

### Coverage — pytest-cov

**What it does:** pytest-cov is a pytest plugin that measures code coverage
during a test run and reports which lines were not executed.

**Why it is good practice:**

- **Integrated** — runs as part of `pytest` with a single `--cov` flag; no
  separate invocation needed.
- **CI gate** — the minimum 80% coverage requirement on new features prevents
  the test suite from becoming a facade that runs but does not verify behaviour.
- **XML output** — `--cov-report=xml` produces a `coverage.xml` file that
  Codecov (or any CI coverage service) can parse and annotate on pull requests.

---

### HTTP Client — httpx

**What it does:** httpx is a modern HTTP client for Python with both sync and
async interfaces.  FastAPI's `TestClient` is built on top of httpx.

**Why it is good practice:**

- **Required by FastAPI TestClient** — `starlette.testclient.TestClient`
  (re-exported by FastAPI) uses httpx under the hood; it is not optional.
- **Consistent API** — httpx's API is deliberately similar to the popular
  `requests` library, so it is easy to use in tests without a learning curve.
- **Async capable** — if the project ever adds async endpoints, httpx's
  `AsyncClient` can test them without switching libraries.

---

### Test Reporting — allure-pytest

**What it does:** allure-pytest is a pytest plugin that emits structured JSON
during the test run.  The Allure CLI then renders these into a rich HTML
report with per-test timelines, attachments, and pass/fail history.

**Why it is good practice:**

- **Readable reports** — Allure's HTML output is far more navigable than
  plain terminal output, making it easy to identify which tests failed and why,
  especially in a CI context with many tests.
- **Behaviour-driven structure** — `@allure.feature` and `@allure.story`
  decorators organise tests by product area rather than by file, bridging the
  gap between technical tests and stakeholder-readable results.
- **Local only** — report generation is intentionally kept off CI (it adds
  time and artefact storage complexity); developers generate reports locally
  with `just test-report` and `just perf-report` when they need them.

---

### Integration Database — testcontainers `[postgres]`

**What it does:** testcontainers starts a real Docker container running
PostgreSQL at the beginning of the test session and tears it down at the end.
Each test runs inside a savepoint transaction that is rolled back on teardown,
providing full isolation without truncating tables between tests.

**Why it is good practice:**

- **Real database, real behaviour** — SQLite (the common in-memory alternative)
  has different type coercion rules, missing features (e.g. `RETURNING`), and
  different locking semantics.  Tests that pass against SQLite have failed in
  production against PostgreSQL.  testcontainers eliminates that class of
  failure entirely.
- **No mocking** — mocking the database hides the real queries from the test.
  A mocked test can pass while the actual SQL is syntactically invalid or
  returns wrong results.
- **Savepoint isolation** — wrapping each test in a savepoint (rather than
  truncating) is dramatically faster and leaves no dirty state between tests,
  even if a test throws an unhandled exception.
