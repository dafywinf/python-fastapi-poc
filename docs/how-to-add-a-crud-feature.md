# How To Add A New CRUD Feature

This guide explains how to add a new CRUD feature to this repository in the same
style as the existing app. It is intentionally repo-specific. The goal is not
just to make something work, but to make it fit the architectural and testing
patterns already established here.

It is also meant to be a high-level orientation guide. If someone is new to
this repo, this document should explain both:

- what technologies the repo uses
- why those technologies were chosen here
- how a new feature should move through the stack from backend to frontend

## What This Repo Is Optimizing For

This repository is not trying to be the smallest possible CRUD demo. It is
trying to be a strong learning/reference app that still feels practical.

That means the codebase intentionally prefers:

- explicit architecture over clever shortcuts
- real contract and database behavior over fake test doubles at lower levels
- generated API contracts over duplicated request/response shapes
- a maintainable component/query structure over page-local fetch logic
- backend-authoritative correctness plus frontend validation for UX
- a test pyramid with a thick middle rather than a browser-heavy E2E stack

When you add a feature here, the target is not just “works on screen.” The
target is:

- backend invariants are explicit
- frontend contract stays aligned with the backend
- the code teaches good habits to the next person reading it

## High-Level Stack

### Backend stack

- **FastAPI**
  Used for request handling, dependency injection, OpenAPI generation, and
  response-model enforcement.
- **SQLAlchemy ORM**
  Used as the backend schema and persistence source of truth.
- **Alembic**
  Used for explicit schema migrations.
- **Pydantic v2**
  Used for request validation and response contracts.
- **pytest + testcontainers**
  Used for backend tests against a real PostgreSQL instance.

Why this backend stack:

- FastAPI gives a clean path from route definitions to OpenAPI contract output.
- SQLAlchemy plus Alembic makes schema evolution explicit and teachable.
- Pydantic keeps request/response behavior visible at the boundary instead of
  hidden in ad hoc code.
- Real Postgres tests catch actual integration problems that SQLite or heavy
  mocking would miss.

### Frontend stack

- **Vue 3**
  The application framework.
- **PrimeVue**
  Shared UI primitives.
- **Tailwind CSS**
  App-owned styling layer.
- **Pinia**
  App/session state, especially auth.
- **TanStack Vue Query**
  Server-state fetching, caching, invalidation, and polling.
- **Vitest + Vue Test Utils**
  Fast component and integration testing.
- **MSW**
  Request-boundary mocks for frontend tests.
- **Playwright**
  Light browser-level smoke coverage.
- **openapi-typescript**
  Generated TypeScript types from the backend OpenAPI schema.

Why this frontend stack:

- PrimeVue solves repeated UI primitives without forcing a fixed visual theme.
- Tailwind keeps styling in the app’s control and works well with PrimeVue
  unstyled mode.
- Pinia is used only for true client/app state, not generic fetched data.
- Vue Query solves the remote-state problems that page-local fetch logic tends to
  create.
- MSW plus generated types gives fast tests that still stay close to the real
  backend contract.
- Playwright is kept small so most coverage stays in the faster middle layer.

## How The Layers Fit Together

When a new feature is added, the intended flow is:

1. backend model and migration
2. backend schema validation
3. backend service behavior
4. backend routes
5. backend tests
6. backend OpenAPI export
7. generated frontend contract types
8. frontend API module
9. frontend queries and mutations
10. frontend page composable
11. frontend client-side validation
12. frontend UI
13. frontend Vitest/MSW tests
14. optional Playwright coverage

The important rule is that the frontend does not invent the contract first. The
backend defines it, OpenAPI exports it, and the frontend consumes it.

## How OpenAPI Passes Across The Repo

This is one of the most important repo-specific patterns.

The flow is:

1. FastAPI builds the OpenAPI schema from route definitions and Pydantic models.
2. [scripts/export_openapi.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/scripts/export_openapi.py) exports that schema to
   `frontend/src/api/generated/openapi.json`.
3. `openapi-typescript` converts that JSON schema into
   `frontend/src/api/generated/schema.d.ts`.
4. Frontend API modules, type facades, and MSW handlers use those generated
   types.
5. Frontend component tests then exercise the UI against contract-shaped mock
   responses.

Why this matters:

- it reduces drift between backend and frontend
- it gives frontend tests realistic payload shapes without needing a live backend
- it keeps the backend as the actual source of truth

In short:

- backend owns the contract
- OpenAPI exports the contract
- frontend consumes the contract
- MSW tests reinforce the contract

The best existing examples are:

- Backend resource with richer domain behavior:
  [backend/routine_routes.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/routine_routes.py),
  [backend/routine_services.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/routine_services.py),
  [backend/schemas.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/schemas.py),
  [tests/test_routines.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/tests/test_routines.py)
- Frontend list/detail feature with server-state, dialogs, and actions:
  [frontend/src/views/RoutinesView.vue](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/views/RoutinesView.vue),
  [frontend/src/views/RoutineDetailView.vue](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/views/RoutineDetailView.vue),
  [frontend/src/features/routines/useRoutinesPage.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/features/routines/useRoutinesPage.ts),
  [frontend/src/features/routines/queries/useRoutineQueries.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/features/routines/queries/useRoutineQueries.ts),
  [frontend/src/features/routines/mutations/useRoutineMutations.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/features/routines/mutations/useRoutineMutations.ts)
- Frontend simpler list-only feature:
  [frontend/src/views/UsersView.vue](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/views/UsersView.vue),
  [frontend/src/features/users/queries/useUsersQuery.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/features/users/queries/useUsersQuery.ts)
- OpenAPI export and frontend contract generation:
  [scripts/export_openapi.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/scripts/export_openapi.py),
  [frontend/package.json](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/package.json),
  [frontend/src/api/generated/schema.d.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/api/generated/schema.d.ts)
- Frontend contract-aware tests:
  [frontend/src/test/msw/handlers.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/test/msw/handlers.ts),
  [frontend/src/test/utils/render.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/test/utils/render.ts),
  [frontend/src/__tests__/UsersView.test.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/__tests__/UsersView.test.ts)

## The Approach

Work in this order:

1. Define the backend data model and invariants.
2. Add backend schema validation.
3. Add service-layer behavior.
4. Add route handlers and register them.
5. Add backend tests.
6. Export OpenAPI and regenerate frontend contract types.
7. Add frontend API module and type facade.
8. Add frontend query and mutation modules.
9. Add page composable and UI.
10. Add frontend tests.
11. Run the verification commands.

That order matters.

Why:

- The backend is the source of truth for shape and behavior.
- The frontend contract is generated from backend OpenAPI, so the backend must
  be stable before you generate types.
- Query and UI code should sit on top of a settled transport/API layer, not the
  other way around.
- Tests should prove the real contract, not a guessed one.

## Before You Start

Decide what kind of feature you are adding.

Examples:

- simple resource: `Device`, `Scene`, `WebhookTarget`
- nested resource: `RoutineAction` inside `Routine`
- list + detail + create/update/delete
- list-only admin view

Also decide:

- is it public or authenticated?
- does it have invariants beyond simple field validation?
- does it need a detail page?
- does it need polling or history?
- does it affect scheduler or background execution state?

If the feature has non-trivial rules, write those down first. This repo expects
important invariants to live in the backend, not only in the frontend.

## Part 1: Backend

### 1. Add or update the SQLAlchemy model

Add the model in [backend/models.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/models.py).

Follow the existing conventions:

- `Mapped[...]` annotations
- `mapped_column(...)`
- `DateTime(timezone=True)` for all datetime columns
- explicit foreign keys and relationships
- JSON columns only where flexible structure is genuinely needed

Why:

- This file is the schema source of truth for Alembic and for readers of the repo.
- Keeping datetimes timezone-aware from the start avoids later migration pain.

### 2. Add an Alembic migration

Create a migration after the model change:

```bash
just makemigrations "add my new resource"
```

Then review the generated migration carefully. Do not assume autogenerate got
everything right.

Why:

- This repo teaches explicit schema evolution, not “drop and recreate.”
- Migration review is where you catch wrong nullability, wrong defaults, and
  timezone drift.

### 3. Add request and response schemas

Add `Create`, `Update`, and `Response` schemas in
[backend/schemas.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/schemas.py).

Follow the pattern used by `RoutineCreate`, `RoutineUpdate`, and
`RoutineResponse`.

Important rules:

- `Create` schemas should validate complete payloads.
- `Update` schemas should support partial updates cleanly.
- For PATCH/PUT-style partial updates, use `model_fields_set` when behavior must
  distinguish “not provided” from explicit `null`.
- Response schemas should use `ConfigDict(from_attributes=True)` when they map
  directly from ORM objects.

Why:

- The schema layer is where request correctness becomes explicit.
- If you skip this and validate in route handlers, the contract gets fuzzy fast.
- Backend validation remains the source of truth even if the frontend also
  validates obvious mandatory fields.

### 4. Add service-layer behavior

Add business logic in a service module. For a CRUD feature, the routines service
is the reference:
[backend/routine_services.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/routine_services.py).

Keep the route layer thin. The service layer should own:

- create/update/delete behavior
- ordering rules
- uniqueness semantics
- cross-field invariants
- transactional rollback behavior

Why:

- Route handlers should not become mini service layers.
- This makes backend behavior testable without tying everything to HTTP details.

Examples from the repo:

- `update_routine()` preserves scheduler invariants and rollback safety.
- `create_action()` implements insert-and-shift semantics instead of relying on
  a raw uniqueness failure.

### 5. Add route handlers

Add route handlers in a new route module or extend an existing one.

Reference:
[backend/routine_routes.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/routine_routes.py)

Follow these patterns:

- use `APIRouter(prefix=..., tags=[...])`
- use `Annotated[Session, Depends(get_session)]`
- use small `get_*_or_404` dependencies for fetch-or-404
- convert service results into response models
- use `WriteDep` for authenticated write access where appropriate
- decorate handlers with `@handle_exception(logger)`

Why:

- This keeps status codes, auth gating, and dependency wiring consistent.
- Fetch-or-404 dependencies reduce duplication and make handlers easier to scan.

### 6. Register the router

Wire the router into [backend/main.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/main.py).

Why:

- The route does not exist until the app includes it.
- OpenAPI export will not include it otherwise.

### 7. Add backend tests before moving to the frontend

Add tests in `tests/test_<feature>.py` or extend an existing file.

Reference:
[tests/test_routines.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/tests/test_routines.py)

The minimum useful backend test set is:

- create success
- list success
- get-by-id success
- update success
- delete success
- 404 on missing resource
- 422 on validation/invariant violations
- auth gating for writes if the resource is protected

Add domain-specific tests too. For example:

- order compaction
- transition rules
- rollback behavior
- timestamp expectations

Why:

- The frontend depends on backend behavior being stable.
- OpenAPI gives shape, not behavioral correctness.

## Part 2: OpenAPI And Contract Flow

### 8. Export the backend OpenAPI schema

The frontend contract is generated from the backend OpenAPI schema using:

- [scripts/export_openapi.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/scripts/export_openapi.py)
- the `api:generate-types` script in [frontend/package.json](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/package.json)

Run:

```bash
cd frontend
npm run api:generate-types
```

This does two things:

1. exports `app.openapi()` to `src/api/generated/openapi.json`
2. generates TypeScript definitions in `src/api/generated/schema.d.ts`

Why:

- The frontend should consume the backend contract, not duplicate it by hand.
- This reduces drift in request/response shape assumptions.

### 9. Decide whether to create a frontend type facade

For richer domains, this repo sometimes uses a thin facade over generated types.

Reference:
[frontend/src/types/routine.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/types/routine.ts)

Use a facade when:

- the generated OpenAPI types are too noisy to use directly everywhere
- you want a cleaner domain type surface for the UI
- you still want the source of truth to be the generated schema

Do not create an unrelated handwritten duplicate if you can avoid it.

Why:

- A facade is acceptable; a second independent contract is not.

## Part 3: Frontend API And Server State

### 10. Add a frontend API module

Add a feature API module in `frontend/src/api/`.

Reference:
[frontend/src/api/routines.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/api/routines.ts)

Use the shared transport layer:
[frontend/src/api/client.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/api/client.ts)

Do not:

- call `fetch` directly from views
- reimplement token injection
- reimplement JSON/error parsing

Why:

- Transport concerns belong in one place.
- Feature API modules should describe endpoints, not HTTP mechanics.

### 11. Add query keys, query hooks, and mutation hooks

For anything beyond a trivial screen, use Vue Query.

References:

- [frontend/src/features/routines/queries/keys.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/features/routines/queries/keys.ts)
- [frontend/src/features/routines/queries/useRoutineQueries.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/features/routines/queries/useRoutineQueries.ts)
- [frontend/src/features/routines/mutations/useRoutineMutations.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/features/routines/mutations/useRoutineMutations.ts)

Create:

- query keys
- list query
- detail query if needed
- create/update/delete mutations
- any polling queries if the feature has active state

Always invalidate the right query keys after mutations.

Why:

- This repo no longer manages remote state manually inside views.
- Query invalidation is more reliable than hand-editing local arrays.

### 12. Add a page composable

For a screen with real behavior, add a page-level composable.

Reference:
[frontend/src/features/routines/useRoutinesPage.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/features/routines/useRoutinesPage.ts)

This composable should own:

- query hook composition
- loading/error projection
- dialog state
- form shaping
- client-side validation for obvious mandatory fields
- mutation calls
- view-friendly helper functions

Why:

- Views stay readable.
- Tests can focus on behavior rather than huge page components.
- Validation rules belong closer to form orchestration than to leaf input
  components.

### 13. Add client-side validation for mandatory fields

Backend validation is still authoritative, but new forms should also validate
the most obvious mandatory fields before submit.

Examples:

- required names
- required messages
- positive numeric intervals
- required cron strings when the selected mode is cron

In this repo, the preferred split is:

- backend schemas enforce correctness
- page composables decide validation rules and submit behavior
- reusable form components render field errors

For simple forms, composable-level validation is acceptable.

For heavier forms, prefer a schema-based client validation layer so rules do not
spread across submit handlers.

Why:

- Users should not have to wait for a round trip to learn a name is required.
- Keeping backend validation as the source of truth prevents client/backend drift.
- Keeping error display in reusable components prevents page templates from
  becoming noisy.

### 14. Build the UI from the composable

Put the page component under `frontend/src/views/` and extract reusable pieces
under `frontend/src/features/<feature>/components/` as needed.

References:

- [frontend/src/views/RoutinesView.vue](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/views/RoutinesView.vue)
- [frontend/src/views/RoutineDetailView.vue](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/views/RoutineDetailView.vue)
- [frontend/src/features/routines/components/RoutineFormFields.vue](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/features/routines/components/RoutineFormFields.vue)

Use PrimeVue primitives where appropriate:

- `DataTable`
- `Dialog`
- `Button`
- `Select`
- `Tag`
- `Toast`

Why:

- The repo already standardized on PrimeVue + Tailwind.
- Reusing the component layer avoids drifting back to one-off UI patterns.

### 15. Add the route

Add the route in [frontend/src/router/index.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/router/index.ts).

Follow the current rules:

- lazy-load route views
- use route meta for `requiresAuth` or `publicOnly`
- keep redirect behavior explicit

Why:

- Route-level policy is easier to audit than scattered in-view redirects.

## Part 4: Frontend Tests

### 16. Add MSW handlers shaped from the OpenAPI contract

Add handlers in:
[frontend/src/test/msw/handlers.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/test/msw/handlers.ts)

Use generated types from:
[frontend/src/api/generated/schema.d.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/api/generated/schema.d.ts)

Why:

- This is the main “UI without full E2E” strategy in this repo.
- It keeps tests fast while staying close to the real API contract.

### 17. Add API and component tests

Use:

- API tests for the feature API layer
- component tests for the view/composable behavior
- component tests for client-side validation behavior when the feature has forms

References:

- [frontend/src/__tests__/api.auth.test.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/__tests__/api.auth.test.ts)
- [frontend/src/__tests__/api.routines.test.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/__tests__/api.routines.test.ts)
- [frontend/src/__tests__/UsersView.test.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/__tests__/UsersView.test.ts)
- [frontend/src/test/utils/render.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/test/utils/render.ts)

The shared mount helper already wires:

- Pinia
- Vue Router
- Vue Query
- PrimeVue
- Toast service

Use it rather than building a one-off mount stack every time.

Why:

- Test harness drift is a real maintenance cost.
- Shared render setup makes tests reflect the real app environment.

### 18. Add Playwright only for real browser value

If the feature needs browser-level proof, add a small Playwright test.

Use Playwright for:

- route guards
- navigation flows
- browser-only behavior
- accessibility smoke checks

Do not use Playwright as your main feature test layer if Vitest + MSW can prove
the behavior more cheaply.

References:

- [frontend/e2e/auth.spec.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/e2e/auth.spec.ts)
- [frontend/e2e/routines.spec.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/e2e/routines.spec.ts)
- [frontend/e2e/accessibility.spec.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/e2e/accessibility.spec.ts)

Why:

- This repo follows a test pyramid with a thick middle, not an E2E-heavy model.

## Part 5: Recommended Implementation Order

If you are adding a new resource called `Device`, do it in this order:

1. Add `Device` model to `backend/models.py`.
2. Generate and review Alembic migration.
3. Add `DeviceCreate`, `DeviceUpdate`, `DeviceResponse` schemas.
4. Add `device_services.py` with list/get/create/update/delete behavior.
5. Add `device_routes.py` and include the router in `backend/main.py`.
6. Add `tests/test_devices.py`.
7. Run backend tests.
8. Run `cd frontend && npm run api:generate-types`.
9. Add `frontend/src/api/devices.ts`.
10. Add `frontend/src/types/device.ts` only if a thin facade is useful.
11. Add `frontend/src/features/devices/queries/keys.ts`.
12. Add query and mutation modules.
13. Add `useDevicesPage.ts`.
14. Add client-side validation for required fields and obvious invalid states.
15. Add `DevicesView.vue` and `DeviceDetailView.vue` if needed.
16. Register routes in `frontend/src/router/index.ts`.
17. Add MSW handlers and Vitest tests.
18. Add one Playwright test only if browser-only behavior matters.
19. Run the full verification commands.

Why this order:

- Every step depends on the previous layer being real.
- You avoid building UI against a guessed backend.
- You keep contract generation in the middle, where it belongs.

## What To Copy Vs What To Adapt

Copy these patterns:

- route -> service split
- OpenAPI export -> generated schema flow
- shared frontend API client
- Vue Query query/mutation modules
- page composables
- MSW + shared render helper

Adapt these parts:

- exact UI shape
- auth rules
- whether you need detail pages
- whether you need nested resources
- whether your domain needs scheduler/background execution semantics

Do not copy blindly:

- routines-specific schedule validation
- action reordering semantics
- execution polling behavior

Those exist because the routines domain needs them.

## Common Mistakes To Avoid

- Putting `fetch` directly in Vue views.
- Duplicating transport logic instead of using `api/client.ts`.
- Keeping remote data in Pinia instead of Vue Query.
- Writing large route components that own fetching, mutation, form shaping, and dialogs all at once.
- Treating OpenAPI as optional after the backend changes.
- Relying only on backend round trips for obvious required-field UX.
- Mocking API modules everywhere instead of using MSW at the request boundary.
- Using naive datetimes in new backend models.
- Letting backend invariants live only in the frontend.

## Verification Checklist

Backend:

```bash
poetry run ruff check backend tests
poetry run pytest tests/test_<feature>.py
```

Frontend:

```bash
cd frontend
npm run api:generate-types
npm run lint
npm test
npm run build
```

If you added Playwright coverage:

```bash
cd frontend
npx playwright test
```

## Short Version

Backend first, contract second, frontend third, tests throughout.

If you follow the routines/users patterns in this repo, a new CRUD feature should
look like this:

- SQLAlchemy model + Alembic migration
- Pydantic create/update/response schemas
- service layer with domain invariants
- thin FastAPI route handlers
- backend pytest coverage
- OpenAPI export and generated frontend types
- frontend API module on shared client
- Vue Query queries and mutations
- page composable
- client-side required-field validation
- PrimeVue/Tailwind UI
- MSW-backed Vitest tests
- optional Playwright smoke coverage
