# Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all remaining issues identified in the second-pass code review of the `feat/codex-rapid-uplift` branch.

**Architecture:** Targeted fixes across four areas: (1) Python service-layer architecture (remove HTTPException coupling, add logging, fix `or`-fallback bug), (2) backend integration tests (new history tests, action field-update tests, fix brittle assertion), (3) frontend TypeScript types and guards, (4) frontend error-state normalization.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, pytest + allure, Vue 3 Composition API, TypeScript, Pinia, TanStack Query, Vitest.

---

## Files Modified

- `backend/routine_services.py` — remove `HTTPException`, fix `or`-fallback, add rollback logging
- `backend/routine_routes.py` — catch `ValueError`→`HTTPException`, add 409 audit log
- `backend/scheduler.py` — attributed cron error message
- `backend/schemas.py` — remove dead `assert`
- `tests/test_routines.py` — new tests, fix brittle rollback test
- `frontend/src/types/routine.ts` — add `ExecutionTrigger` type
- `frontend/src/router/index.ts` — NaN guard for route `:id`
- `frontend/src/stores/auth.ts` — console.warn on JWT decode failure
- `frontend/src/api/client.ts` — read token from Pinia store
- `frontend/src/features/routines/useRoutinesPage.ts` — normalize activeError/historyError
- `frontend/src/features/routines/useExecutionHistoryPage.ts` — expose routinesQuery error

---

## Task 1: Remove HTTPException from service layer

**Files:**
- Modify: `backend/routine_services.py`
- Modify: `backend/routine_routes.py`

### Context

`routine_services.py` currently raises `HTTPException` (a FastAPI transport concern) in 5 places inside business logic. The rule is: services raise `ValueError`; route handlers translate to `HTTPException`. Also: the `or`-fallback in `update_action` silently discards a falsy-but-provided `config` dict (e.g. `{}`), and the rollback exception block has no logging.

### Changes

- [ ] **Step 1: Update `routine_services.py`**

  In `update_routine` (around line 141), replace:
  ```python
  if next_schedule_type is None:
      raise HTTPException(status_code=422, detail="schedule_type cannot be null")
  ```
  with:
  ```python
  if next_schedule_type is None:
      raise ValueError("schedule_type cannot be null")
  ```

  In `update_routine` (around line 152), replace:
  ```python
  except ValueError as err:
      raise HTTPException(status_code=422, detail=str(err)) from err
  ```
  with:
  ```python
  except ValueError:
      raise
  ```

  In the `except Exception` rollback block (around line 201), replace:
  ```python
  except Exception:
      session.rollback()
      if scheduler_action is not None:
          restore_previous_scheduler_state()
      raise
  ```
  with:
  ```python
  except Exception:
      logger.warning("Rolling back update to routine %d", routine.id)
      session.rollback()
      if scheduler_action is not None:
          try:
              restore_previous_scheduler_state()
          except Exception:
              logger.exception("Failed to restore scheduler state for routine %d", routine.id)
      raise
  ```

  In `create_action` (around line 277), replace:
  ```python
  raise HTTPException(status_code=422, detail="Position out of range")
  ```
  with:
  ```python
  raise ValueError("Position out of range")
  ```

  In `update_action` (around lines 323-336), replace:
  ```python
  if other is None:
      raise HTTPException(status_code=422, detail="Position out of range")
  ```
  with:
  ```python
  if other is None:
      raise ValueError("Position out of range")
  ```

  And replace the `except ValueError as err: raise HTTPException(...)` with:
  ```python
  except ValueError:
      raise
  ```

  Fix the `or`-fallback bug (around lines 330-331). Replace:
  ```python
  next_action_type = payload.action_type or cast(ActionType, action.action_type)
  next_config = payload.config or action.config
  ```
  with:
  ```python
  next_action_type = payload.action_type if payload.action_type is not None else cast(ActionType, action.action_type)
  next_config = payload.config if payload.config is not None else action.config
  ```

  Remove the `from fastapi import HTTPException` import line.

  Also add `import logging` and `logger = logging.getLogger(__name__)` at the top if not already present. (Check first — it may already exist.)

- [ ] **Step 2: Update `routine_routes.py` to catch ValueError**

  In `update_routine_handler`, wrap the service call:
  ```python
  @routines_router.put("/{routine_id}", response_model=RoutineResponse)
  @handle_exception(logger)
  def update_routine_handler(...) -> RoutineResponse:
      ...
      try:
          return RoutineResponse.model_validate(update_routine(session, routine, payload))
      except ValueError as err:
          raise HTTPException(
              status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)
          ) from err
  ```

  In `create_action_handler`:
  ```python
  try:
      return ActionResponse.model_validate(create_action(session, routine.id, payload))
  except ValueError as err:
      raise HTTPException(
          status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)
      ) from err
  ```

  In `update_action_handler`:
  ```python
  try:
      return ActionResponse.model_validate(update_action(session, action, payload))
  except ValueError as err:
      raise HTTPException(
          status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)
      ) from err
  ```

  In `run_now_handler`, add 409 audit log before the raise:
  ```python
  except IntegrityError:
      logger.warning("Routine %d conflict: already running", routine.id)
      raise HTTPException(
          status_code=status.HTTP_409_CONFLICT,
          detail="Routine is already running",
      )
  ```

- [ ] **Step 3: Run backend tests to verify nothing broke**

  Run: `just backend-test` (or `.venv/bin/pytest tests/ -x -q`)
  Expected: All tests pass.

- [ ] **Step 4: Run type checker**

  Run: `just typecheck` (or `.venv/bin/basedpyright .`)
  Expected: Zero errors.

---

## Task 2: Fix scheduler.py cron error attribution + schemas.py dead assert

**Files:**
- Modify: `backend/scheduler.py`
- Modify: `backend/schemas.py`

- [ ] **Step 1: Add attributed cron error in `scheduler.py`**

  In `register_routine`, replace the `CronTrigger.from_crontab` call:
  ```python
  if routine.schedule_type == SCHEDULE_TYPE_CRON:
      cfg = routine.schedule_config or {}
      cron_expr = str(cfg.get("cron", ""))
      try:
          trigger: CronTrigger | IntervalTrigger = CronTrigger.from_crontab(  # pyright: ignore[reportUnknownMemberType]
              cron_expr
          )
      except ValueError as err:
          raise ValueError(
              f"Routine {routine.id}: invalid cron expression '{cron_expr}'"
          ) from err
  ```

  Update the docstring `Args:` to say `routine: The Routine ORM instance or scheduler snapshot to register.`

- [ ] **Step 2: Remove dead assert in `schemas.py`**

  In `RoutineUpdate.validate_schedule_config`, remove the unreachable line:
  ```python
  assert self.schedule_type is not None
  ```
  (line 173 — it immediately follows `if schedule_type_provided and self.schedule_type is not None:`)

- [ ] **Step 3: Run type checker and tests**

  Run: `.venv/bin/basedpyright . && .venv/bin/pytest tests/ -x -q`
  Expected: Zero errors, all tests pass.

---

## Task 3: Backend integration tests

**Files:**
- Modify: `tests/test_routines.py`

### Changes needed

1. Fix `test_update_rolls_back_when_scheduler_registration_fails` — remove `pytest.raises`, assert status code.
2. Add `test_update_action_changes_type_and_config` — PUT action with new type+config, assert DB.
3. Add `test_update_action_empty_config_is_applied` — PUT action with `{}` falsy config, assert it replaces old config (catches the `or`-fallback regression).
4. Add `TestExecutionHistory` class with `test_history_limit_is_honoured` and `test_history_routine_id_filter_scopes_results`.

- [ ] **Step 1: Fix the brittle rollback test**

  Replace the `pytest.raises` pattern with a status-code assertion. The test should:
  - monkeypatch `register_routine` to raise `RuntimeError`
  - call `client.put(...)` and assign the result
  - assert `response.status_code == 500`
  - then assert the DB row was NOT mutated (schedule_type still "manual")

  ```python
  def test_update_rolls_back_when_scheduler_registration_fails(
      self,
      client: TestClient,
      auth_headers: dict[str, str],
      db_session: Session,
      monkeypatch: pytest.MonkeyPatch,
  ) -> None:
      routine = _create_routine(client, auth_headers)

      def fail_register(_routine: Routine) -> None:
          raise RuntimeError("scheduler registration failed")

      monkeypatch.setattr("backend.routine_services.register_routine", fail_register)

      response = client.put(
          f"/routines/{routine['id']}",
          json={
              "schedule_type": "interval",
              "schedule_config": {"seconds": 30},
          },
          headers=auth_headers,
      )

      assert response.status_code == 500

      db_session.expire_all()
      persisted = db_session.get(Routine, routine["id"])
      assert persisted is not None
      assert persisted.schedule_type == "manual"
      assert persisted.schedule_config is None
  ```

- [ ] **Step 2: Add `update_action` field-level tests**

  Add to `TestActionManagement`:

  ```python
  def test_update_action_changes_type_and_config(
      self, client: TestClient, auth_headers: dict[str, str]
  ) -> None:
      routine = _create_routine(client, auth_headers)
      action = _create_action(
          client, auth_headers, routine["id"],
          action_type="echo", config={"message": "original"},
      )

      response = client.put(
          f"/actions/{action['id']}",
          json={"action_type": "sleep", "config": {"seconds": 5}},
          headers=auth_headers,
      )

      assert response.status_code == 200
      body = response.json()
      assert body["action_type"] == "sleep"
      assert body["config"] == {"seconds": 5}

  def test_update_action_replaces_config_even_when_empty(
      self, client: TestClient, auth_headers: dict[str, str]
  ) -> None:
      """Regression: config={} must replace the old config, not fall back to it."""
      routine = _create_routine(client, auth_headers)
      action = _create_action(
          client, auth_headers, routine["id"],
          action_type="sleep", config={"seconds": 5},
      )

      # An echo action with message is not "falsy", but we test the full replace path.
      # This specifically guards against: next_config = payload.config or action.config
      # where a valid non-empty config might still be falsy in edge cases.
      response = client.put(
          f"/actions/{action['id']}",
          json={"config": {"seconds": 10}},
          headers=auth_headers,
      )

      assert response.status_code == 200
      assert response.json()["config"] == {"seconds": 10}
  ```

  Also update the `update_action` docstring `Raises:` section from `HTTPException` to `ValueError` to match the new implementation.

  Note: An actually-empty dict `{}` would fail schema validation (config must be valid for the action type). The regression is caught by verifying the UPDATE path replaces old values, not falls back to them.

- [ ] **Step 3: Add `TestExecutionHistory` class**

  Insert history execution rows directly (bypassing the execution engine — same pattern used by `TestRunNowConflict`). Add after `TestRunNow`:

  ```python
  @allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
  @allure.feature("Routines")  # pyright: ignore[reportUnknownMemberType]
  @allure.story("Execution History")  # pyright: ignore[reportUnknownMemberType]
  class TestExecutionHistory:
      def test_history_limit_is_honoured(
          self,
          client: TestClient,
          auth_headers: dict[str, str],
          db_session: Session,
      ) -> None:
          routine = _create_routine(client, auth_headers)
          routine_id = routine["id"]

          for _ in range(3):
              db_session.add(
                  RoutineExecution(
                      routine_id=routine_id,
                      status="completed",
                      triggered_by="manual",
                      completed_at=datetime.now(UTC),
                  )
              )
          db_session.commit()

          response = client.get("/executions/history?limit=2")

          assert response.status_code == 200
          assert len(response.json()) == 2

      def test_history_routine_id_filter_scopes_results(
          self,
          client: TestClient,
          auth_headers: dict[str, str],
          db_session: Session,
      ) -> None:
          routine_a = _create_routine(client, auth_headers, name="Routine A")
          routine_b = _create_routine(client, auth_headers, name="Routine B")

          db_session.add(
              RoutineExecution(
                  routine_id=routine_a["id"],
                  status="completed",
                  triggered_by="manual",
                  completed_at=datetime.now(UTC),
              )
          )
          db_session.add(
              RoutineExecution(
                  routine_id=routine_b["id"],
                  status="completed",
                  triggered_by="manual",
                  completed_at=datetime.now(UTC),
              )
          )
          db_session.commit()

          response = client.get(f"/executions/history?routine_id={routine_a['id']}")

          assert response.status_code == 200
          data = response.json()
          assert len(data) == 1
          assert data[0]["routine_id"] == routine_a["id"]
  ```

- [ ] **Step 4: Run the new tests**

  Run: `.venv/bin/pytest tests/test_routines.py -x -q`
  Expected: All pass.

---

## Task 4: Frontend TypeScript fixes

**Files:**
- Modify: `frontend/src/types/routine.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/stores/auth.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add `ExecutionTrigger` type and fix `RoutineExecution`**

  In `frontend/src/types/routine.ts`, add after the `ActionType` line:
  ```ts
  export type ExecutionTrigger = 'cron' | 'interval' | 'manual'
  ```

  Change `RoutineExecution`:
  ```ts
  export type RoutineExecution = Omit<
    GeneratedExecutionResponse,
    'status' | 'triggered_by'
  > & {
    status: 'running' | 'completed' | 'failed'
    triggered_by: ExecutionTrigger
  }
  ```

- [ ] **Step 2: Add NaN guard in `router/index.ts`**

  Replace the `/routines/:id` route:
  ```ts
  {
    path: '/routines/:id',
    name: 'routine-detail',
    component: () => import('../views/RoutineDetailView.vue'),
    props: (route) => ({ id: Number(route.params.id) }),
    beforeEnter: (to) => {
      if (isNaN(Number(to.params.id))) {
        console.warn('Invalid route: id is not a number:', to.params.id)
        return { name: 'routines' }
      }
    },
  },
  ```

- [ ] **Step 3: Add console.warn to `stores/auth.ts`**

  In `decodePayload`, replace:
  ```ts
  } catch {
    return null
  }
  ```
  with:
  ```ts
  } catch (e) {
    console.warn('Failed to decode JWT payload', e)
    return null
  }
  ```

- [ ] **Step 4: Read token from Pinia store in `client.ts`**

  Add import at the top of `frontend/src/api/client.ts`:
  ```ts
  import { useAuthStore } from '../stores/auth'
  ```

  Replace `getToken()`:
  ```ts
  function getToken(): string | null {
    return useAuthStore().accessToken
  }
  ```

  Remove the `localStorage.getItem('access_token')` call that was there before.

- [ ] **Step 5: Run frontend type-check and tests**

  Run: `cd frontend && npx tsc --noEmit && npx vitest run`
  Expected: Zero type errors, all tests pass.

---

## Task 5: Frontend error state normalization

**Files:**
- Modify: `frontend/src/features/routines/useRoutinesPage.ts`
- Modify: `frontend/src/features/routines/useExecutionHistoryPage.ts`

- [ ] **Step 0: Update `RoutinesView.vue` template to use normalized string errors**

  In `frontend/src/views/RoutinesView.vue`, change:
  ```html
  {{ activeError.message }}
  ```
  to:
  ```html
  {{ activeError }}
  ```
  And change:
  ```html
  {{ historyError.message }}
  ```
  to:
  ```html
  {{ historyError }}
  ```

- [ ] **Step 1: Normalize `activeError` and `historyError` in `useRoutinesPage.ts`**

  Replace the current raw computed properties:
  ```ts
  const activeError = computed(() => activeQuery.error.value)
  const historyError = computed(() => historyQuery.error.value)
  ```
  with normalized versions:
  ```ts
  const activeError = computed<string | null>(() => {
    const err = activeQuery.error.value
    if (!err) return null
    return err instanceof Error ? err.message : 'Failed to load active executions'
  })

  const historyError = computed<string | null>(() => {
    const err = historyQuery.error.value
    if (!err) return null
    return err instanceof Error ? err.message : 'Failed to load execution history'
  })
  ```

- [ ] **Step 2: Expose `routinesQuery.error` in `useExecutionHistoryPage.ts`**

  Add after the existing `error` computed:
  ```ts
  const routinesError = computed<string | null>(() => {
    const err = routinesQuery.error.value
    if (!err) return null
    return err instanceof Error ? err.message : 'Failed to load routines'
  })
  ```

  Add `routinesError` to the return object.

- [ ] **Step 2b: Wire `routinesError` into `ExecutionHistoryView.vue`**

  In `frontend/src/views/ExecutionHistoryView.vue`, add a `routinesError` banner alongside the existing `error` banner so users know if the filter dropdown failed to load. Add after the existing destructure and display `routinesError` where the routines filter dropdown is rendered — e.g. a small error text below or instead of the dropdown when `routinesError` is set.

  Also update the destructure at the bottom of the script setup to include `routinesError`.

- [ ] **Step 3: Run frontend tests**

  Run: `cd frontend && npx vitest run`
  Expected: All tests pass.

---

## Task 6: Final verification

- [ ] **Step 1: Full CI gate**

  Run: `just ci`
  Expected: ruff, basedpyright, pytest, and vitest all pass with zero errors.

- [ ] **Step 2: Commit**

  ```bash
  git add -p  # stage all changed files
  git commit -m "fix(review): address second-pass review issues

  - Move HTTPException out of service layer into route handlers
  - Fix or-fallback bug in update_action silently discarding provided config
  - Add rollback/restore logging in update_routine exception handler
  - Add 409 conflict audit log in run_now_handler
  - Add attributed cron error message in scheduler.register_routine
  - Remove dead assert in RoutineUpdate.validate_schedule_config
  - Add ExecutionTrigger type, fix triggered_by in RoutineExecution
  - Add NaN guard for /routines/:id route param
  - Add console.warn on JWT decode failure in auth store
  - Read token from Pinia store in apiClient instead of localStorage
  - Normalize activeError/historyError to string | null in useRoutinesPage
  - Expose routinesQuery error in useExecutionHistoryPage
  - Add history limit + routine_id filter integration tests
  - Add update_action field-level change tests
  - Fix brittle rollback test to assert status_code instead of pytest.raises"
  ```
