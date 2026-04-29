"""Tests for the Routines, Actions, and Execution endpoints."""

from collections.abc import Generator
from datetime import UTC, datetime
from typing import TypedDict

import allure
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import DateTime, Engine
from sqlalchemy.orm import Session, sessionmaker

import backend.database as _db_module
import backend.execution_engine as _engine_module
from backend.database import get_session
from backend.main import app
from backend.models import Routine, RoutineExecution, User

# ---------------------------------------------------------------------------
# Response shapes
# ---------------------------------------------------------------------------


class ActionResponse(TypedDict):
    id: int
    routine_id: int
    position: int
    action_type: str
    config: dict[str, object]


class RoutineResponse(TypedDict):
    id: int
    name: str
    schedule_type: str
    schedule_config: dict[str, object] | None
    is_active: bool
    created_at: str
    actions: list[ActionResponse]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_routine(
    client: TestClient,
    auth_headers: dict[str, str],
    **overrides: object,
) -> RoutineResponse:
    """POST a routine with auth and return the parsed response body.

    Args:
        client: The test HTTP client.
        auth_headers: Authorization headers containing a valid Bearer token.
        **overrides: Fields to override in the default payload.

    Returns:
        The parsed JSON response body of the created Routine.
    """
    payload: dict[str, object] = {
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
    config: dict[str, object] | None = None,
    position: int | None = None,
) -> ActionResponse:
    """POST an action to a routine and return the parsed response body.

    Args:
        client: The test HTTP client.
        auth_headers: Authorization headers containing a valid Bearer token.
        routine_id: Parent routine primary key.
        action_type: Type of action (default ``"echo"``).
        config: Action config dict (default ``{"message": "hello"}``).
        position: Optional insertion position within the routine.

    Returns:
        The parsed JSON response body of the created Action.
    """
    payload: dict[str, object] = {
        "action_type": action_type,
        "config": config or {"message": "hello"},
    }
    if position is not None:
        payload["position"] = position
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
    def test_list_routines_returns_newest_first_with_nested_actions(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db_session: Session,
    ) -> None:
        older = _create_routine(client, auth_headers, name="Older Routine")
        newer = _create_routine(client, auth_headers, name="Newer Routine")
        _create_action(
            client,
            auth_headers,
            older["id"],
            action_type="echo",
            config={"message": "hello"},
        )
        older_row = db_session.get(Routine, older["id"])
        newer_row = db_session.get(Routine, newer["id"])
        assert older_row is not None
        assert newer_row is not None
        older_row.created_at = datetime(2026, 1, 1, tzinfo=UTC)
        newer_row.created_at = datetime(2026, 1, 2, tzinfo=UTC)
        db_session.commit()

        response = client.get("/routines/")

        assert response.status_code == 200
        body = response.json()
        assert [routine["name"] for routine in body["items"][:2]] == [
            "Newer Routine",
            "Older Routine",
        ]
        older_row = next(r for r in body["items"] if r["id"] == older["id"])
        assert older_row["actions"] == [
            {
                "id": older_row["actions"][0]["id"],
                "routine_id": older["id"],
                "position": 1,
                "action_type": "echo",
                "config": {"message": "hello"},
            }
        ]

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
        assert datetime.fromisoformat(body["created_at"]).tzinfo is not None
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
    def test_rejects_invalid_cron_expression(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/routines/",
            json={
                "name": "Broken Cron",
                "schedule_type": "cron",
                "schedule_config": {"cron": "not a cron"},
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

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

    def test_update_rejects_manual_with_config(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers)

        response = client.put(
            f"/routines/{routine['id']}",
            json={
                "schedule_type": "manual",
                "schedule_config": {"cron": "0 9 * * *"},
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_update_rejects_schedule_type_without_matching_config(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers)

        response = client.put(
            f"/routines/{routine['id']}",
            json={"schedule_type": "interval"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_update_switches_cron_to_manual_and_clears_config(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db_session: Session,
    ) -> None:
        routine = _create_routine(
            client,
            auth_headers,
            schedule_type="cron",
            schedule_config={"cron": "0 9 * * *"},
        )

        response = client.put(
            f"/routines/{routine['id']}",
            json={"schedule_type": "manual"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["schedule_type"] == "manual"
        assert body["schedule_config"] is None

        persisted = db_session.get(Routine, routine["id"])
        assert persisted is not None
        assert persisted.schedule_type == "manual"
        assert persisted.schedule_config is None

    def test_explicit_null_schedule_config_is_field_aware(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(
            client,
            auth_headers,
            schedule_type="cron",
            schedule_config={"cron": "0 9 * * *"},
        )

        response = client.put(
            f"/routines/{routine['id']}",
            json={"schedule_config": None},
            headers=auth_headers,
        )

        assert response.status_code == 422

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

        def override_get_session() -> Generator[Session, None, None]:
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_session] = override_get_session
        try:
            lenient_client = TestClient(app, raise_server_exceptions=False)
            response = lenient_client.put(
                f"/routines/{routine['id']}",
                json={
                    "schedule_type": "interval",
                    "schedule_config": {"seconds": 30},
                },
                headers=auth_headers,
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 500

        persisted = db_session.get(Routine, routine["id"])
        assert persisted is not None
        assert persisted.schedule_type == "manual"
        assert persisted.schedule_config is None


# ---------------------------------------------------------------------------
# TestActionManagement
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Routines")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Actions")  # pyright: ignore[reportUnknownMemberType]
class TestActionManagement:
    def test_create_action_rejects_invalid_echo_config(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers)

        response = client.post(
            f"/routines/{routine['id']}/actions",
            json={"action_type": "echo", "config": {"message": ""}},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_update_action_rejects_invalid_sleep_config(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers)
        action = _create_action(
            client,
            auth_headers,
            routine["id"],
            action_type="sleep",
            config={"seconds": 5},
        )

        response = client.put(
            f"/actions/{action['id']}",
            json={"config": {"seconds": -1}},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_create_action_appends(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers)
        routine_id = routine["id"]

        action1 = _create_action(client, auth_headers, routine_id)
        action2 = _create_action(client, auth_headers, routine_id)

        assert action1["position"] == 1
        assert action2["position"] == 2

    def test_create_action_inserts_and_shifts_later_positions(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers)
        routine_id = routine["id"]

        a1 = _create_action(client, auth_headers, routine_id, config={"message": "a1"})
        a2 = _create_action(client, auth_headers, routine_id, config={"message": "a2"})
        inserted = _create_action(
            client,
            auth_headers,
            routine_id,
            config={"message": "inserted"},
            position=2,
        )

        assert a1["position"] == 1
        assert a2["position"] == 2
        assert inserted["position"] == 2

        actions_response = client.get(f"/routines/{routine_id}/actions")
        assert actions_response.status_code == 200
        actions = actions_response.json()

        assert [action["position"] for action in actions] == [1, 2, 3]
        assert [action["config"]["message"] for action in actions] == [
            "a1",
            "inserted",
            "a2",
        ]

    def test_create_action_position_out_of_range(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers)
        routine_id = routine["id"]
        _create_action(client, auth_headers, routine_id)

        response = client.post(
            f"/routines/{routine_id}/actions",
            json={
                "action_type": "echo",
                "config": {"message": "bad position"},
                "position": 99,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

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

    def test_update_action_changes_type_and_config(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers)
        action = _create_action(
            client,
            auth_headers,
            routine["id"],
            action_type="echo",
            config={"message": "hello"},
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
        routine = _create_routine(client, auth_headers)
        action = _create_action(
            client,
            auth_headers,
            routine["id"],
            action_type="sleep",
            config={"seconds": 5},
        )

        # {} is invalid for sleep — with the old or-fallback bug this would
        # silently use {"seconds": 5} and return 200; correct behaviour is 422.
        response = client.put(
            f"/actions/{action['id']}",
            json={"config": {}},
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
        self,
        client: TestClient,
        auth_headers: dict[str, str],
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
        monkeypatch.setattr(
            _engine_module.routine_executor,
            "_session_factory",
            container_session_factory,
        )

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
        _engine_module.routine_executor.run(routine_id, "manual", execution_id)

        # Verify the execution reached 'completed'.
        with container_session_factory() as session:
            result = session.get(RoutineExecution, execution_id)
            assert result is not None
            assert result.status == "completed"
            assert result.completed_at is not None

        # Clean up in two steps: delete execution first (cascades to action_executions),
        # then delete the routine (cascades to actions). Splitting commits avoids FK
        # violations that occur when SQLAlchemy flushes action deletions before
        # action_execution deletions within a single transaction.
        with container_session_factory() as session:
            result = session.get(RoutineExecution, execution_id)
            if result is not None:
                session.delete(result)
                session.commit()
        with container_session_factory() as session:
            routine_obj = session.get(Routine, routine_id)
            if routine_obj is not None:
                session.delete(routine_obj)
                session.commit()

    def test_execution_failure_marks_failed(
        self,
        engine: Engine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        container_session_factory = sessionmaker(
            bind=engine, autocommit=False, autoflush=False
        )
        monkeypatch.setattr(_db_module, "SessionLocal", container_session_factory)
        monkeypatch.setattr(
            _engine_module.routine_executor,
            "_session_factory",
            container_session_factory,
        )

        from backend.models import Action, Routine, RoutineExecution

        with container_session_factory() as session:
            routine = Routine(
                name="Broken Routine",
                schedule_type="manual",
                schedule_config=None,
                is_active=True,
            )
            session.add(routine)
            session.commit()
            session.refresh(routine)

            session.add(
                Action(
                    routine_id=routine.id,
                    position=1,
                    action_type="sleep",
                    config={"seconds": "not-a-number"},
                )
            )
            session.commit()

            execution = RoutineExecution(
                routine_id=routine.id,
                status="running",
                triggered_by="manual",
            )
            session.add(execution)
            session.commit()
            session.refresh(execution)
            routine_id = routine.id
            execution_id = execution.id

        _engine_module.routine_executor.run(routine_id, "manual", execution_id)

        with container_session_factory() as session:
            result = session.get(RoutineExecution, execution_id)
            assert result is not None
            assert result.status == "failed"
            assert result.completed_at is not None

        with container_session_factory() as session:
            result = session.get(RoutineExecution, execution_id)
            if result is not None:
                session.delete(result)
                session.commit()
        with container_session_factory() as session:
            routine_obj = session.get(Routine, routine_id)
            if routine_obj is not None:
                session.delete(routine_obj)
                session.commit()

    def test_execution_appears_in_active(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Verify an enqueued execution appears in the active executions list.

        The route handler inserts a RoutineExecution row with status='queued'
        synchronously before returning 202.  The test session sees the row
        immediately — no background worker is needed.
        """
        routine = _create_routine(client, auth_headers, name="Queued Routine")
        routine_id = routine["id"]

        run_response = client.post(f"/routines/{routine_id}/run", headers=auth_headers)
        assert run_response.status_code == 202
        execution_id = run_response.json()["execution_id"]

        active_response = client.get("/executions/active")
        assert active_response.status_code == 200
        active_ids = [r["id"] for r in active_response.json()]
        assert execution_id in active_ids


# ---------------------------------------------------------------------------
# TestTimestampColumns
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Routines")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Timestamps")  # pyright: ignore[reportUnknownMemberType]
class TestTimestampColumns:
    def test_timestamp_columns_are_timezone_aware(self) -> None:
        assert isinstance(User.__table__.c.created_at.type, DateTime)
        assert isinstance(Routine.__table__.c.created_at.type, DateTime)
        assert isinstance(RoutineExecution.__table__.c.started_at.type, DateTime)
        assert isinstance(RoutineExecution.__table__.c.completed_at.type, DateTime)
        assert User.__table__.c.created_at.type.timezone is True
        assert Routine.__table__.c.created_at.type.timezone is True
        assert RoutineExecution.__table__.c.started_at.type.timezone is True
        assert RoutineExecution.__table__.c.completed_at.type.timezone is True


# ---------------------------------------------------------------------------
# TestRunNowConflict
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Routines")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Conflict")  # pyright: ignore[reportUnknownMemberType]
class TestRunNowConflict:
    def test_run_now_allows_multiple_queued_runs(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """The queue model allows multiple concurrent enqueue requests.

        Each POST /run inserts a new RoutineExecution row regardless of whether
        one is already running or queued — no 409 is returned.
        """
        routine = _create_routine(client, auth_headers, name="Queueable Routine")
        routine_id = routine["id"]

        first = client.post(f"/routines/{routine_id}/run", headers=auth_headers)
        second = client.post(f"/routines/{routine_id}/run", headers=auth_headers)

        assert first.status_code == 202
        assert second.status_code == 202
        assert first.json()["execution_id"] != second.json()["execution_id"]


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Routines")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Auth")  # pyright: ignore[reportUnknownMemberType]
class TestRoutineWriteAuthProtection:
    def test_create_routine_requires_auth(self, client: TestClient) -> None:
        response = client.post(
            "/routines/",
            json={
                "name": "Protected",
                "schedule_type": "manual",
                "schedule_config": None,
                "is_active": True,
            },
        )

        assert response.status_code == 401

    def test_run_now_requires_auth(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers, name="Protected Run")

        response = client.post(f"/routines/{routine['id']}/run")

        assert response.status_code == 401

    def test_create_action_requires_auth(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        routine = _create_routine(client, auth_headers, name="Protected Action")

        response = client.post(
            f"/routines/{routine['id']}/actions",
            json={"action_type": "echo", "config": {"message": "hello"}},
        )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# TestExecutionHistory
# ---------------------------------------------------------------------------


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
        routine = _create_routine(client, auth_headers, name="History Limit Routine")
        routine_id = routine["id"]

        for _ in range(5):
            db_session.add(
                RoutineExecution(
                    routine_id=routine_id,
                    status="completed",
                    triggered_by="manual",
                )
            )
        db_session.commit()

        response = client.get("/executions/history?limit=3")

        assert response.status_code == 200
        assert len(response.json()["items"]) == 3

    def test_history_routine_id_filter_scopes_results(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db_session: Session,
    ) -> None:
        routine_a = _create_routine(client, auth_headers, name="History Routine A")
        routine_b = _create_routine(client, auth_headers, name="History Routine B")

        for r in [routine_a, routine_b]:
            db_session.add(
                RoutineExecution(
                    routine_id=r["id"],
                    status="completed",
                    triggered_by="manual",
                )
            )
        db_session.commit()

        response = client.get(f"/executions/history?routine_id={routine_a['id']}")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1
        assert all(row["routine_id"] == routine_a["id"] for row in body["items"])
