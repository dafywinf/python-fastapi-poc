"""Business logic for Sequence operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Sequence
from backend.schemas import SequenceCreate, SequenceUpdate


def create_sequence(session: Session, payload: SequenceCreate) -> Sequence:
    """Create and persist a new Sequence.

    Args:
        session: Active SQLAlchemy session.
        payload: Validated creation payload.

    Returns:
        The newly created Sequence instance.
    """
    sequence = Sequence(name=payload.name, description=payload.description)
    session.add(sequence)
    session.commit()
    session.refresh(sequence)
    return sequence


def list_sequences(session: Session) -> list[Sequence]:
    """Return all Sequence records ordered by creation date descending.

    Args:
        session: Active SQLAlchemy session.

    Returns:
        List of Sequence instances.
    """
    return list(
        session.execute(select(Sequence).order_by(Sequence.created_at.desc())).scalars()
    )


def get_sequence(session: Session, sequence_id: int) -> Sequence | None:
    """Fetch a single Sequence by primary key.

    Args:
        session: Active SQLAlchemy session.
        sequence_id: Primary key of the target record.

    Returns:
        Sequence instance or None if not found.
    """
    return session.get(Sequence, sequence_id)


def update_sequence(
    session: Session,
    sequence: Sequence,
    payload: SequenceUpdate,
) -> Sequence:
    """Apply partial updates to a Sequence.

    Args:
        session: Active SQLAlchemy session.
        sequence: The existing Sequence instance to update.
        payload: Validated update payload (None fields are ignored).

    Returns:
        The updated Sequence instance.
    """
    if payload.name is not None:
        sequence.name = payload.name
    if payload.description is not None:
        sequence.description = payload.description
    session.commit()
    session.refresh(sequence)
    return sequence


def delete_sequence(session: Session, sequence: Sequence) -> None:
    """Delete a Sequence record.

    Args:
        session: Active SQLAlchemy session.
        sequence: The Sequence instance to delete.
    """
    session.delete(sequence)
    session.commit()
