"""Execution engine and background launcher for routine runs."""

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Thread

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database import SessionLocal
from backend.domain_types import (
    ACTION_TYPE_ECHO,
    ACTION_TYPE_SLEEP,
    EXECUTION_STATUS_COMPLETED,
    EXECUTION_STATUS_FAILED,
    EXECUTION_STATUS_RUNNING,
    ExecutionStatus,
    ExecutionTrigger,
)
from backend.models import Action, RoutineExecution

logger = logging.getLogger(__name__)

ThreadFactory = Callable[..., Thread]


class RoutineExecutor:
    """Run routines using an injected SQLAlchemy session factory."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def run(
        self,
        routine_id: int,
        triggered_by: ExecutionTrigger,
        execution_id: int | None = None,
    ) -> None:
        """Execute a routine's actions sequentially.

        Uses three short-lived SQLAlchemy sessions so that no DB connection is held
        open during ``time.sleep()`` calls, avoiding connection-pool exhaustion.

        Args:
            routine_id: The ID of the routine to execute.
            triggered_by: What triggered this run ("cron", "interval", or "manual").
            execution_id: If provided, the execution row was already inserted by the
                caller (Run Now path). If None, this function inserts it
                (scheduler path).
        """
        resolved_execution_id = execution_id
        try:
            if resolved_execution_id is None:
                resolved_execution_id = self._create_execution_row(
                    routine_id, triggered_by
                )
                if resolved_execution_id is None:
                    return

            actions = self._load_actions(routine_id)
            for action in actions:
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

            self._update_execution_status(
                routine_id,
                resolved_execution_id,
                EXECUTION_STATUS_COMPLETED,
            )

        except Exception:
            logger.exception(
                "Routine %d execution %d failed", routine_id, resolved_execution_id
            )
            if resolved_execution_id is None:
                logger.error(
                    "Routine %d failed before an execution row could be created",
                    routine_id,
                )
                return
            self._update_execution_status(
                routine_id,
                resolved_execution_id,
                EXECUTION_STATUS_FAILED,
            )

    def _create_execution_row(
        self,
        routine_id: int,
        triggered_by: ExecutionTrigger,
    ) -> int | None:
        """Insert an execution row for scheduler-triggered runs."""
        try:
            with self._session_factory() as session:
                execution = RoutineExecution(
                    routine_id=routine_id,
                    status=EXECUTION_STATUS_RUNNING,
                    triggered_by=triggered_by,
                )
                session.add(execution)
                session.commit()
                session.refresh(execution)
                return execution.id
        except Exception:
            logger.exception(
                "Failed to create execution row for routine %d", routine_id
            )
            return None

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


class BackgroundRoutineLauncher:
    """Start routine executions in background threads."""

    def __init__(
        self,
        executor: RoutineExecutor,
        thread_factory: ThreadFactory = Thread,
    ) -> None:
        self._executor = executor
        self._thread_factory = thread_factory

    def start(
        self,
        routine_id: int,
        triggered_by: ExecutionTrigger,
        execution_id: int | None = None,
    ) -> Thread:
        """Launch a background thread for a routine execution.

        Args:
            routine_id: The routine to execute.
            triggered_by: What triggered the run.
            execution_id: Existing execution row ID for run-now calls.

        Returns:
            The started daemon thread.
        """
        thread = self._thread_factory(
            target=self._executor.run,
            args=[routine_id, triggered_by, execution_id],
            daemon=True,
        )
        thread.start()
        return thread


routine_executor = RoutineExecutor(SessionLocal)
execution_launcher = BackgroundRoutineLauncher(routine_executor)


def run_routine(
    routine_id: int,
    triggered_by: ExecutionTrigger,
    execution_id: int | None = None,
) -> None:
    """Backward-compatible wrapper around the default routine executor."""
    routine_executor.run(routine_id, triggered_by, execution_id)
