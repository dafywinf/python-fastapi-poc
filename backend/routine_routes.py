"""API route handlers for Routine, Action, and Execution resources.

All handlers use synchronous `def` so FastAPI runs them in the external
thread pool, keeping the event loop free from blocking database I/O.
"""

import logging
from threading import Thread
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.exceptions import handle_exception
from backend.execution_engine import run_routine
from backend.models import Action, Routine
from backend.routine_services import (
    create_action,
    create_routine,
    delete_action,
    delete_routine,
    get_active_executions,
    get_execution_history,
    get_routine,
    insert_execution_row,
    list_actions,
    list_routines,
    update_action,
    update_routine,
)
from backend.schemas import (
    ActionCreate,
    ActionResponse,
    ActionUpdate,
    ExecutionResponse,
    RoutineCreate,
    RoutineResponse,
    RoutineUpdate,
    RunResponse,
)
from backend.security import WriteDep

logger = logging.getLogger(__name__)

routines_router = APIRouter(prefix="/routines", tags=["routines"])
actions_router = APIRouter(prefix="/actions", tags=["actions"])
executions_router = APIRouter(prefix="/executions", tags=["executions"])

SessionDep = Annotated[Session, Depends(get_session)]


def _get_routine_or_404(routine_id: int, session: SessionDep) -> Routine:
    """Shared dependency: fetch a Routine by ID or raise 404.

    Args:
        routine_id: Path parameter — primary key of the target Routine.
        session: Injected database session.

    Returns:
        The requested Routine instance.

    Raises:
        HTTPException: 404 if the Routine does not exist.
    """
    routine = get_routine(session, routine_id)
    if routine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Routine {routine_id} not found",
        )
    return routine


RoutineDep = Annotated[Routine, Depends(_get_routine_or_404)]


def _get_action_or_404(action_id: int, session: SessionDep) -> Action:
    """Shared dependency: fetch an Action by ID or raise 404.

    Args:
        action_id: Path parameter — primary key of the target Action.
        session: Injected database session.

    Returns:
        The requested Action instance.

    Raises:
        HTTPException: 404 if the Action does not exist.
    """
    action = session.get(Action, action_id)
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action {action_id} not found",
        )
    return action


ActionDep = Annotated[Action, Depends(_get_action_or_404)]


# ---------------------------------------------------------------------------
# Routine handlers
# ---------------------------------------------------------------------------


@routines_router.get("/", response_model=list[RoutineResponse])
@handle_exception(logger)
def list_routines_handler(session: SessionDep) -> list[RoutineResponse]:
    """List all Routines ordered by creation date descending.

    Args:
        session: Injected database session.

    Returns:
        List of Routines with their nested Actions.
    """
    return [RoutineResponse.model_validate(r) for r in list_routines(session)]


@routines_router.post(
    "/",
    response_model=RoutineResponse,
    status_code=status.HTTP_201_CREATED,
)
@handle_exception(logger)
def create_routine_handler(
    payload: RoutineCreate, session: SessionDep, _user: WriteDep
) -> RoutineResponse:
    """Create a new Routine.

    Args:
        payload: Validated creation payload.
        session: Injected database session.
        _user: Authenticated username (enforces JWT auth; value unused).

    Returns:
        The created Routine with its nested Actions.
    """
    return RoutineResponse.model_validate(create_routine(session, payload))


@routines_router.get("/{routine_id}", response_model=RoutineResponse)
@handle_exception(logger)
def get_routine_handler(routine: RoutineDep) -> RoutineResponse:
    """Retrieve a single Routine by ID.

    Args:
        routine: Injected Routine instance (raises 404 if not found).

    Returns:
        The requested Routine with its nested Actions.
    """
    return RoutineResponse.model_validate(routine)


@routines_router.put("/{routine_id}", response_model=RoutineResponse)
@handle_exception(logger)
def update_routine_handler(
    routine: RoutineDep,
    payload: RoutineUpdate,
    session: SessionDep,
    _user: WriteDep,
) -> RoutineResponse:
    """Update an existing Routine.

    Args:
        routine: Injected Routine instance (raises 404 if not found).
        payload: Fields to update (None values are ignored).
        session: Injected database session.
        _user: Authenticated username (enforces JWT auth; value unused).

    Returns:
        The updated Routine with its nested Actions.
    """
    return RoutineResponse.model_validate(update_routine(session, routine, payload))


@routines_router.delete("/{routine_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exception(logger)
def delete_routine_handler(
    routine: RoutineDep, session: SessionDep, _user: WriteDep
) -> None:
    """Delete a Routine and its associated Actions.

    Args:
        routine: Injected Routine instance (raises 404 if not found).
        session: Injected database session.
        _user: Authenticated username (enforces JWT auth; value unused).
    """
    delete_routine(session, routine)


@routines_router.get("/{routine_id}/actions", response_model=list[ActionResponse])
@handle_exception(logger)
def list_actions_handler(
    routine: RoutineDep, session: SessionDep
) -> list[ActionResponse]:
    """List all Actions for a Routine in position order.

    Args:
        routine: Injected Routine instance (raises 404 if not found).
        session: Injected database session.

    Returns:
        List of Actions ordered by position.
    """
    return [ActionResponse.model_validate(a) for a in list_actions(session, routine.id)]


@routines_router.post(
    "/{routine_id}/actions",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
)
@handle_exception(logger)
def create_action_handler(
    routine: RoutineDep,
    payload: ActionCreate,
    session: SessionDep,
    _user: WriteDep,
) -> ActionResponse:
    """Create a new Action within a Routine.

    Args:
        routine: Injected Routine instance (raises 404 if not found).
        payload: Validated creation payload.
        session: Injected database session.
        _user: Authenticated username (enforces JWT auth; value unused).

    Returns:
        The created Action.
    """
    return ActionResponse.model_validate(create_action(session, routine.id, payload))


@routines_router.post(
    "/{routine_id}/run",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@handle_exception(logger)
def run_now_handler(
    routine: RoutineDep, session: SessionDep, _user: WriteDep
) -> RunResponse:
    """Trigger an immediate execution of a Routine.

    Inserts a RoutineExecution row and starts the engine in a daemon thread.
    Returns 409 if the routine is already running.

    Args:
        routine: Injected Routine instance (raises 404 if not found).
        session: Injected database session.
        _user: Authenticated username (enforces JWT auth; value unused).

    Returns:
        RunResponse containing the new execution ID.

    Raises:
        HTTPException: 409 if the Routine is already running.
    """
    try:
        execution = insert_execution_row(session, routine.id, triggered_by="manual")
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Routine is already running",
        )
    thread = Thread(
        target=run_routine,
        args=[routine.id, "manual", execution.id],
        daemon=True,
    )
    thread.start()
    return RunResponse(execution_id=execution.id)


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------


@actions_router.put("/{action_id}", response_model=ActionResponse)
@handle_exception(logger)
def update_action_handler(
    action: ActionDep,
    payload: ActionUpdate,
    session: SessionDep,
    _user: WriteDep,
) -> ActionResponse:
    """Update an existing Action.

    Args:
        action: Injected Action instance (raises 404 if not found).
        payload: Fields to update (None values are ignored).
        session: Injected database session.
        _user: Authenticated username (enforces JWT auth; value unused).

    Returns:
        The updated Action.
    """
    return ActionResponse.model_validate(update_action(session, action, payload))


@actions_router.delete("/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exception(logger)
def delete_action_handler(
    action: ActionDep, session: SessionDep, _user: WriteDep
) -> None:
    """Delete an Action and compact the position sequence.

    Args:
        action: Injected Action instance (raises 404 if not found).
        session: Injected database session.
        _user: Authenticated username (enforces JWT auth; value unused).
    """
    delete_action(session, action)


# ---------------------------------------------------------------------------
# Execution handlers
# ---------------------------------------------------------------------------


@executions_router.get("/active", response_model=list[ExecutionResponse])
@handle_exception(logger)
def active_executions_handler(session: SessionDep) -> list[ExecutionResponse]:
    """Return all currently running Routine executions.

    Args:
        session: Injected database session.

    Returns:
        List of running ExecutionResponse records, newest first.
    """
    rows = get_active_executions(session)
    return [ExecutionResponse(**row) for row in rows]


@executions_router.get("/history", response_model=list[ExecutionResponse])
@handle_exception(logger)
def history_handler(
    session: SessionDep,
    limit: int = 10,
    routine_id: int | None = None,
) -> list[ExecutionResponse]:
    """Return completed or failed Routine executions.

    Args:
        session: Injected database session.
        limit: Maximum number of records to return (default 10).
        routine_id: If provided, restrict results to this routine.

    Returns:
        List of ExecutionResponse records, newest first.
    """
    rows = get_execution_history(session, limit=limit, routine_id=routine_id)
    return [ExecutionResponse(**row) for row in rows]
