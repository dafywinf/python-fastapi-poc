"""Pydantic V2 DTOs for the Sequence resource and auth responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TokenResponse(BaseModel):
    """Response payload for the POST /auth/token endpoint."""

    access_token: str
    token_type: str = "bearer"


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


class UserResponse(BaseModel):
    """User profile as returned by the API — used for /users/ list and /users/me."""

    id: int
    email: str
    name: str
    picture: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
