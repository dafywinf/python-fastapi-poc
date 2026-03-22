"""Pydantic V2 DTOs for auth, users, routines, actions, and executions."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator


class TokenResponse(BaseModel):
    """Response payload for the POST /auth/token endpoint."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User profile as returned by the API — used for /users/ list and /users/me."""

    id: int
    email: str
    name: str
    picture: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Action schemas
# ---------------------------------------------------------------------------


class ActionCreate(BaseModel):
    """Payload for creating a new Action within a Routine."""

    action_type: Literal["sleep", "echo"]
    config: dict[str, Any]
    position: int | None = None  # if omitted, service appends at end


class ActionUpdate(BaseModel):
    """Payload for updating an existing Action."""

    action_type: Literal["sleep", "echo"] | None = None
    config: dict[str, Any] | None = None
    position: int | None = None  # if provided, triggers position swap


class ActionResponse(BaseModel):
    """Response DTO for an Action."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    routine_id: int
    position: int
    action_type: str
    config: dict[str, Any]


# ---------------------------------------------------------------------------
# Routine schemas
# ---------------------------------------------------------------------------


class RoutineCreate(BaseModel):
    """Payload for creating a new Routine."""

    name: str
    description: str | None = None
    schedule_type: Literal["cron", "interval", "manual"]
    schedule_config: dict[str, Any] | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def validate_schedule_config(self) -> "RoutineCreate":
        """Validate that schedule_config matches the declared schedule_type."""
        if self.schedule_type == "manual" and self.schedule_config is not None:
            raise ValueError("schedule_config must be null for manual routines")
        if self.schedule_type == "cron":
            cfg = self.schedule_config
            if not isinstance(cfg, dict) or "cron" not in cfg:
                raise ValueError(
                    'cron routines require schedule_config {"cron": "<expression>"}'
                )
        if self.schedule_type == "interval":
            cfg = self.schedule_config
            if not isinstance(cfg, dict) or "seconds" not in cfg:
                raise ValueError(
                    'interval routines require schedule_config {"seconds": <int>}'
                )
        return self


class RoutineUpdate(BaseModel):
    """Payload for updating an existing Routine."""

    name: str | None = None
    description: str | None = None
    schedule_type: Literal["cron", "interval", "manual"] | None = None
    schedule_config: dict[str, Any] | None = None
    is_active: bool | None = None


class RoutineResponse(BaseModel):
    """Response DTO for a Routine, including its nested Actions."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    schedule_type: str
    schedule_config: dict[str, Any] | None
    is_active: bool
    created_at: datetime
    actions: list[ActionResponse] = []


# ---------------------------------------------------------------------------
# Execution schemas
# ---------------------------------------------------------------------------


class RunResponse(BaseModel):
    """Response returned immediately when a Routine execution is triggered."""

    execution_id: int


class ExecutionResponse(BaseModel):
    """Response DTO for a Routine Execution record.

    ``routine_name`` is denormalised from a join and must be set manually by
    the service layer — it cannot be populated via ``from_attributes`` alone.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    routine_id: int
    routine_name: str
    status: str
    triggered_by: str
    started_at: datetime
    completed_at: datetime | None
