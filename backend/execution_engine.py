"""Execution engine — runs a routine's actions using three short-lived sessions."""

import logging
import time
from datetime import UTC, datetime

from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import Action, RoutineExecution

logger = logging.getLogger(__name__)


def run_routine(
    routine_id: int,
    triggered_by: str,
    execution_id: int | None = None,
) -> None:
    """Execute a routine's actions sequentially.

    Uses three short-lived SQLAlchemy sessions so that no DB connection is held
    open during ``time.sleep()`` calls, avoiding connection-pool exhaustion.

    Args:
        routine_id: The ID of the routine to execute.
        triggered_by: What triggered this run ("cron", "interval", or "manual").
        execution_id: If provided, the execution row was already inserted by the
            caller (Run Now path). If None, this function inserts it (scheduler path).
    """
    # Step 1: Insert execution row if not already done (scheduler path)
    if execution_id is None:
        with SessionLocal() as session:
            execution = RoutineExecution(
                routine_id=routine_id,
                status="running",
                triggered_by=triggered_by,
            )
            session.add(execution)
            session.commit()
            session.refresh(execution)
            execution_id = execution.id

    # execution_id is now guaranteed to be int
    resolved_execution_id: int = execution_id

    # Step 2: Load actions in a separate session, close immediately
    with SessionLocal() as session:
        actions = list(
            session.execute(
                select(Action)
                .where(Action.routine_id == routine_id)
                .order_by(Action.position)
            ).scalars()
        )

    # Step 3: Execute actions — no session open during sleep
    try:
        for action in actions:
            if action.action_type == "sleep":
                raw = action.config.get("seconds")
                if raw is None or (isinstance(raw, str) and raw.strip() == ""):
                    raise ValueError(
                        f"sleep action {action.id}: 'seconds' value is missing or empty"
                    )
                seconds = int(raw)
                logger.info("Routine %d: sleeping for %d seconds", routine_id, seconds)
                time.sleep(seconds)
            elif action.action_type == "echo":
                message = str(action.config["message"])
                logger.info("Routine %d echo: %s", routine_id, message)

        # Step 4: Mark completed
        with SessionLocal() as session:
            exc = session.get(RoutineExecution, resolved_execution_id)
            if exc is not None:
                exc.status = "completed"
                exc.completed_at = datetime.now(UTC)
                session.commit()

    except Exception:
        logger.exception(
            "Routine %d execution %d failed", routine_id, resolved_execution_id
        )
        with SessionLocal() as session:
            exc = session.get(RoutineExecution, resolved_execution_id)
            if exc is not None:
                exc.status = "failed"
                exc.completed_at = datetime.now(UTC)
                session.commit()
