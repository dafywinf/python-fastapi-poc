"""Business logic for Routine, Action, and RoutineExecution operations."""

import logging
from datetime import UTC, datetime, timedelta
from typing import TypedDict, cast

from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session, joinedload

from backend.domain_types import (
    EXECUTION_STATUS_COMPLETED,
    EXECUTION_STATUS_FAILED,
    EXECUTION_STATUS_QUEUED,
    EXECUTION_STATUS_RUNNING,
    SCHEDULE_TYPE_MANUAL,
    ActionExecutionStatus,
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


class ActionExecutionRow(TypedDict):
    """Serialized action execution row."""

    id: int
    action_id: int
    position: int
    action_type: ActionType
    config: dict[str, object]
    status: ActionExecutionStatus
    started_at: datetime | None
    completed_at: datetime | None


class ExecutionRow(TypedDict):
    """Serialized execution row joined with routine name."""

    id: int
    routine_id: int
    routine_name: str
    status: ExecutionStatus
    triggered_by: ExecutionTrigger
    queued_at: datetime
    scheduled_for: datetime
    started_at: datetime | None
    completed_at: datetime | None


class ActiveExecutionRow(ExecutionRow):
    """Execution row extended with per-action progress."""

    action_executions: list[ActionExecutionRow]


# ---------------------------------------------------------------------------
# Routine CRUD
# ---------------------------------------------------------------------------


def list_routines(
    session: Session,
    search: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[Routine], int]:
    """Return a paginated, optionally filtered slice of Routine records.

    Args:
        session: Active SQLAlchemy session.
        search: Optional substring to filter on routine name (case-insensitive).
        limit: Maximum number of records to return.
        offset: Number of records to skip.

    Returns:
        Tuple of (page of Routine instances ordered newest first, total match count).
    """
    stmt = select(Routine).order_by(Routine.created_at.desc())
    if search:
        stmt = stmt.where(Routine.name.ilike(f"%{search}%"))
    total: int = session.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()
    rows = list(session.execute(stmt.limit(limit).offset(offset)).scalars())
    return rows, total


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


def get_routine_by_name(session: Session, name: str) -> Routine | None:
    """Fetch a single Routine by name (case-insensitive).

    Args:
        session: Active SQLAlchemy session.
        name: The routine name to search for.

    Returns:
        Routine instance or None if not found.
    """
    stmt = select(Routine).where(func.lower(Routine.name) == func.lower(name))
    return session.execute(stmt).scalar_one_or_none()


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


def reorder_actions(
    session: Session,
    routine: Routine,
    action_ids: list[int],
) -> list[Action]:
    """Assign positions 1…n to actions in the given order.

    All supplied IDs must belong to the routine and the list must include every
    action exactly once.

    Args:
        session: Active SQLAlchemy session.
        routine: The parent Routine instance.
        action_ids: Action IDs in the desired order (first = position 1).

    Returns:
        The updated Action instances in position order.

    Raises:
        ValueError: If the supplied IDs do not exactly match the routine's actions.
    """
    existing_actions: list[Action] = list(
        session.execute(select(Action).where(Action.routine_id == routine.id)).scalars()
    )
    existing_ids = {a.id for a in existing_actions}
    if set(action_ids) != existing_ids or len(action_ids) != len(existing_ids):
        raise ValueError(
            "action_ids must contain every action in the routine exactly once"
        )

    action_by_id = {a.id: a for a in existing_actions}
    for position, action_id in enumerate(action_ids, start=1):
        action_by_id[action_id].position = position

    session.commit()
    return sorted(existing_actions, key=lambda a: a.position)


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
    """Insert a new RoutineExecution row with status 'queued'.

    The queue worker will claim the row and transition it to 'running' when
    it is the oldest item whose ``scheduled_for`` time has arrived.

    Args:
        session: Active SQLAlchemy session.
        routine_id: The Routine primary key.
        triggered_by: Label indicating who triggered the run (e.g. 'manual').

    Returns:
        The newly inserted RoutineExecution instance.
    """
    execution = RoutineExecution(
        routine_id=routine_id,
        status=EXECUTION_STATUS_QUEUED,
        triggered_by=triggered_by,
    )
    session.add(execution)
    session.commit()
    session.refresh(execution)
    return execution


def get_active_executions(session: Session) -> list[ActiveExecutionRow]:
    """Return all queued and running executions with routine name and action progress.

    Results are ordered by ``scheduled_for`` ascending so the frontend can
    render a FIFO queue view — the running item (if any) is always first,
    followed by queued items in the order they will execute.

    Args:
        session: Active SQLAlchemy session.

    Returns:
        List of dicts with execution fields, ``routine_name``, and nested
        ``action_executions`` ordered by position.
    """
    stmt = (
        select(RoutineExecution)
        .options(
            joinedload(RoutineExecution.routine),
            joinedload(RoutineExecution.action_executions),
        )
        .where(
            RoutineExecution.status.in_(
                [EXECUTION_STATUS_QUEUED, EXECUTION_STATUS_RUNNING]
            )
        )
        .order_by(RoutineExecution.scheduled_for.asc())
    )
    results = list(session.execute(stmt).scalars().unique())
    rows = cast(
        list[ActiveExecutionRow],
        [
            {
                "id": r.id,
                "routine_id": r.routine_id,
                "routine_name": r.routine.name,
                "status": r.status,
                "triggered_by": r.triggered_by,
                "queued_at": r.queued_at,
                "scheduled_for": r.scheduled_for,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "action_executions": [
                    {
                        "id": ae.id,
                        "action_id": ae.action_id,
                        "position": ae.position,
                        "action_type": ae.action_type,
                        "config": ae.config,
                        "status": ae.status,
                        "started_at": ae.started_at,
                        "completed_at": ae.completed_at,
                    }
                    for ae in sorted(r.action_executions, key=lambda x: x.position)
                ],
            }
            for r in results
        ],
    )
    return rows


def get_execution_detail(
    session: Session,
    execution_id: int,
) -> ActiveExecutionRow | None:
    """Return a single execution with routine name and action progress.

    Args:
        session: Active SQLAlchemy session.
        execution_id: Primary key of the target RoutineExecution.

    Returns:
        ActiveExecutionRow dict or None if the execution does not exist.
    """
    stmt = (
        select(RoutineExecution)
        .options(
            joinedload(RoutineExecution.routine),
            joinedload(RoutineExecution.action_executions),
        )
        .where(RoutineExecution.id == execution_id)
    )
    result = session.execute(stmt).unique().scalar_one_or_none()
    if result is None:
        return None
    return cast(
        ActiveExecutionRow,
        {
            "id": result.id,
            "routine_id": result.routine_id,
            "routine_name": result.routine.name,
            "status": result.status,
            "triggered_by": result.triggered_by,
            "queued_at": result.queued_at,
            "scheduled_for": result.scheduled_for,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "action_executions": [
                {
                    "id": ae.id,
                    "action_id": ae.action_id,
                    "position": ae.position,
                    "action_type": ae.action_type,
                    "config": ae.config,
                    "status": ae.status,
                    "started_at": ae.started_at,
                    "completed_at": ae.completed_at,
                }
                for ae in sorted(result.action_executions, key=lambda x: x.position)
            ],
        },
    )


def get_execution_history(
    session: Session,
    limit: int = 25,
    offset: int = 0,
    routine_id: int | None = None,
    search: str | None = None,
    since_minutes: int | None = None,
) -> tuple[list[ExecutionRow], int]:
    """Return paginated completed or failed executions, with optional filters.

    Args:
        session: Active SQLAlchemy session.
        limit: Maximum number of records to return.
        offset: Number of records to skip.
        routine_id: If provided, restrict results to this routine.
        search: Optional substring to filter on routine name (case-insensitive).
        since_minutes: If provided, only return executions queued within
            the last ``since_minutes`` minutes.

    Returns:
        Tuple of (page of execution dicts with ``routine_name``, total match count),
        newest first.
    """
    stmt = (
        select(RoutineExecution)
        .options(joinedload(RoutineExecution.routine))
        .where(
            RoutineExecution.status.in_(
                [EXECUTION_STATUS_COMPLETED, EXECUTION_STATUS_FAILED]
            )
        )
        .order_by(RoutineExecution.queued_at.desc())
    )
    if routine_id is not None:
        stmt = stmt.where(RoutineExecution.routine_id == routine_id)
    if search:
        # joinedload does not produce a filterable JOIN — add an explicit one
        stmt = stmt.join(RoutineExecution.routine).where(
            Routine.name.ilike(f"%{search}%")
        )
    if since_minutes is not None:
        cutoff = datetime.now(UTC) - timedelta(minutes=since_minutes)
        stmt = stmt.where(RoutineExecution.queued_at >= cutoff)
    total: int = session.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()
    results = list(session.execute(stmt.limit(limit).offset(offset)).scalars().unique())
    rows = cast(
        list[ExecutionRow],
        [
            {
                "id": r.id,
                "routine_id": r.routine_id,
                "routine_name": r.routine.name,
                "status": r.status,
                "triggered_by": r.triggered_by,
                "queued_at": r.queued_at,
                "scheduled_for": r.scheduled_for,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
            }
            for r in results
        ],
    )
    return rows, total
