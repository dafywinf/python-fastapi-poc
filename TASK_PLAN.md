# Project Progress & Task Plan: Sequence Manager

## Phase 0: Foundation & Toolchain (COMPLETED)

**Goal:** Establish a robust, type-safe Python environment with real-world testing.

- [x] **Core API:** Initial FastAPI sequence management implementation.
- [x] **Testing Infrastructure:** Replace SQLite with `testcontainers` (PostgreSQL) for real integration tests.
- [x] **Type Safety:** Swap `mypy` for `basedpyright` and fix project-wide linting/type errors.
- [x] **Performance Baseline:** Performance tests demonstrating event loop blocking vs. sync handlers.
- [x] **Configuration:** Move from `python-dotenv` to `pydantic-settings` for typed environment config.
- [x] **CI/CD:** GitHub Actions integration with Allure reporting and `just` recipes for automation.
- [x] **Standardisation:** Initial `CLAUDE.md` and `PYTHON_STANDARDS.md` established.

---

## Phase 1: Observability & Monitoring (COMPLETED)

**Goal:** Full-stack visibility into the service's health and logs.

- [x] **Metrics:** Prometheus instrumentator and `/metrics` endpoint.
- [x] **Visualisation:** Grafana dashboards for RED metrics.
- [x] **Architecture Docs:** Documented architectural decisions and C4 diagrams.
- [x] **Logging (Loki):** Implement centralised logging via Loki with direct HTTP push from Python.
- [x] **Structured Logs:** Transition backend loggers to JSON format for Loki indexing.

---

## Phase 2: Security & Identity

**Goal:** Layered authentication and authorization.

- [x] **Auth Core:** Implement JWT logic (OAuth2 Password Bearer) in `backend/security.py`.
- [x] **Local Secret Management:** JWT secret and admin credentials managed via `pydantic-settings` (`JWT_SECRET_KEY`, `ADMIN_PASSWORD_HASH`).
- [x] **Access Control:**
  - Created `get_optional_user` / `OptionalUserDep` for public view access.
  - Implemented `WriteDep` (`require_authenticated_user`) to gate POST/PATCH/DELETE.
- [x] **Security Testing:** Updated test suite (`tests/test_auth.py`) to verify 401 security boundaries.

---

## Phase 3: Frontend Scaffolding (Vite + PrimeVue)

**Goal:** Modern, accessible UI foundation.

- [x] **Vite Setup:** Initialise `frontend/` with Vue 3 and TypeScript.
- [x] **PrimeVue Integration:** Set up "Unstyled Mode" with Tailwind CSS.
- [x] **Layout:** Build the responsive App shell (Navbar/Sidebar).
- [x] **API Layer:** Configure Fetch-based API client with Vite proxy for port 8000 communication.
- [x] **Frontend Tests:** Vitest + allure-vitest; 47 tests across types, API client, list view, detail view.
- [x] **Frontend E2E Tests:** Playwright + Chromium; 12 tests across list, CRUD dialogs, and detail view (Page Object Model, real browser + real backend).
- [x] **CI Integration:** GitHub Actions `frontend` and `frontend-e2e` jobs (build, Vitest, Playwright, Allure artifact uploads).
- [x] **Documentation:** `docs/frontend.md` — architecture, tech stack, test guide, C4 diagram.

---

## Phase 4: Data & Interaction Split (View vs. Edit)

**Goal:** Complete the user loop with conditional permissions.

- [x] **DataTable:** Sortable sequence table with client-side column sorting.
- [x] **View Mode:** Read-only detail view for sequences (`/sequences/:id`).
- [x] **CRUD Dialogs:** Create, edit, and delete via native `<dialog>` modals in list and detail views.
- [x] **Login Flow:** User authentication UI and JWT persistence in `localStorage`.
- [x] **Edit Mode:** Conditional rendering of forms/dialogs based on auth state.

---

## Phase 5: Social Login & User Management ✅

- [x] Google OAuth2 backend (`google_oauth.py` + `user_routes.py`)
- [x] User model + Alembic migration
- [x] `pytest-env` dev dependency + `pyproject.toml` env config
- [x] `admin_username` / `admin_password_hash` / `google_client_id` / `google_client_secret` optional in `config.py`
- [x] Frontend login flow (`LoginView`, `AuthCallbackView`, `useAuth` composable)
- [x] Users page (`UsersView` + `api/users.ts`)
- [x] Navbar auth state (Sign in / Logout / user email)
- [x] Sequences page conditional edit UI (Create, Edit, Delete gated on `isAuthenticated`)
- [x] Tests: backend unit tests, Vitest component tests, Playwright E2E auth flow and users page
