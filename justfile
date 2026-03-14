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

# Start all platform services (database + monitoring)
platform-up:
    docker compose up -d db
    docker compose --profile monitoring up -d

# Stop all platform services (database + monitoring)
platform-down:
    docker compose --profile monitoring down

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
# Requires: just platform-up && just dev running in a separate terminal
ci: check test perf e2e

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

# Run end-to-end tests against the live stack (requires just platform-up and just dev)
e2e:
    {{venv}}/pytest tests/e2e/ -v -s -m e2e --alluredir=allure-results

# Start Prometheus and Grafana monitoring services
obs-up:
    docker compose --profile monitoring up -d

# Stop and remove Prometheus and Grafana monitoring services
obs-down:
    docker compose --profile monitoring down

# Tail logs from monitoring containers
obs-logs:
    docker compose --profile monitoring logs -f

# Tail logs from the Loki container
loki-logs:
    docker compose --profile monitoring logs -f loki

# Start DB, wait for healthy, then run migrations
bootstrap: db-up
    #!/usr/bin/env bash
    echo "Waiting for postgres to be ready..."
    until docker compose exec db pg_isready -U postgres -q; do sleep 1; done
    just migrate
