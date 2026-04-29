"""API route handlers for Routine, Action, and Execution resources.

All handlers use synchronous `def` so FastAPI runs them in the external
thread pool, keeping the event loop free from blocking database I/O.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.domain_types import EXECUTION_TRIGGER_MANUAL
from backend.exceptions import handle_exception
from backend.execution_engine import enqueue_routine_run
from backend.models import Action, Routine
from backend.routine_services import (
    create_action,
    create_routine,
    delete_action,
    delete_routine,
    get_active_executions,
    get_execution_detail,
    get_execution_history,
    get_routine,
    get_routine_by_name,
    list_actions,
    list_routines,
    reorder_actions,
    update_action,
    update_routine,
)
from backend.schemas import (
    ActionCreate,
    ActionResponse,
    ActionsReorderRequest,
    ActionUpdate,
    ActiveExecutionResponse,
    ExecutionResponse,
    PageResponse,
    RoutineCreate,
    RoutineResponse,
    RoutineUpdate,
    RunRequest,
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


@routines_router.get("/", response_model=PageResponse[RoutineResponse])
@handle_exception(logger)
def list_routines_handler(
    session: SessionDep,
    search: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> PageResponse[RoutineResponse]:
    """List Routines ordered newest first, with optional search and pagination.

    Args:
        session: Injected database session.
        search: Optional substring filter on routine name (case-insensitive).
        limit: Maximum number of records to return (default 25).
        offset: Number of records to skip (default 0).

    Returns:
        Paginated page of Routines with their nested Actions.
    """
    items, total = list_routines(session, search=search, limit=limit, offset=offset)
    return PageResponse(
        items=[RoutineResponse.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


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

    Raises:
        HTTPException: 409 if a routine with the same name already exists.
    """
    if get_routine_by_name(session, payload.name.strip()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A routine named '{payload.name.strip()}' already exists",
        )
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
    try:
        return RoutineResponse.model_validate(update_routine(session, routine, payload))
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)
        ) from err


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
    try:
        action = create_action(session, routine.id, payload)
        return ActionResponse.model_validate(action)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)
        ) from err


@routines_router.patch(
    "/{routine_id}/actions/reorder",
    response_model=list[ActionResponse],
)
@handle_exception(logger)
def reorder_actions_handler(
    routine: RoutineDep,
    payload: ActionsReorderRequest,
    session: SessionDep,
    _user: WriteDep,
) -> list[ActionResponse]:
    """Bulk-reorder Actions within a Routine by supplying IDs in the desired order.

    All action IDs for the routine must be supplied exactly once. The service
    assigns positions 1…n in the given order.

    Args:
        routine: Injected Routine instance (raises 404 if not found).
        payload: Ordered list of action IDs.
        session: Injected database session.
        _user: Authenticated username (enforces JWT auth; value unused).

    Returns:
        The updated Actions in position order.
    """
    try:
        actions = reorder_actions(session, routine, payload.action_ids)
        return [ActionResponse.model_validate(a) for a in actions]
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)
        ) from err


@routines_router.post(
    "/{routine_id}/run",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@handle_exception(logger)
def run_now_handler(
    routine: RoutineDep,
    session: SessionDep,
    _user: WriteDep,
    body: RunRequest | None = None,
) -> RunResponse:
    """Queue an execution of a Routine, optionally at a future time.

    Inserts a RoutineExecution row with status 'queued'. The global execution
    queue worker will pick it up once ``scheduled_for`` has arrived (defaults
    to now for immediate runs). Multiple calls are allowed — each adds a new
    entry to the queue.

    Args:
        routine: Injected Routine instance (raises 404 if not found).
        _user: Authenticated username (enforces JWT auth; value unused).
        body: Optional. Supply ``scheduled_for`` to delay execution until a
            future UTC datetime.

    Returns:
        RunResponse containing the new execution ID.
    """
    scheduled_for = body.utc_scheduled_for() if body else None
    execution_id = enqueue_routine_run(
        routine.id, EXECUTION_TRIGGER_MANUAL, scheduled_for, session
    )
    return RunResponse(execution_id=execution_id)


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
    try:
        return ActionResponse.model_validate(update_action(session, action, payload))
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)
        ) from err


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


@executions_router.get("/active", response_model=list[ActiveExecutionResponse])
@handle_exception(logger)
def active_executions_handler(session: SessionDep) -> list[ActiveExecutionResponse]:
    """Return all currently running Routine executions with per-action progress.

    Args:
        session: Injected database session.

    Returns:
        List of running ActiveExecutionResponse records, newest first.
    """
    rows = get_active_executions(session)
    return [ActiveExecutionResponse.model_validate(row) for row in rows]


@executions_router.get("/history", response_model=PageResponse[ExecutionResponse])
@handle_exception(logger)
def history_handler(
    session: SessionDep,
    limit: int = 25,
    offset: int = 0,
    routine_id: int | None = None,
    search: str | None = None,
    since_minutes: int | None = None,
) -> PageResponse[ExecutionResponse]:
    """Return completed or failed Routine executions with pagination and filters.

    Args:
        session: Injected database session.
        limit: Maximum number of records to return (default 25).
        offset: Number of records to skip (default 0).
        routine_id: If provided, restrict results to this routine.
        search: Optional substring filter on routine name (case-insensitive).
        since_minutes: If provided, only return executions queued within
            the last ``since_minutes`` minutes.

    Returns:
        Paginated page of ExecutionResponse records, newest first.
    """
    rows, total = get_execution_history(
        session,
        limit=limit,
        offset=offset,
        routine_id=routine_id,
        search=search,
        since_minutes=since_minutes,
    )
    return PageResponse(
        items=[ExecutionResponse(**row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@executions_router.get("/{execution_id}", response_model=ActiveExecutionResponse)
@handle_exception(logger)
def get_execution_handler(
    execution_id: int, session: SessionDep
) -> ActiveExecutionResponse:
    """Return full details for a single execution including per-action progress.

    Args:
        execution_id: Path parameter — primary key of the target execution.
        session: Injected database session.

    Returns:
        ActiveExecutionResponse with nested action executions.

    Raises:
        HTTPException: 404 if the execution does not exist.
    """
    row = get_execution_detail(session, execution_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found",
        )
    return ActiveExecutionResponse.model_validate(row)
