"""Execution engine, global queue, and background launcher for routine runs."""

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Thread
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database import SessionLocal
from backend.domain_types import (
    ACTION_EXECUTION_STATUS_COMPLETED,
    ACTION_EXECUTION_STATUS_FAILED,
    ACTION_EXECUTION_STATUS_PENDING,
    ACTION_EXECUTION_STATUS_RUNNING,
    ACTION_TYPE_ECHO,
    ACTION_TYPE_SLEEP,
    EXECUTION_STATUS_COMPLETED,
    EXECUTION_STATUS_FAILED,
    EXECUTION_STATUS_QUEUED,
    EXECUTION_STATUS_RUNNING,
    ActionExecutionStatus,
    ExecutionStatus,
    ExecutionTrigger,
)
from backend.models import Action, ActionExecution, RoutineExecution

logger = logging.getLogger(__name__)

ThreadFactory = Callable[..., Thread]


class RoutineExecutor:
    """Run a single routine execution to completion using short-lived sessions."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def run(
        self,
        routine_id: int,
        triggered_by: ExecutionTrigger,
        execution_id: int,
    ) -> None:
        """Execute a routine's actions sequentially.

        Uses short-lived SQLAlchemy sessions so that no DB connection is held
        open during ``time.sleep()`` calls, avoiding connection-pool exhaustion.
        The execution row must already exist with status 'running' before this
        is called — the queue worker handles the queued→running transition.

        Args:
            routine_id: The ID of the routine to execute.
            triggered_by: What triggered this run ("cron", "interval", or "manual").
            execution_id: Primary key of the existing RoutineExecution row.
        """
        current_action_execution_id: int | None = None
        try:
            actions = self._load_actions(routine_id)
            action_execution_ids = self._create_pending_action_executions(
                execution_id, actions
            )

            for action in actions:
                current_action_execution_id = action_execution_ids.get(action.id)
                self._update_action_execution_status(
                    current_action_execution_id, ACTION_EXECUTION_STATUS_RUNNING
                )

                if action.action_type == ACTION_TYPE_SLEEP:
                    raw = action.config.get("seconds")
                    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
                        raise ValueError(
                            f"sleep action {action.id}: "
                            "'seconds' value is missing or empty"
                        )
                    if not isinstance(raw, (int, str)):
                        raise ValueError(
                            f"sleep action {action.id}: "
                            "'seconds' must be an int or numeric string"
                        )
                    seconds = int(raw)
                    logger.info(
                        "Routine %d: sleeping for %d seconds",
                        routine_id,
                        seconds,
                    )
                    time.sleep(seconds)
                elif action.action_type == ACTION_TYPE_ECHO:
                    message = str(action.config["message"])
                    logger.info("Routine %d echo: %s", routine_id, message)

                self._update_action_execution_status(
                    current_action_execution_id, ACTION_EXECUTION_STATUS_COMPLETED
                )
                current_action_execution_id = None

            self._update_execution_status(
                routine_id,
                execution_id,
                EXECUTION_STATUS_COMPLETED,
            )

        except Exception:
            logger.exception("Routine %d execution %d failed", routine_id, execution_id)
            if current_action_execution_id is not None:
                self._update_action_execution_status(
                    current_action_execution_id, ACTION_EXECUTION_STATUS_FAILED
                )
            self._update_execution_status(
                routine_id,
                execution_id,
                EXECUTION_STATUS_FAILED,
            )

    def _load_actions(self, routine_id: int) -> list[Action]:
        """Load ordered actions for a routine in a short-lived session."""
        with self._session_factory() as session:
            return list(
                session.execute(
                    select(Action)
                    .where(Action.routine_id == routine_id)
                    .order_by(Action.position)
                ).scalars()
            )

    def _create_pending_action_executions(
        self, execution_id: int, actions: list[Action]
    ) -> dict[int, int]:
        """Create pending ActionExecution rows for all actions in a routine.

        Args:
            execution_id: The parent RoutineExecution primary key.
            actions: Ordered list of Action instances to track.

        Returns:
            Mapping of action_id → action_execution_id for subsequent updates.
        """
        try:
            with self._session_factory() as session:
                rows = [
                    ActionExecution(
                        execution_id=execution_id,
                        action_id=action.id,
                        position=action.position,
                        action_type=action.action_type,
                        config=action.config,
                        status=ACTION_EXECUTION_STATUS_PENDING,
                    )
                    for action in actions
                ]
                session.add_all(rows)
                session.commit()
                for row in rows:
                    session.refresh(row)
                return {row.action_id: row.id for row in rows}
        except Exception:
            logger.exception(
                "Failed to create action execution rows for execution %d", execution_id
            )
            return {}

    def _update_action_execution_status(
        self,
        action_execution_id: int | None,
        status: ActionExecutionStatus,
    ) -> None:
        """Update a single ActionExecution row's status and timestamps.

        Args:
            action_execution_id: Primary key of the ActionExecution row, or None to
                skip (used when row creation failed).
            status: Target status — "running", "completed", or "failed".
        """
        if action_execution_id is None:
            return
        try:
            with self._session_factory() as session:
                ae = session.get(ActionExecution, action_execution_id)
                if ae is None:
                    return
                ae.status = status
                now = datetime.now(UTC)
                if status == ACTION_EXECUTION_STATUS_RUNNING:
                    ae.started_at = now
                elif status in (
                    ACTION_EXECUTION_STATUS_COMPLETED,
                    ACTION_EXECUTION_STATUS_FAILED,
                ):
                    ae.completed_at = now
                session.commit()
        except Exception:
            logger.exception(
                "Failed to update action execution %d to %s",
                action_execution_id,
                status,
            )

    def _update_execution_status(
        self,
        routine_id: int,
        execution_id: int,
        status: ExecutionStatus,
    ) -> None:
        """Best-effort status transition with explicit logging on failure."""
        try:
            with self._session_factory() as session:
                execution = session.get(RoutineExecution, execution_id)
                if execution is None:
                    logger.warning(
                        "Routine %d execution %d not found while marking %s",
                        routine_id,
                        execution_id,
                        status,
                    )
                    return
                execution.status = status
                execution.completed_at = datetime.now(UTC)
                session.commit()
        except Exception:
            logger.exception(
                "Failed to mark routine %d execution %d as %s",
                routine_id,
                execution_id,
                status,
            )


class ExecutionQueue:
    """Global single-worker queue that serialises all routine executions.

    A single daemon thread polls the database every second for queued executions
    whose ``scheduled_for`` time has arrived. It atomically claims the next item
    (queued → running) and hands it to ``RoutineExecutor.run()``.

    Because the worker polls the database, it automatically recovers queued rows
    after a server restart with no in-memory state required.
    """

    def __init__(
        self,
        executor: RoutineExecutor,
        session_factory: sessionmaker[Session],
        thread_factory: ThreadFactory = Thread,
    ) -> None:
        self._executor = executor
        self._session_factory = session_factory
        self._worker = thread_factory(target=self._poll_loop, daemon=True)
        self._worker.start()

    def _poll_loop(self) -> None:
        """Main worker loop — runs forever in a daemon thread."""
        while True:
            try:
                claimed = self._claim_next()
                if claimed is not None:
                    routine_id, triggered_by, execution_id = claimed
                    self._executor.run(routine_id, triggered_by, execution_id)
                    # Skip sleep so the next queued item starts immediately.
                else:
                    time.sleep(1)
            except Exception:
                logger.exception("Execution queue worker encountered an error")
                time.sleep(1)

    def _claim_next(self) -> tuple[int, ExecutionTrigger, int] | None:
        """Atomically claim the oldest ready queued execution.

        Uses ``FOR UPDATE SKIP LOCKED`` so a future second worker process could
        safely run alongside this one without double-claiming.

        Returns:
            ``(routine_id, triggered_by, execution_id)`` of the claimed row, or
            ``None`` if no ready item exists.
        """
        now = datetime.now(UTC)
        try:
            with self._session_factory() as session:
                stmt = (
                    select(RoutineExecution)
                    .where(
                        RoutineExecution.status == EXECUTION_STATUS_QUEUED,
                        RoutineExecution.scheduled_for <= now,
                    )
                    .order_by(RoutineExecution.scheduled_for)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                execution = session.execute(stmt).scalar_one_or_none()
                if execution is None:
                    return None
                execution.status = EXECUTION_STATUS_RUNNING
                execution.started_at = datetime.now(UTC)
                session.commit()
                return (
                    execution.routine_id,
                    cast(ExecutionTrigger, execution.triggered_by),
                    execution.id,
                )
        except Exception:
            logger.exception("Failed to claim next queued execution")
            return None


def enqueue_routine_run(
    routine_id: int,
    triggered_by: ExecutionTrigger,
    scheduled_for: datetime | None = None,
    session: Session | None = None,
) -> int:
    """Insert a queued RoutineExecution and return its ID.

    The ``ExecutionQueue`` worker will claim and execute it once
    ``scheduled_for`` (defaults to now) has arrived.

    Args:
        routine_id: The routine to run.
        triggered_by: What triggered the run ("cron", "interval", or "manual").
        scheduled_for: Earliest time the worker may start execution.
            Defaults to the current time (run as soon as possible).
        session: Optional SQLAlchemy session. When provided (e.g. from a
            FastAPI dependency), the row is written on that session and the
            caller is responsible for committing. When omitted, a new
            ``SessionLocal`` session is opened and committed internally.

    Returns:
        The primary key of the newly inserted RoutineExecution row.
    """
    if session is not None:
        execution = RoutineExecution(
            routine_id=routine_id,
            status=EXECUTION_STATUS_QUEUED,
            triggered_by=triggered_by,
            scheduled_for=scheduled_for or datetime.now(UTC),
        )
        session.add(execution)
        session.flush()
        session.refresh(execution)
        return execution.id

    with SessionLocal() as own_session:
        execution = RoutineExecution(
            routine_id=routine_id,
            status=EXECUTION_STATUS_QUEUED,
            triggered_by=triggered_by,
            scheduled_for=scheduled_for or datetime.now(UTC),
        )
        own_session.add(execution)
        own_session.commit()
        own_session.refresh(execution)
        return execution.id


def run_routine(
    routine_id: int,
    triggered_by: ExecutionTrigger,
) -> None:
    """APScheduler callback — enqueues a routine run for the worker to pick up.

    Args:
        routine_id: The routine to run.
        triggered_by: Schedule type ("cron" or "interval").
    """
    enqueue_routine_run(routine_id, triggered_by)


# ---------------------------------------------------------------------------
# Global singletons — started when this module is first imported
# ---------------------------------------------------------------------------

routine_executor = RoutineExecutor(SessionLocal)
execution_queue = ExecutionQueue(routine_executor, SessionLocal)
