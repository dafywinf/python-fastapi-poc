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
