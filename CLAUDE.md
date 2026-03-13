  5 ## Global Standards
  6
  7 @.claude/standards/\_INDEX.md
  8
 13 ## External Skills
 14
 16 - **Python:** `fullstack-dev-skills:python-pro` for general implementation.dhou


🎯 Objective
Create a "Hello World" style FastAPI application for managing a Sequence entity. This project is designed for a synchronous, threaded architecture (Python 3.12) and uses Alembic for database versioning.

🛠 Tech Stack
Framework: FastAPI

Python Version: 3.12 (using UK English naming conventions)

Version Management: pyenv (via .python-version file)

Dependency Management: Poetry (configured for in-project .venv)

Database: PostgreSQL with psycopg2-binary

ORM: SQLAlchemy (Synchronous Session management)

Migrations: Alembic (The "Liquibase" of Python)

Command Runner: just (via a justfile)

🏗 Architectural Rules
Sync-First (Threaded): Use standard def for route handlers (not async def). This allows FastAPI to utilize its external thread pool for blocking database I/O, preventing Event Loop congestion.

Dependency Injection: Implement a get_session dependency to manage the SQLAlchemy session lifecycle (Unit of Work pattern).

Explicit Exception Handling: Include a decorator @handle_exception(logger) that uses logger.exception() to ensure full tracebacks are captured in logs.

Environment Isolation: The Poetry virtual environment must be stored locally in a .venv folder within the project directory.

📜 Database Schema (Alembic)
Table Name: sequences

Columns: - id: Integer (Primary Key)

name: String (Required)

description: String (Nullable)

created_at: DateTime (Server Default)

🚀 Justfile Commands
just dev: Runs uvicorn backend.main:app --reload

just migrate: Runs alembic upgrade head

just makemigrations "message": Runs alembic revision --autogenerate -m "message"

📂 Project Structure
Plaintext
.
├── alembic/            # Migration environment & env.py
├── backend/
│   ├── main.py         # Entry point & Exception decorators
│   ├── models.py       # SQLAlchemy models (Source of Truth)
│   ├── schemas.py      # Pydantic models (DTOs)
│   ├── database.py     # Engine & SessionLocal setup
│   ├── routes.py       # API Controllers (using def)
│   └── services.py     # Business logic
├── .env                # Database credentials
├── .python-version     # Set to 3.12
├── alembic.ini         # Alembic configuration
├── justfile            # Task automation
└── pyproject.toml      # Poetry dependencies
📋 README Requirements
The generated README.md must include a "Getting Started" section with:

macOS Setup: brew install pyenv poetry just

Python Install: pyenv install $(cat .python-version)

Poetry Config: poetry config virtualenvs.in-project true (to force local .venv)

Project Install: poetry install
