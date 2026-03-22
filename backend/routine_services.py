"""Business logic for Routine, Action, and RoutineExecution operations."""

from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session, joinedload

from backend.models import Action, Routine, RoutineExecution
from backend.scheduler import register_routine, unregister_routine
from backend.schemas import ActionCreate, ActionUpdate, RoutineCreate, RoutineUpdate

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
    if routine.is_active and routine.schedule_type != "manual":
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
    prev_is_active = routine.is_active
    prev_schedule_type = routine.schedule_type
    prev_schedule_config = routine.schedule_config

    if payload.name is not None:
        routine.name = payload.name
    if payload.description is not None:
        routine.description = payload.description
    if payload.schedule_type is not None:
        routine.schedule_type = payload.schedule_type
    if payload.schedule_config is not None:
        routine.schedule_config = payload.schedule_config
    if payload.is_active is not None:
        routine.is_active = payload.is_active

    session.commit()
    session.refresh(routine)

    new_is_active = routine.is_active

    if prev_is_active and not new_is_active:
        # Active → inactive: remove the job
        unregister_routine(routine.id)
    elif not prev_is_active and new_is_active:
        # Inactive → active: register the job
        register_routine(routine)
    elif new_is_active:
        # Still active — check if schedule changed
        schedule_changed = (
            routine.schedule_type != prev_schedule_type
            or routine.schedule_config != prev_schedule_config
        )
        if schedule_changed:
            register_routine(routine)  # replace_existing=True handles reschedule

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

    Args:
        session: Active SQLAlchemy session.
        routine_id: The parent Routine primary key.
        payload: Validated creation payload.

    Returns:
        The newly created Action instance.
    """
    if payload.position is None:
        max_pos: int | None = session.execute(
            select(func.max(Action.position)).where(Action.routine_id == routine_id)
        ).scalar_one_or_none()
        position = (max_pos or 0) + 1
    else:
        position = payload.position

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
        HTTPException: 422 if the requested position is out of range.
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
            raise HTTPException(status_code=422, detail="Position out of range")
        old_pos = action.position
        action.position = new_pos
        other.position = old_pos
        session.flush()

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
    session: Session, routine_id: int, triggered_by: str
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
        status="running",
        triggered_by=triggered_by,
    )
    session.add(execution)
    session.commit()
    session.refresh(execution)
    return execution


def get_active_executions(session: Session) -> list[dict[str, Any]]:
    """Return all currently running executions joined with routine name.

    Args:
        session: Active SQLAlchemy session.

    Returns:
        List of dicts with execution fields plus ``routine_name``.
    """
    stmt = (
        select(RoutineExecution)
        .options(joinedload(RoutineExecution.routine))
        .where(RoutineExecution.status == "running")
        .order_by(RoutineExecution.started_at.desc())
    )
    results = list(session.execute(stmt).scalars().unique())
    return [
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
    ]


def get_execution_history(
    session: Session,
    limit: int = 10,
    routine_id: int | None = None,
) -> list[dict[str, Any]]:
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
        .where(RoutineExecution.status.in_(["completed", "failed"]))
        .order_by(RoutineExecution.started_at.desc())
        .limit(limit)
    )
    if routine_id is not None:
        stmt = stmt.where(RoutineExecution.routine_id == routine_id)
    results = list(session.execute(stmt).scalars().unique())
    return [
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
    ]
