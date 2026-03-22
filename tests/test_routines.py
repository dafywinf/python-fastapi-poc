"""Tests for the Routines, Actions, and Execution endpoints."""

from typing import Any

import allure
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

import backend.database as _db_module
import backend.execution_engine as _engine_module
from backend.models import RoutineExecution

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_routine(
    client: TestClient,
    auth_headers: dict[str, str],
    **overrides: Any,
) -> dict[str, Any]:
    """POST a routine with auth and return the parsed response body.

    Args:
        client: The test HTTP client.
        auth_headers: Authorization headers containing a valid Bearer token.
        **overrides: Fields to override in the default payload.

    Returns:
        The parsed JSON response body of the created Routine.
    """
    payload: dict[str, Any] = {
        "name": "Test Routine",
        "schedule_type": "manual",
        "schedule_config": None,
        "is_active": True,
        **overrides,
    }
    response = client.post("/routines/", json=payload, headers=auth_headers)
    assert response.status_code == 201
    return response.json()  # type: ignore[no-any-return]


def _create_action(
    client: TestClient,
    auth_headers: dict[str, str],
    routine_id: int,
    action_type: str = "echo",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """POST an action to a routine and return the parsed response body.

    Args:
        client: The test HTTP client.
        auth_headers: Authorization headers containing a valid Bearer token.
        routine_id: Parent routine primary key.
        action_type: Type of action (default ``"echo"``).
        config: Action config dict (default ``{"message": "hello"}``).

    Returns:
        The parsed JSON response body of the created Action.
    """
    payload: dict[str, Any] = {
        "action_type": action_type,
        "config": config or {"message": "hello"},
    }
    response = client.post(
        f"/routines/{routine_id}/actions", json=payload, headers=auth_headers
    )
    assert response.status_code == 201
    return response.json()  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# TestRoutineCRUD
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Routines")  # pyright: ignore[reportUnknownMemberType]
@allure.story("CRUD")  # pyright: ignore[reportUnknownMemberType]
class TestRoutineCRUD:
    def test_create_routine_manual(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/routines/",
            json={
                "name": "Morning Lights",
                "schedule_type": "manual",
                "schedule_config": None,
                "is_active": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Morning Lights"
        assert body["schedule_type"] == "manual"
        assert body["schedule_config"] is None
        assert body["is_active"] is True
        assert "id" in body
        assert "created_at" in body
        assert body["actions"] == []

    def test_create_routine_cron(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/routines/",
            json={
                "name": "Daily Alarm",
                "schedule_type": "cron",
                "schedule_config": {"cron": "0 9 * * *"},
                "is_active": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["schedule_type"] == "cron"
        assert body["schedule_config"] == {"cron": "0 9 * * *"}

    def test_create_routine_interval(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/routines/",
            json={
                "name": "Hourly Check",
                "schedule_type": "interval",
                "schedule_config": {"seconds": 3600},
                "is_active": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["schedule_type"] == "interval"
        assert body["schedule_config"] == {"seconds": 3600}

    def test_get_routine(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        created = _create_routine(client, auth_headers, name="Fetch Me")
        routine_id = created["id"]

        response = client.get(f"/routines/{routine_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == routine_id
        assert body["name"] == "Fetch Me"
        assert body["schedule_type"] == "manual"
        assert body["is_active"] is True

    def test_update_routine(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        created = _create_routine(client, auth_headers, name="Old Name")
        routine_id = created["id"]

        response = client.put(
            f"/routines/{routine_id}",
            json={"name": "New Name"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "New Name"
        assert body["id"] == routine_id

    def test_delete_routine_cascades(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        created = _create_routine(client, auth_headers, name="To Delete")
        routine_id = created["id"]
        _create_action(client, auth_headers, routine_id)

        delete_response = client.delete(f"/routines/{routine_id}", headers=auth_headers)
        assert delete_response.status_code == 204

        # Routine itself is gone
        get_response = client.get(f"/routines/{routine_id}")
        assert get_response.status_code == 404

        # Actions for this routine are also gone (cascade)
        actions_response = client.get(
            f"/routines/{routine_id}/actions", headers=auth_headers
        )
        assert actions_response.status_code == 404


# ---------------------------------------------------------------------------
# TestScheduleConfigValidation
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Routines")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Validation")  # pyright: ignore[reportUnknownMemberType]
class TestScheduleConfigValidation:
    def test_rejects_manual_with_config(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/routines/",
            json={
                "name": "Bad Manual",
                "schedule_type": "manual",
                "schedule_config": {"cron": "0 9 * * *"},
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_rejects_cron_without_cron_key(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/routines/",
            json={
                "name": "Bad Cron",
                "schedule_type": "cron",
                "schedule_config": {"seconds": 60},
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_rejects_interval_without_seconds_key(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/routines/",
            json={
                "name": "Bad Interval",
                "schedule_type": "interval",
                "schedule_config": {"cron": "* * * * *"},
            },
            headers=auth_headers,
        )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# TestActionManagement
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Routines")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Actions")  # pyright: ignore[reportUnknownMemberType]
class TestActionManagement:
    def test_create_action_appends(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers)
        routine_id = routine["id"]

        action1 = _create_action(client, auth_headers, routine_id)
        action2 = _create_action(client, auth_headers, routine_id)

        assert action1["position"] == 1
        assert action2["position"] == 2

    def test_delete_action_compacts_positions(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers)
        routine_id = routine["id"]

        a1 = _create_action(client, auth_headers, routine_id, config={"message": "a1"})
        a2 = _create_action(client, auth_headers, routine_id, config={"message": "a2"})
        a3 = _create_action(client, auth_headers, routine_id, config={"message": "a3"})

        assert a1["position"] == 1
        assert a2["position"] == 2
        assert a3["position"] == 3

        # Delete the middle action (position 2)
        del_response = client.delete(f"/actions/{a2['id']}", headers=auth_headers)
        assert del_response.status_code == 204

        # Remaining actions should be at positions 1 and 2 (compact)
        actions_response = client.get(f"/routines/{routine_id}/actions")
        assert actions_response.status_code == 200
        actions = actions_response.json()
        positions = [a["position"] for a in actions]
        assert positions == [1, 2]

    def test_update_action_swaps_position(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers)
        routine_id = routine["id"]

        a1 = _create_action(client, auth_headers, routine_id, config={"message": "a1"})
        a2 = _create_action(client, auth_headers, routine_id, config={"message": "a2"})
        a3 = _create_action(client, auth_headers, routine_id, config={"message": "a3"})

        # Move action at position 1 to position 3 — should swap with action at pos 3
        put_response = client.put(
            f"/actions/{a1['id']}",
            json={"position": 3},
            headers=auth_headers,
        )
        assert put_response.status_code == 200
        assert put_response.json()["position"] == 3

        # Fetch all actions to verify final order
        actions_response = client.get(f"/routines/{routine_id}/actions")
        actions = {a["id"]: a["position"] for a in actions_response.json()}

        # a1 should now be at 3, a3 (formerly pos 3) should be at 1, a2 unchanged
        assert actions[a1["id"]] == 3
        assert actions[a2["id"]] == 2
        assert actions[a3["id"]] == 1

    def test_update_action_position_out_of_range(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers)
        routine_id = routine["id"]
        action = _create_action(client, auth_headers, routine_id)

        response = client.put(
            f"/actions/{action['id']}",
            json={"position": 99},
            headers=auth_headers,
        )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# TestExecutionLifecycle
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Routines")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Execution")  # pyright: ignore[reportUnknownMemberType]
class TestExecutionLifecycle:
    def test_run_now_returns_202(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers, name="Run Me")
        routine_id = routine["id"]

        response = client.post(f"/routines/{routine_id}/run", headers=auth_headers)

        assert response.status_code == 202
        body = response.json()
        assert "execution_id" in body
        assert isinstance(body["execution_id"], int)

    def test_execution_completes(
        self,
        engine: Engine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify an execution transitions to 'completed' for a 0-second sleep routine.

        The execution engine uses three separate ``SessionLocal`` connections.  The
        standard ``db_session`` fixture wraps tests in an uncommitted outer transaction
        (create_savepoint isolation), so those separate connections cannot see the
        test-session rows.

        This test therefore bypasses the HTTP/thread layer entirely: it uses real
        autocommitting ``SessionLocal`` sessions (bound to the testcontainer engine)
        to set up the routine, run the engine synchronously, and verify the result.
        All data is cleaned up via an explicit delete at the end so the outer
        transaction rollback does not interfere.
        """
        container_session_factory = sessionmaker(
            bind=engine, autocommit=False, autoflush=False
        )
        monkeypatch.setattr(_db_module, "SessionLocal", container_session_factory)
        monkeypatch.setattr(_engine_module, "SessionLocal", container_session_factory)

        from backend.execution_engine import run_routine
        from backend.models import Action, Routine, RoutineExecution

        # Use real committed sessions so the execution engine can see the rows.
        with container_session_factory() as session:
            routine = Routine(
                name="Fast Routine",
                schedule_type="manual",
                schedule_config=None,
                is_active=True,
            )
            session.add(routine)
            session.commit()
            session.refresh(routine)
            routine_id = routine.id

            action = Action(
                routine_id=routine_id,
                position=1,
                action_type="sleep",
                config={"seconds": 0},
            )
            session.add(action)
            session.commit()

            execution = RoutineExecution(
                routine_id=routine_id,
                status="running",
                triggered_by="manual",
            )
            session.add(execution)
            session.commit()
            session.refresh(execution)
            execution_id = execution.id

        # Run the engine synchronously (no thread) so we can assert inline.
        run_routine(routine_id, "manual", execution_id)

        # Verify the execution reached 'completed'.
        with container_session_factory() as session:
            result = session.get(RoutineExecution, execution_id)
            assert result is not None
            assert result.status == "completed"
            assert result.completed_at is not None

            # Clean up committed data so testcontainer state stays consistent.
            session.delete(result)
            routine_obj = session.get(Routine, routine_id)
            if routine_obj is not None:
                session.delete(routine_obj)
            session.commit()

    def test_execution_appears_in_active(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Verify a running execution appears in the active executions list.

        The execution row is inserted by the route handler via the test session
        (injected via ``get_session`` override) and is therefore immediately
        visible to subsequent queries on the same session.  We do not need the
        background thread to complete — we only assert the row exists in the
        ``/executions/active`` response before the sleep finishes.
        """
        # Use a 3-second sleep so the execution is still running when we poll
        routine = _create_routine(client, auth_headers, name="Slow Routine")
        routine_id = routine["id"]
        _create_action(
            client,
            auth_headers,
            routine_id,
            action_type="sleep",
            config={"seconds": 3},
        )

        run_response = client.post(f"/routines/{routine_id}/run", headers=auth_headers)
        assert run_response.status_code == 202
        execution_id = run_response.json()["execution_id"]

        # Fetch active executions — the execution row was inserted into the test
        # session by insert_execution_row before the thread started, so it is
        # immediately visible here without any sleep.
        active_response = client.get("/executions/active")
        assert active_response.status_code == 200
        active_ids = [r["id"] for r in active_response.json()]
        assert execution_id in active_ids


# ---------------------------------------------------------------------------
# TestRunNowConflict
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Routines")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Conflict")  # pyright: ignore[reportUnknownMemberType]
class TestRunNowConflict:
    def test_run_now_409_when_already_running(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db_session: Session,
    ) -> None:
        routine = _create_routine(client, auth_headers, name="Conflict Routine")
        routine_id = routine["id"]

        # Manually insert a running execution directly into the test session
        existing = RoutineExecution(
            routine_id=routine_id,
            status="running",
            triggered_by="manual",
        )
        db_session.add(existing)
        db_session.commit()

        # Now attempt to run the routine again — should get 409
        response = client.post(f"/routines/{routine_id}/run", headers=auth_headers)

        assert response.status_code == 409
        assert "already running" in response.json()["detail"].lower()
