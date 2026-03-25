venv        := `poetry env info --executable | xargs dirname`
backend_log := "/tmp/backend.log"
frontend_log := "/tmp/frontend.log"

BRAINSTORM_PORT := env("BRAINSTORM_PORT", "19452")

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

# Run unit tests only — no database required, safe inside the devcontainer
backend-test-fast:
    {{venv}}/pytest tests/unit/ --alluredir=allure-results --clean-alluredir

# Run the full backend test suite (unit + integration) — requires Docker for testcontainers, run on host only
backend-test:
    {{venv}}/pytest --alluredir=allure-results --clean-alluredir

# Run backend tests and open the Allure report in a browser
backend-test-report: backend-test
    allure serve allure-results

# Run backend tests with a terminal coverage report
backend-test-cov:
    {{venv}}/pytest --cov=backend --cov-report=term-missing

# Run performance/timing tests (writes Allure results)
backend-perf:
    {{venv}}/pytest tests/perf/ -v -s -m perf --alluredir=allure-results-perf --clean-alluredir

# Run performance/timing tests and open the Allure report in a browser
backend-perf-report: backend-perf
    allure serve allure-results-perf

# Run end-to-end tests against the live stack (requires platform-up + backend-dev)
backend-e2e:
    {{venv}}/pytest tests/e2e/ -v -s -m e2e --alluredir=allure-results-e2e --clean-alluredir

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

# Install Playwright browser binaries (run once after npm install)
frontend-e2e-install:
    cd frontend && npx playwright install chromium

# Run Playwright e2e tests (requires: just dev-up)
frontend-e2e:
    cd frontend && npm run e2e

# Run frontend Vitest tests and open the Allure report in a browser
frontend-test-report: frontend-test
    cd frontend && allure serve allure-results

# Run Playwright e2e tests and open the Allure report in a browser
# Requires: just dev-up
frontend-e2e-report: frontend-e2e
    cd frontend && allure serve allure-results-e2e

# Delete all Allure results so the next report contains only fresh test runs
clean-reports:
    rm -rf allure-results allure-results-perf allure-results-e2e frontend/allure-results frontend/allure-results-e2e

# Run all tests (backend + frontend) then open a combined Allure report
# Requires: just platform-up && just dev-up
report: clean-reports ci
    allure serve allure-results allure-results-perf allure-results-e2e frontend/allure-results frontend/allure-results-e2e

# ── Platform ─────────────────────────────────────────────────────────────────

# Start all platform services (PostgreSQL + Redis + full monitoring stack)
platform-up: db-up redis-up obs-up

# Stop all platform services
platform-down:
    docker compose --profile monitoring down

# Start the PostgreSQL container only
db-up:
    docker compose up -d db

# Start the Redis container
redis-up:
    docker compose up -d redis

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

# Devcontainer-safe check: everything that runs without Docker (lint + type check + unit tests)
# Safe to run inside the devcontainer. Does NOT require Docker or platform-up.
container-ci: backend-check frontend-check backend-test-fast frontend-test

# Full pre-PR gate: backend checks + all tests + frontend check + frontend tests + playwright e2e
# Requires: just platform-up && just dev-up running in another terminal
ci: backend-check frontend-check backend-test backend-perf backend-e2e frontend-test frontend-e2e

# ── Dev Container ────────────────────────────────────────────────────────────

# Launch an interactive devcontainer shell (e.g. `just dev-shell`, `just dev-shell claude`)
# Add --firewall as the first argument for network-firewalled autonomous mode:
#   just dev-shell --firewall claude
[positional-arguments]
dev-shell *args:
    #!/usr/bin/env bash
    set -euo pipefail
    docker build -t python-fastapi-poc-devcontainer .devcontainer/
    tty_flag=$( [[ -t 0 ]] && echo "-it" || echo "-i" )
    run_args=(
        --rm $tty_flag --init
        -v "$(pwd):$(pwd)" -w "$(pwd)"
        -v "$SSH_AUTH_SOCK:/tmp/ssh-agent.sock"
        -e SSH_AUTH_SOCK=/tmp/ssh-agent.sock
        -e COLORTERM="${COLORTERM:-}"
        -e DEVCONTAINER_WORKSPACE="$(pwd)"
        -e POETRY_VIRTUALENVS_IN_PROJECT=false
    )
    # Firewalled mode: iptables egress filter + run as root then drop privileges via gosu
    # Normal mode: run directly as host UID (no firewall, no caps)
    if [[ "${1:-}" = "--firewall" ]]; then
        shift
        run_args+=(
            --cap-add=NET_ADMIN --cap-add=NET_RAW
            -e DEVCONTAINER_FIREWALL=1
            -e DEVCONTAINER_UID="$(id -u)"
            -e DEVCONTAINER_GID="$(id -g)"
        )
    else
        run_args+=(--user "$(id -u):$(id -g)")
    fi
    # Conditional host config mounts (only add if the source exists)
    [[ -f "$HOME/.gitconfig" ]] && run_args+=(-v "$HOME/.gitconfig:/tmp/home/.gitconfig:ro")
    [[ -d "$HOME/.config/gh" ]] && run_args+=(-v "$HOME/.config/gh:/tmp/gh-config")
    [[ -d "$HOME/.claude" ]] && run_args+=(
        -v "$HOME/.claude:/tmp/home/.claude"
        -v "$HOME/.claude:$HOME/.claude"
    )
    [[ -f "$HOME/.claude.json" ]] && run_args+=(-v "$HOME/.claude.json:/tmp/home/.claude.json")
    # Superpowers brainstorming visual companion port
    run_args+=(-p "{{ BRAINSTORM_PORT }}:{{ BRAINSTORM_PORT }}")
    run_args+=(-e "BRAINSTORM_PORT={{ BRAINSTORM_PORT }}")
    run_args+=(-e "BRAINSTORM_HOST=0.0.0.0")
    run_args+=(-e "BRAINSTORM_URL_HOST=localhost")
    if [[ $# -eq 0 ]]; then
        exec docker run "${run_args[@]}" python-fastapi-poc-devcontainer bash
    else
        exec docker run "${run_args[@]}" python-fastapi-poc-devcontainer "$@"
    fi
