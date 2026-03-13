📋 The Master Specification for Claude
Project Goal: A "Hello World" FastAPI application for a Sequence entity using a Synchronous/Threaded architecture and Alembic migrations.

1. Environment & Tools
Python: 3.12 (UK English).

Version Management: pyenv (using a .python-version file).

Dependency Management: Poetry (configured for in-project .venv).

OS Target: AlmaLinux 9 / macOS.

Command Runner: just (via a justfile).

2. Stack Requirements
Framework: FastAPI.

Web Server: Uvicorn (standard def mode).

Database: PostgreSQL with psycopg2-binary.

ORM: SQLAlchemy (Synchronous Session).

Migrations: Alembic (configured with env.py for autogeneration).

3. Core logic
Routes: Use standard def for all routes to utilise FastAPI’s thread pool.

Dependency Injection: A get_session function to manage the SQLAlchemy session lifecycle.

Exceptions: A @handle_exception(logger) decorator that uses logger.exception() for full tracebacks.

Schema: A Sequence table with id, name, and description.

4. Explicit Instructions for Claude
"I am using pyenv for Python version management and Poetry for dependency management. I want the project's virtual environment to be stored locally in a .venv folder within the project directory.

Please ensure the alembic/env.py file correctly imports my SQLAlchemy models so that just makemigrations detects my 'Sequence' table automatically.

Finally, add a 'Getting Started' section to my README that includes Homebrew installation commands for macOS, pyenv setup, and the Poetry configuration command (poetry config virtualenvs.in-project true) to ensure the .venv is created in-project."
