# Home Automation Routines — Design Spec

**Date:** 2026-03-21
**Status:** Approved

---

## Overview

Extend the existing FastAPI + Vue 3 application with a **Home Automation Routines** domain. A Routine is a named, ordered sequence of Actions that executes on a cron schedule, a repeating interval, or immediately on demand. The primary learning goal is well-structured Vue 3 patterns: reactive CRUD tables, a reusable polling composable, and dynamic multi-panel home page updates.

---

## Domain Model

### Routine

A named automation that owns an ordered list of Actions and a schedule.

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `name` | String | Required |
| `description` | String | Nullable |
| `schedule_type` | Enum | `cron` \| `interval` \| `manual` |
| `schedule_config` | JSON | Required when `schedule_type` is `cron` or `interval`; must be `null` when `schedule_type` is `manual`. `cron` requires `{"cron": "<cron expression>"}`. `interval` requires `{"seconds": <integer>}`. Any other shape is rejected with 422. |
| `is_active` | Boolean | Whether APScheduler should register this routine. Defaults to `True`. |
| `created_at` | DateTime | Server default `now()` |

### Action

An ordered step within a Routine. Two types are supported initially.

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `routine_id` | Integer | FK → `routines` (cascade delete) |
| `position` | Integer | 1-based ordering within the routine. Must be unique per routine. |
| `action_type` | Enum | `sleep` \| `echo` |
| `config` | JSON | `{"seconds": <positive integer>}` for `sleep`; `{"message": "<string>"}` for `echo`. Validated by Pydantic discriminated union on `action_type`. |

### RoutineExecution

An append-only record of each time a Routine ran. Rows are never deleted.

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `routine_id` | Integer | FK → `routines` (cascade delete) |
| `status` | Enum | `running` \| `completed` \| `failed` |
| `triggered_by` | Enum | `cron` \| `interval` \| `manual` — mirrors the `schedule_type` value of the routine at the time of execution |
| `started_at` | DateTime | Set on creation |
| `completed_at` | DateTime | Nullable — set when status transitions to `completed` or `failed` |

> **Note:** `triggered_by` values are intentionally the same labels as `schedule_type`. They are not independent — `triggered_by` records the `schedule_type` of the routine at the moment the execution was created.

### Database Constraints

- A unique partial index on `(routine_id)` where `status = 'running'` enforces the single-execution-per-routine invariant at the database level, preventing race conditions when concurrent Run Now requests arrive simultaneously.

---

## Backend Architecture

### Scheduler Lifecycle

`APScheduler.BackgroundScheduler` is created and started inside the FastAPI `lifespan` context manager. On startup it queries all `is_active=True` routines and registers their jobs using `CronTrigger` or `IntervalTrigger` respectively. Manual routines are not registered with APScheduler.

The scheduler is conditionally started based on `settings.scheduler_enabled`. When `scheduler_enabled=False` (test environments), the `lifespan` handler skips starting the scheduler entirely. The scheduler instance is stored as application state (`app.state.scheduler`) so route handlers can access it for add/remove operations.

### Scheduler Sync on Mutation

When routines are created, updated, or deleted, the service layer must keep APScheduler in sync:

| Operation | APScheduler action |
|---|---|
| Create routine, `is_active=True`, non-manual | Add job via `scheduler.add_job(...)` using the routine's `id` as the job ID |
| Create routine, `is_active=False` or `manual` | No scheduler action |
| Update routine — `is_active` toggled to `False` | `scheduler.remove_job(routine_id)` if job exists |
| Update routine — `is_active` toggled to `True` | `scheduler.add_job(...)` with new schedule |
| Update routine — schedule changed, `is_active=True` | `scheduler.reschedule_job(routine_id, trigger=...)` |
| Delete routine | `scheduler.remove_job(routine_id)` if job exists |

### Execution Engine — Session Boundaries

The execution engine runs in APScheduler's thread pool. It must **not** reuse an HTTP-request-scoped SQLAlchemy session. Instead, it creates its own short-lived sessions using the session factory directly:

1. **Session 1** — insert `routine_executions` row with `status=running`, commit, close.
2. **Session 2** — load the routine's actions ordered by `position`, close immediately after load.
3. Execute each action synchronously (`time.sleep` / `logger.info`). No session is held open during `sleep`.
4. **Session 3** — update execution row to `completed` or `failed`, set `completed_at`, commit, close.

This three-session pattern avoids holding a connection pool slot open across potentially long `sleep` actions.

### Execution Engine — Run Flow

```
insert execution row (status=running)
for action in actions ordered by position:
    if action_type == "sleep": time.sleep(config["seconds"])
    if action_type == "echo":  logger.info(config["message"])
update execution row (status=completed, completed_at=now())
# on any unhandled exception:
update execution row (status=failed, completed_at=now())
logger.exception(...)
```

### API Surface

| Method | Path | Success | Notes |
|---|---|---|---|
| `GET` | `/routines` | `200` | Returns list of all routines |
| `POST` | `/routines` | `201` | Creates routine; registers scheduler job if applicable |
| `GET` | `/routines/{id}` | `200` | Returns routine with actions |
| `PUT` | `/routines/{id}` | `200` | Updates routine; syncs scheduler per table above |
| `DELETE` | `/routines/{id}` | `204` | Deletes routine + cascade (actions, executions); removes scheduler job |
| `GET` | `/routines/{id}/actions` | `200` | Returns actions ordered by `position` |
| `POST` | `/routines/{id}/actions` | `201` | Appends action at end (position = max + 1) |
| `PUT` | `/actions/{id}` | `200` | Updates action type, config, or position (see reorder contract below) |
| `DELETE` | `/actions/{id}` | `204` | Removes action; compacts remaining positions to fill gap |
| `POST` | `/routines/{id}/run` | `202` | Triggers immediate execution; returns `{"execution_id": <id>}`. Returns `409` if a `running` execution already exists (enforced by DB unique partial index). |
| `GET` | `/executions/active` | `200` | All executions with `status=running`, ordered by `started_at desc` |
| `GET` | `/executions/history` | `200` | Completed/failed executions. Accepts `?limit=N` (default 10, max 100) and `?routine_id=N` filter. Ordered by `started_at desc`. |

### Action Reorder Contract

Pressing "up" or "down" on the detail page calls `PUT /actions/{id}` with `{"position": <new_position>}`. The server swaps the target action's position with the action currently occupying `new_position` within the same routine (a two-row swap). If `new_position` is out of range (< 1 or > count), the server returns `422`.

### Cascade Delete

When a routine is deleted:
- All `actions` rows with `routine_id` are deleted (DB-level cascade on FK)
- All `routine_executions` rows with `routine_id` are deleted (DB-level cascade on FK)
- The APScheduler job is removed if it exists

Cascades are defined at the SQLAlchemy model level using `cascade="all, delete-orphan"`.

### Configuration

New settings added to `backend/config.py`:

```python
scheduler_enabled: bool = True
```

When `False`, the `lifespan` handler skips `scheduler.start()`. Tests set this via the `pyproject.toml` `[tool.pytest-env]` block (existing pattern).

---

## Frontend Architecture

### `usePolling(fn, intervalMs)` Composable

The core Vue learning pattern. Signature:

```ts
function usePolling<T>(
  fn: () => Promise<T>,
  intervalMs: number
): { data: Ref<T | null>; loading: Ref<boolean>; error: Ref<Error | null>; refresh: () => Promise<void> }
```

Behaviour:
- Calls `fn` immediately on mount (initial fetch)
- `loading` is `true` only during the initial fetch; subsequent polls do not set `loading`
- Sets up `setInterval(fn, intervalMs)` after the initial fetch completes
- Calls `clearInterval` in `onUnmounted` — no interval leaks on navigation
- On poll error: sets `error` ref; does not clear `data` (last-good data remains visible); continues polling
- `refresh()` — calls `fn` immediately outside the interval cycle; useful for post-mutation updates

### Initial Load UX

During the initial fetch (`loading === true`), each polling panel displays a spinner. Once data is available, the spinner is replaced by the table (even if the table is empty). On poll error, a subtle error banner is shown below the table title; the table data remains visible.

### Home Page Panels

**Configured Routines**
Standard CRUD table. After create/edit/delete, the local `ref` array is mutated directly — no re-fetch needed. Each row has Edit, Delete, and Run Now buttons. Run Now posts to `POST /routines/{id}/run`; on `202` it calls `refresh()` on the executing panel composable so the new execution appears without waiting for the next poll cycle. On `409` it shows an inline warning ("Already running").

**Currently Executing**
Uses `usePolling(fetchActiveExecutions, 3000)`. Displays routine name, triggered-by badge, and elapsed time (computed client-side from `started_at`). Rows appear and disappear based on `status=running`.

**Recent History**
Uses `usePolling(fetchExecutionHistory, 5000)` with `limit=10`. Displays routine name, status badge, triggered-by, and duration (`completed_at - started_at`).

### Additional Pages

**Routine Detail / Edit**
- Form fields: name, description, schedule type selector, schedule config (cron expression input or seconds input shown conditionally)
- Action list: ordered by `position`, each row has up/down buttons and a delete button. Up/down calls `PUT /actions/{id}` with swapped position.
- Add action form at bottom: select type, fill config, submit appends to list
- Run Now button — same behaviour as home page row button

**Execution History Page**
- Full paginated history using `?limit` and `?routine_id` query params
- Filter dropdown to scope by routine

### Navigation

Two new entries in `AppNavbar`:
- **Routines** → home page (three-panel view)
- **History** → full execution history page

---

## Testing

### Backend

- Real PostgreSQL via testcontainers (existing pattern)
- `scheduler_enabled=False` set via `pyproject.toml` `[tool.pytest-env]`; APScheduler never starts during tests
- The execution engine function is called directly in tests (not via the scheduler)
- Test coverage:
  - Routine CRUD (create, read, update, delete with cascade verification)
  - `schedule_config` validation (valid cron, valid interval, null for manual, reject mismatched shapes)
  - Action CRUD including position compaction on delete and position swap on reorder
  - Execution lifecycle: `running` → `completed`, `running` → `failed`
  - `409` conflict guard (DB unique partial index enforces it; test inserts a `running` row then calls run again)
  - `GET /executions/history` with `limit` and `routine_id` filters

### Frontend

- **Vitest**: `usePolling` with `vi.useFakeTimers()` (advance timers, assert calls, assert `clearInterval` on unmount), API client functions, key component rendering
- **Playwright E2E**: create a routine with `echo` + `sleep` actions → click Run Now → assert row appears in executing panel → wait for it to move to history panel

### Allure

All backend test classes decorated with `@allure.feature("Routines")` and appropriate `@allure.story(...)` per project standards. Frontend Vitest and Playwright tests use `allure-vitest` and `@allure-js/playwright` respectively.

---

## Migration Strategy

Two Alembic migrations in dependency order:

1. `add_routines_and_actions_tables` — creates `routines` and `actions` tables. `actions.routine_id` FK references `routines.id`. Also creates the unique partial index on `routine_executions(routine_id) WHERE status = 'running'`... (correction: this index belongs in migration 2).
2. `add_routine_executions_table` — creates `routine_executions` table with FK to `routines.id`, plus the unique partial index on `(routine_id) WHERE status = 'running'`.

Migration 2 depends on migration 1 because `routine_executions.routine_id` references `routines.id`.

Existing `sequences` table and routes remain untouched. The new domain lives alongside the existing one.

---

## Action Types — Extensibility Note

`sleep` and `echo` are the two initial action types. The `action_type` enum and `config` JSON field are intentionally open — adding a `http_request` or `home_assistant` type later requires only a new branch in the execution engine and a new Pydantic config schema, with no structural DB changes.

---

## Out of Scope (This Phase)

- Step-level execution progress (routine-level status only)
- Real smart home device integration
- WebSockets / SSE (polling is sufficient and simpler to learn first)
- Drag-to-reorder actions (up/down buttons cover the learning goal)
- Multi-user routine ownership
- Optimistic UI updates (post-Run Now response body carries `execution_id` for future use, not consumed yet)
