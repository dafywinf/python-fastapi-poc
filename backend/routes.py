"""API route handlers for the Sequence resource.

All handlers use synchronous `def` so FastAPI runs them in the external
thread pool, keeping the event loop free from blocking database I/O.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.exceptions import handle_exception
from backend.models import Sequence
from backend.schemas import SequenceCreate, SequenceResponse, SequenceUpdate
from backend.security import WriteDep
from backend.services import (
    create_sequence,
    delete_sequence,
    get_sequence,
    list_sequences,
    update_sequence,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sequences", tags=["sequences"])

SessionDep = Annotated[Session, Depends(get_session)]


def _get_sequence_or_404(sequence_id: int, session: SessionDep) -> Sequence:
    """Shared dependency: fetch a Sequence by ID or raise 404.

    Args:
        sequence_id: Path parameter — primary key of the target Sequence.
        session: Injected database session.

    Returns:
        The requested Sequence instance.

    Raises:
        HTTPException: 404 if the Sequence does not exist.
    """
    sequence = get_sequence(session, sequence_id)
    if sequence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sequence {sequence_id} not found",
        )
    return sequence


SequenceDep = Annotated[Sequence, Depends(_get_sequence_or_404)]


@router.post(
    "/",
    response_model=SequenceResponse,
    status_code=status.HTTP_201_CREATED,
)
@handle_exception(logger)
def create(
    payload: SequenceCreate, session: SessionDep, _user: WriteDep
) -> SequenceResponse:
    """Create a new Sequence.

    Args:
        payload: Validated creation payload.
        session: Injected database session.
        _user: Authenticated username (enforces JWT auth; value unused).

    Returns:
        The created Sequence.
    """
    return SequenceResponse.model_validate(create_sequence(session, payload))


@router.get("/", response_model=list[SequenceResponse])
@handle_exception(logger)
def list_all(session: SessionDep) -> list[SequenceResponse]:
    """List all Sequences ordered by creation date descending.

    Args:
        session: Injected database session.

    Returns:
        List of Sequences.
    """
    return [SequenceResponse.model_validate(s) for s in list_sequences(session)]


@router.get("/{sequence_id}", response_model=SequenceResponse)
@handle_exception(logger)
def retrieve(sequence: SequenceDep) -> SequenceResponse:
    """Retrieve a single Sequence by ID.

    Args:
        sequence: Injected Sequence instance (raises 404 if not found).

    Returns:
        The requested Sequence.
    """
    return SequenceResponse.model_validate(sequence)


@router.patch("/{sequence_id}", response_model=SequenceResponse)
@handle_exception(logger)
def partial_update(
    sequence: SequenceDep,
    payload: SequenceUpdate,
    session: SessionDep,
    _user: WriteDep,
) -> SequenceResponse:
    """Partially update a Sequence.

    Args:
        sequence: Injected Sequence instance (raises 404 if not found).
        payload: Fields to update (None values are ignored).
        session: Injected database session.
        _user: Authenticated username (enforces JWT auth; value unused).

    Returns:
        The updated Sequence.
    """
    return SequenceResponse.model_validate(update_sequence(session, sequence, payload))


@router.delete("/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exception(logger)
def destroy(sequence: SequenceDep, session: SessionDep, _user: WriteDep) -> None:
    """Delete a Sequence.

    Args:
        sequence: Injected Sequence instance (raises 404 if not found).
        session: Injected database session.
        _user: Authenticated username (enforces JWT auth; value unused).
    """
    delete_sequence(session, sequence)
