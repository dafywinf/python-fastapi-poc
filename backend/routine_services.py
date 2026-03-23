"""Business logic for Routine, Action, and RoutineExecution operations."""

import logging
from datetime import datetime
from typing import TypedDict, cast

from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session, joinedload

from backend.domain_types import (
    EXECUTION_STATUS_COMPLETED,
    EXECUTION_STATUS_FAILED,
    EXECUTION_STATUS_RUNNING,
    SCHEDULE_TYPE_MANUAL,
    ActionType,
    ExecutionStatus,
    ExecutionTrigger,
    ScheduleType,
)
from backend.models import Action, Routine, RoutineExecution
from backend.scheduler import (
    RoutineSchedulerSnapshot,
    register_routine,
    unregister_routine,
)
from backend.schemas import (
    ActionCreate,
    ActionUpdate,
    RoutineCreate,
    RoutineUpdate,
    validate_action_config,
    validate_routine_schedule,
)

logger = logging.getLogger(__name__)


class ExecutionRow(TypedDict):
    """Serialized execution row joined with routine name."""

    id: int
    routine_id: int
    routine_name: str
    status: ExecutionStatus
    triggered_by: ExecutionTrigger
    started_at: datetime
    completed_at: datetime | None


# ---------------------------------------------------------------------------
# Routine CRUD
# ---------------------------------------------------------------------------


def list_routines(session: Session) -> list[Routine]:
    """Return all Routine records ordered by creation date descending.

    Args:
        session: Active SQLAlchemy session.

    Returns:
        List of Routine instances.
    """
    return list(
        session.execute(select(Routine).order_by(Routine.created_at.desc())).scalars()
    )


def create_routine(session: Session, payload: RoutineCreate) -> Routine:
    """Create and persist a new Routine, registering it with the scheduler if active.

    Args:
        session: Active SQLAlchemy session.
        payload: Validated creation payload.

    Returns:
        The newly created Routine instance.
    """
    routine = Routine(
        name=payload.name,
        description=payload.description,
        schedule_type=payload.schedule_type,
        schedule_config=payload.schedule_config,
        is_active=payload.is_active,
    )
    session.add(routine)
    session.commit()
    session.refresh(routine)
    if routine.is_active and routine.schedule_type != SCHEDULE_TYPE_MANUAL:
        register_routine(routine)
    return routine


def get_routine(session: Session, routine_id: int) -> Routine | None:
    """Fetch a single Routine by primary key.

    Args:
        session: Active SQLAlchemy session.
        routine_id: Primary key of the target record.

    Returns:
        Routine instance or None if not found.
    """
    return session.get(Routine, routine_id)


def update_routine(
    session: Session,
    routine: Routine,
    payload: RoutineUpdate,
) -> Routine:
    """Apply partial updates to a Routine, syncing the scheduler as needed.

    Scheduler sync rules:
    - If ``is_active`` changes to False: unregister the job.
    - If ``is_active`` changes to True: register (or re-register) the job.
    - If schedule fields change while already active: re-register so APScheduler
      reschedules (``replace_existing=True`` in ``register_routine`` handles this).

    Args:
        session: Active SQLAlchemy session.
        routine: The existing Routine instance to update.
        payload: Validated update payload (None fields are ignored).

    Returns:
        The updated Routine instance.
    """
    snapshot = RoutineSchedulerSnapshot(
        id=routine.id,
        is_active=routine.is_active,
        schedule_type=cast(ScheduleType, routine.schedule_type),
        schedule_config=routine.schedule_config,
    )
    fields_set = payload.model_fields_set
    schedule_type_provided = "schedule_type" in fields_set
    schedule_config_provided = "schedule_config" in fields_set

    next_schedule_type = (
        payload.schedule_type if schedule_type_provided else snapshot.schedule_type
    )
    if next_schedule_type is None:
        raise ValueError("schedule_type cannot be null")
    if schedule_type_provided and payload.schedule_type == SCHEDULE_TYPE_MANUAL:
        next_schedule_config = None
    elif schedule_config_provided:
        next_schedule_config = payload.schedule_config
    else:
        next_schedule_config = snapshot.schedule_config

    validate_routine_schedule(next_schedule_type, next_schedule_config)

    scheduler_action: str | None = None

    def restore_previous_scheduler_state() -> None:
        if snapshot.is_active and snapshot.schedule_type != SCHEDULE_TYPE_MANUAL:
            register_routine(snapshot)
        elif not snapshot.is_active:
            unregister_routine(routine.id)

    try:
        if payload.name is not None:
            routine.name = payload.name
        if payload.description is not None:
            routine.description = payload.description
        if schedule_type_provided:
            routine.schedule_type = next_schedule_type
        if schedule_type_provided and next_schedule_type == SCHEDULE_TYPE_MANUAL:
            routine.schedule_config = None
        elif schedule_config_provided:
            routine.schedule_config = payload.schedule_config
        if payload.is_active is not None:
            routine.is_active = payload.is_active

        session.flush()

        new_is_active = routine.is_active

        if snapshot.is_active and not new_is_active:
            # Active → inactive: remove the job
            unregister_routine(routine.id)
            scheduler_action = "unregister"
        elif not snapshot.is_active and new_is_active:
            # Inactive → active: register the job
            if routine.schedule_type != SCHEDULE_TYPE_MANUAL:
                register_routine(routine)
                scheduler_action = "register"
        elif new_is_active:
            # Still active — check if schedule changed
            schedule_changed = (
                routine.schedule_type != snapshot.schedule_type
                or routine.schedule_config != snapshot.schedule_config
            )
            if schedule_changed and routine.schedule_type != SCHEDULE_TYPE_MANUAL:
                register_routine(routine)  # replace_existing=True handles reschedule
                scheduler_action = "replace"

        session.commit()
    except Exception:
        logger.warning("Rolling back update to routine %d", routine.id)
        session.rollback()
        if scheduler_action is not None:
            try:
                restore_previous_scheduler_state()
            except Exception:
                logger.exception(
                    "Failed to restore scheduler state for routine %d", routine.id
                )
        raise

    session.refresh(routine)

    return routine


def delete_routine(session: Session, routine: Routine) -> None:
    """Delete a Routine and unregister its scheduler job.

    Unregistration happens before deletion so the job ID is still valid.
    ORM cascade handles child Action and RoutineExecution rows.

    Args:
        session: Active SQLAlchemy session.
        routine: The Routine instance to delete.
    """
    unregister_routine(routine.id)
    session.delete(routine)
    session.commit()


# ---------------------------------------------------------------------------
# Action CRUD
# ---------------------------------------------------------------------------


def list_actions(session: Session, routine_id: int) -> list[Action]:
    """Return all Actions for a Routine, ordered by position.

    Args:
        session: Active SQLAlchemy session.
        routine_id: The parent Routine primary key.

    Returns:
        List of Action instances in position order.
    """
    return list(
        session.execute(
            select(Action)
            .where(Action.routine_id == routine_id)
            .order_by(Action.position)
        ).scalars()
    )


def create_action(session: Session, routine_id: int, payload: ActionCreate) -> Action:
    """Create and append (or insert at) a position within a Routine.

    If ``payload.position`` is None the action is appended at the end
    (max existing position + 1, or 1 if no actions exist yet).
    If ``payload.position`` is provided, later actions are shifted down so the
    new action occupies the requested slot.

    Args:
        session: Active SQLAlchemy session.
        routine_id: The parent Routine primary key.
        payload: Validated creation payload.

    Returns:
        The newly created Action instance.
    """
    max_pos: int | None = session.execute(
        select(func.max(Action.position)).where(Action.routine_id == routine_id)
    ).scalar_one_or_none()
    next_append_position = (max_pos or 0) + 1

    if payload.position is None:
        position = next_append_position
    else:
        position = payload.position
        if position < 1 or position > next_append_position:
            raise ValueError("Position out of range")
        session.execute(
            sa_update(Action)
            .where(Action.routine_id == routine_id, Action.position >= position)
            .values(position=Action.position + 1)
        )

    action = Action(
        routine_id=routine_id,
        position=position,
        action_type=payload.action_type,
        config=payload.config,
    )
    session.add(action)
    session.commit()
    session.refresh(action)
    return action


def update_action(session: Session, action: Action, payload: ActionUpdate) -> Action:
    """Apply partial updates to an Action, swapping positions if requested.

    When ``payload.position`` is provided the action at the target position is
    looked up and the two rows have their positions swapped atomically.  If no
    action occupies the target position a 422 is raised.

    Args:
        session: Active SQLAlchemy session.
        action: The existing Action instance to update.
        payload: Validated update payload (None fields are ignored).

    Returns:
        The updated Action instance.

    Raises:
        ValueError: if the requested position is out of range or config is invalid.
    """
    if payload.position is not None:
        new_pos = payload.position
        other: Action | None = session.execute(
            select(Action).where(
                Action.routine_id == action.routine_id,
                Action.position == new_pos,
                Action.id != action.id,
            )
        ).scalar_one_or_none()
        if other is None:
            raise ValueError("Position out of range")
        old_pos = action.position
        action.position = new_pos
        other.position = old_pos
        session.flush()

    next_action_type = (
        payload.action_type
        if payload.action_type is not None
        else cast(ActionType, action.action_type)
    )
    next_config = payload.config if payload.config is not None else action.config

    validate_action_config(next_action_type, next_config)

    if payload.action_type is not None:
        action.action_type = payload.action_type
    if payload.config is not None:
        action.config = payload.config

    session.commit()
    session.refresh(action)
    return action


def delete_action(session: Session, action: Action) -> None:
    """Delete an Action and compact the position sequence for the routine.

    After deletion, all actions with a higher position are decremented by one
    so the sequence remains contiguous.

    Args:
        session: Active SQLAlchemy session.
        action: The Action instance to delete.
    """
    routine_id = action.routine_id
    deleted_pos = action.position
    session.delete(action)
    session.flush()
    session.execute(
        sa_update(Action)
        .where(Action.routine_id == routine_id, Action.position > deleted_pos)
        .values(position=Action.position - 1)
    )
    session.commit()


# ---------------------------------------------------------------------------
# Execution queries
# ---------------------------------------------------------------------------


def insert_execution_row(
    session: Session, routine_id: int, triggered_by: ExecutionTrigger
) -> RoutineExecution:
    """Insert a new RoutineExecution row with status 'running'.

    The DB unique partial index on (routine_id, status='running') will raise an
    IntegrityError if the routine is already executing.

    Args:
        session: Active SQLAlchemy session.
        routine_id: The Routine primary key.
        triggered_by: Label indicating who triggered the run (e.g. 'manual').

    Returns:
        The newly inserted RoutineExecution instance.
    """
    execution = RoutineExecution(
        routine_id=routine_id,
        status=EXECUTION_STATUS_RUNNING,
        triggered_by=triggered_by,
    )
    session.add(execution)
    session.commit()
    session.refresh(execution)
    return execution


def get_active_executions(session: Session) -> list[ExecutionRow]:
    """Return all currently running executions joined with routine name.

    Args:
        session: Active SQLAlchemy session.

    Returns:
        List of dicts with execution fields plus ``routine_name``.
    """
    stmt = (
        select(RoutineExecution)
        .options(joinedload(RoutineExecution.routine))
        .where(RoutineExecution.status == EXECUTION_STATUS_RUNNING)
        .order_by(RoutineExecution.started_at.desc())
    )
    results = list(session.execute(stmt).scalars().unique())
    rows = cast(
        list[ExecutionRow],
        [
            {
                "id": r.id,
                "routine_id": r.routine_id,
                "routine_name": r.routine.name,
                "status": r.status,
                "triggered_by": r.triggered_by,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
            }
            for r in results
        ],
    )
    return rows


def get_execution_history(
    session: Session,
    limit: int = 10,
    routine_id: int | None = None,
) -> list[ExecutionRow]:
    """Return completed or failed executions, optionally filtered by routine.

    Args:
        session: Active SQLAlchemy session.
        limit: Maximum number of records to return (default 10).
        routine_id: If provided, restrict results to this routine.

    Returns:
        List of dicts with execution fields plus ``routine_name``, newest first.
    """
    stmt = (
        select(RoutineExecution)
        .options(joinedload(RoutineExecution.routine))
        .where(
            RoutineExecution.status.in_(
                [EXECUTION_STATUS_COMPLETED, EXECUTION_STATUS_FAILED]
            )
        )
        .order_by(RoutineExecution.started_at.desc())
    )
    if routine_id is not None:
        stmt = stmt.where(RoutineExecution.routine_id == routine_id)
    stmt = stmt.limit(limit)
    results = list(session.execute(stmt).scalars().unique())
    rows = cast(
        list[ExecutionRow],
        [
            {
                "id": r.id,
                "routine_id": r.routine_id,
                "routine_name": r.routine.name,
                "status": r.status,
                "triggered_by": r.triggered_by,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
            }
            for r in results
        ],
    )
    return rows
