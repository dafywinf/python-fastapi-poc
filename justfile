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

# Run all checks required before raising a PR
ci: check test perf

# Lint and type-check the codebase
check:
    {{venv}}/ruff check .
    {{venv}}/basedpyright .

# Run the test suite (always writes Allure results)
test:
    {{venv}}/pytest --alluredir=allure-results

# Run tests and open the Allure report in a browser
test-report:
    {{venv}}/pytest --alluredir=allure-results
    allure serve allure-results

# Run tests with a terminal coverage report
test-cov:
    {{venv}}/pytest --cov=backend --cov-report=term-missing

# Run performance/timing tests (always writes Allure results)
perf:
    {{venv}}/pytest tests/perf/ -v -s -m perf --alluredir=allure-results

# Run performance/timing tests and open the Allure report in a browser
perf-report:
    {{venv}}/pytest tests/perf/ -v -s -m perf --alluredir=allure-results
    allure serve allure-results

# Start DB, wait for healthy, then run migrations
bootstrap: db-up
    #!/usr/bin/env bash
    echo "Waiting for postgres to be ready..."
    until docker compose exec db pg_isready -U postgres -q; do sleep 1; done
    just migrate
