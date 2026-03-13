"""Pydantic V2 DTOs for the Sequence resource."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SequenceCreate(BaseModel):
    """Payload for creating a new Sequence."""

    name: str
    description: str | None = None


class SequenceUpdate(BaseModel):
    """Payload for updating an existing Sequence."""

    name: str | None = None
    description: str | None = None


class SequenceResponse(BaseModel):
    """Response DTO returned to the caller."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
