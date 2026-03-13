venv := ".venv/bin"

# Start the development server
dev:
    {{venv}}/uvicorn backend.main:app --reload

# Apply all pending database migrations
migrate:
    {{venv}}/alembic upgrade head

# Generate a new Alembic migration
makemigrations message:
    {{venv}}/alembic revision --autogenerate -m "{{message}}"

# Start the PostgreSQL container in the background
db-up:
    docker compose up -d db

# Stop and remove the PostgreSQL container
db-down:
    docker compose down

# Tail logs from the PostgreSQL container
db-logs:
    docker compose logs -f db

# Run the test suite
test:
    {{venv}}/pytest

# Run tests with a terminal coverage report
test-cov:
    {{venv}}/pytest --cov=backend --cov-report=term-missing

# Run performance/timing tests (demonstrates event loop blocking anti-pattern)
perf:
    {{venv}}/pytest tests/perf/ -v -s -m perf

# Start DB, wait for healthy, then run migrations
bootstrap: db-up
    #!/usr/bin/env bash
    echo "Waiting for postgres to be ready..."
    until docker compose exec db pg_isready -U postgres -q; do sleep 1; done
    just migrate
