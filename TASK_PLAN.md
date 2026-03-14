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

## Phase 1: Observability & Monitoring (IN PROGRESS)

**Goal:** Full-stack visibility into the service's health and logs.

- [x] **Metrics:** Prometheus instrumentator and `/metrics` endpoint.
- [x] **Visualisation:** Grafana dashboards for RED metrics.
- [x] **Architecture Docs:** Documented architectural decisions and C4 diagrams.
- [x] **Logging (Loki):** Implement centralised logging via Loki with direct HTTP push from Python.
- [x] **Structured Logs:** Transition backend loggers to JSON format for Loki indexing.

---

## Phase 2: Security & Identity

**Goal:** Layered authentication and authorization.

- [ ] **Auth Core:** Implement JWT logic (OAuth2 Password Bearer) in `backend/security.py`.
- [ ] **Local Secret Management:** Support for encrypted `.env` or local KMS mocks for sensitive data.
- [ ] **Access Control:**
  - Create `Optional[User]` dependency for public view access.
  - Implement `PermissionChecker` to gate Write operations (POST/PUT/DELETE).
- [ ] **Security Testing:** Update test suite to verify 401/403 security boundaries.

---

## Phase 3: Frontend Scaffolding (Vite + PrimeVue)

**Goal:** Modern, accessible UI foundation.

- [ ] **Vite Setup:** Initialise `frontend/` with Vue 3 and TypeScript.
- [ ] **PrimeVue Integration:** Set up "Unstyled Mode" with Tailwind CSS.
- [ ] **Layout:** Build the responsive App shell (Navbar/Sidebar).
- [ ] **API Layer:** Configure Axios/Fetch interceptors for port 8000 communication.

---

## Phase 4: Data & Interaction Split (View vs. Edit)

**Goal:** Complete the user loop with conditional permissions.

- [ ] **DataTable:** Implement PrimeVue `DataTable` with server-side sorting/filtering.
- [ ] **View Mode:** Read-only detail view for sequences.
- [ ] **Login Flow:** User authentication UI and JWT persistence in `localStorage`.
- [ ] **Edit Mode:** Conditional rendering of forms/dialogs based on user ownership/scopes.
