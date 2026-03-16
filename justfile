venv        := ".venv/bin"
backend_log := "/tmp/backend.log"
frontend_log := "/tmp/frontend.log"

# List all available commands
help:
    @just --list

# ── Private helpers ─────────────────────────────────────────────────────────

[private]
_stop-backend:
    pkill -f "uvicorn backend.main:app" || true

[private]
_stop-frontend:
    pkill -f "frontend/node_modules/.bin/vite" || true

# ── Dev (full stack) ─────────────────────────────────────────────────────────

# Start backend + frontend in the background (logs → /tmp/*.log). Run after: just platform-up
dev-up: _stop-backend _stop-frontend
    #!/usr/bin/env bash
    set -e
    {{venv}}/uvicorn backend.main:app --reload > {{backend_log}} 2>&1 &
    echo "Backend started (port 8000) → {{backend_log}}"
    cd frontend && npm run dev > {{frontend_log}} 2>&1 &
    echo "Frontend started (port 5173) → {{frontend_log}}"
    sleep 3
    curl -sf http://localhost:8000/health > /dev/null && echo "✓ Backend healthy" || echo "✗ Backend not responding"
    curl -sf http://localhost:5173 > /dev/null && echo "✓ Frontend healthy" || echo "✗ Frontend not responding"

# Stop backend and frontend
dev-down: _stop-backend _stop-frontend
    @echo "Backend and frontend stopped"

# Tail backend and frontend logs (Ctrl-C to exit)
dev-logs:
    tail -f {{backend_log}} {{frontend_log}}

# ── Backend ──────────────────────────────────────────────────────────────────

# Start the FastAPI backend with hot-reload (port 8000)
backend-dev:
    {{venv}}/uvicorn backend.main:app --reload

# Stop the FastAPI backend
backend-dev-stop: _stop-backend

# Lint, format-check, and type-check the backend
backend-check:
    {{venv}}/ruff check .
    {{venv}}/ruff format --check .
    {{venv}}/basedpyright .

# Run the backend integration test suite (writes Allure results)
backend-test:
    {{venv}}/pytest --alluredir=allure-results

# Run backend tests and open the Allure report in a browser
backend-test-report: backend-test
    allure serve allure-results

# Run backend tests with a terminal coverage report
backend-test-cov:
    {{venv}}/pytest --cov=backend --cov-report=term-missing

# Run performance/timing tests (writes Allure results)
backend-perf:
    {{venv}}/pytest tests/perf/ -v -s -m perf --alluredir=allure-results

# Run performance/timing tests and open the Allure report in a browser
backend-perf-report: backend-perf
    allure serve allure-results

# Run end-to-end tests against the live stack (requires platform-up + backend-dev)
backend-e2e:
    {{venv}}/pytest tests/e2e/ -v -s -m e2e --alluredir=allure-results

# Apply all pending database migrations
migrate:
    {{venv}}/alembic upgrade head

# Generate a new Alembic migration
makemigrations message:
    {{venv}}/alembic revision --autogenerate -m "{{message}}"

# ── Frontend ─────────────────────────────────────────────────────────────────

# Start the Vite dev server (port 5173, proxies /sequences → port 8000)
frontend-dev:
    cd frontend && npm run dev

# Stop the Vite dev server for this project
frontend-dev-stop: _stop-frontend

# ESLint — lint Vue + TypeScript source
frontend-lint:
    cd frontend && npm run lint

# TypeScript type-check and production build
frontend-check: frontend-lint
    cd frontend && npm run build

# Run the frontend Vitest unit tests (writes Allure results to frontend/allure-results/)
frontend-test:
    cd frontend && npm test

# ── Platform ─────────────────────────────────────────────────────────────────

# Start all platform services (PostgreSQL + full monitoring stack)
platform-up: db-up obs-up

# Stop all platform services
platform-down:
    docker compose --profile monitoring down

# Start the PostgreSQL container only
db-up:
    docker compose up -d db

# Stop and remove all containers
db-down:
    docker compose down

# Tail logs from the PostgreSQL container
db-logs:
    docker compose logs -f db

# Start Prometheus, Loki, and Grafana only
obs-up:
    docker compose --profile monitoring up -d

# Stop Prometheus, Loki, and Grafana
obs-down:
    docker compose --profile monitoring down

# Tail logs from all monitoring containers
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

# ── CI ───────────────────────────────────────────────────────────────────────

# Full pre-PR gate: backend checks + all tests + frontend check + frontend tests
# Requires: just platform-up && just backend-dev running in another terminal
ci: backend-check frontend-check backend-test backend-perf backend-e2e frontend-test
