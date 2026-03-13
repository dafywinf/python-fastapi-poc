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
from backend.schemas import SequenceCreate, SequenceResponse, SequenceUpdate
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


@router.post(
    "/",
    response_model=SequenceResponse,
    status_code=status.HTTP_201_CREATED,
)
@handle_exception(logger)
def create(payload: SequenceCreate, session: SessionDep) -> SequenceResponse:
    """Create a new Sequence.

    Args:
        payload: Validated creation payload.
        session: Injected database session.

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
def retrieve(sequence_id: int, session: SessionDep) -> SequenceResponse:
    """Retrieve a single Sequence by ID.

    Args:
        sequence_id: Primary key of the target Sequence.
        session: Injected database session.

    Returns:
        The requested Sequence.

    Raises:
        HTTPException: 404 if the Sequence does not exist.
    """
    sequence = get_sequence(session, sequence_id)
    if sequence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sequence {sequence_id} not found",
        )
    return SequenceResponse.model_validate(sequence)


@router.patch("/{sequence_id}", response_model=SequenceResponse)
@handle_exception(logger)
def partial_update(
    sequence_id: int,
    payload: SequenceUpdate,
    session: SessionDep,
) -> SequenceResponse:
    """Partially update a Sequence.

    Args:
        sequence_id: Primary key of the target Sequence.
        payload: Fields to update (None values are ignored).
        session: Injected database session.

    Returns:
        The updated Sequence.

    Raises:
        HTTPException: 404 if the Sequence does not exist.
    """
    sequence = get_sequence(session, sequence_id)
    if sequence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sequence {sequence_id} not found",
        )
    return SequenceResponse.model_validate(update_sequence(session, sequence, payload))


@router.delete("/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exception(logger)
def destroy(sequence_id: int, session: SessionDep) -> None:
    """Delete a Sequence.

    Args:
        sequence_id: Primary key of the target Sequence.
        session: Injected database session.

    Raises:
        HTTPException: 404 if the Sequence does not exist.
    """
    sequence = get_sequence(session, sequence_id)
    if sequence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sequence {sequence_id} not found",
        )
    delete_sequence(session, sequence)
