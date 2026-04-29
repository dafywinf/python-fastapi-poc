"""Pydantic V2 DTOs for auth, users, routines, actions, and executions."""

from datetime import datetime, timezone
from typing import Generic, TypeVar

from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel, ConfigDict, model_validator

from backend.domain_types import (
    ACTION_TYPE_ECHO,
    SCHEDULE_TYPE_CRON,
    SCHEDULE_TYPE_INTERVAL,
    SCHEDULE_TYPE_MANUAL,
    ActionExecutionStatus,
    ActionType,
    ExecutionStatus,
    ExecutionTrigger,
    JSONObject,
    ScheduleType,
)

_T = TypeVar("_T")


class PageResponse(BaseModel, Generic[_T]):
    """Generic paginated response envelope returned by list endpoints."""

    items: list[_T]
    total: int
    limit: int
    offset: int


def validate_routine_schedule(
    schedule_type: ScheduleType,
    schedule_config: JSONObject | None,
) -> None:
    """Validate that schedule_config matches the declared schedule_type."""
    if schedule_type == SCHEDULE_TYPE_MANUAL and schedule_config is not None:
        raise ValueError("schedule_config must be null for manual routines")
    if schedule_type == SCHEDULE_TYPE_CRON:
        cfg = schedule_config
        if not isinstance(cfg, dict) or "cron" not in cfg:
            raise ValueError(
                'cron routines require schedule_config {"cron": "<expression>"}'
            )
        try:
            CronTrigger.from_crontab(str(cfg["cron"]))  # pyright: ignore[reportUnknownMemberType]
        except ValueError as err:
            raise ValueError("schedule_config.cron must be a valid crontab") from err
    if schedule_type == SCHEDULE_TYPE_INTERVAL:
        cfg = schedule_config
        if not isinstance(cfg, dict) or "seconds" not in cfg:
            raise ValueError(
                'interval routines require schedule_config {"seconds": <int>}'
            )
        seconds = cfg["seconds"]
        if not isinstance(seconds, int) or seconds <= 0:
            raise ValueError("schedule_config.seconds must be a positive integer")


def validate_action_config(action_type: ActionType, config: JSONObject) -> None:
    """Validate that action config matches the declared action type."""
    if action_type == ACTION_TYPE_ECHO:
        message = config.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ValueError(
                'echo actions require config {"message": "<non-empty text>"}'
            )
        return

    seconds = config.get("seconds")
    if not isinstance(seconds, int) or seconds < 0:
        raise ValueError('sleep actions require config {"seconds": <int>=0+}')


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

    action_type: ActionType
    config: JSONObject
    position: int | None = None  # if omitted, service appends at end

    @model_validator(mode="after")
    def validate_config(self) -> "ActionCreate":
        """Validate that config matches the declared action type."""
        validate_action_config(self.action_type, self.config)
        return self


class ActionsReorderRequest(BaseModel):
    """Ordered list of action IDs for bulk reordering.

    The backend assigns position 1…n to the supplied IDs in the given order.
    All IDs must belong to the target routine.
    """

    action_ids: list[int]


class ActionUpdate(BaseModel):
    """Payload for updating an existing Action."""

    action_type: ActionType | None = None
    config: JSONObject | None = None
    position: int | None = None  # if provided, triggers position swap

    @model_validator(mode="after")
    def validate_config(self) -> "ActionUpdate":
        """Validate config when both config and action type are known."""
        next_action_type = self.action_type
        if next_action_type is not None and self.config is not None:
            validate_action_config(next_action_type, self.config)
        return self


class ActionResponse(BaseModel):
    """Response DTO for an Action."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    routine_id: int
    position: int
    action_type: ActionType
    config: JSONObject


# ---------------------------------------------------------------------------
# Routine schemas
# ---------------------------------------------------------------------------


class RoutineCreate(BaseModel):
    """Payload for creating a new Routine."""

    name: str
    description: str | None = None
    schedule_type: ScheduleType
    schedule_config: JSONObject | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def validate_schedule_config(self) -> "RoutineCreate":
        """Validate that schedule_config matches the declared schedule_type."""
        validate_routine_schedule(self.schedule_type, self.schedule_config)
        return self


class RoutineUpdate(BaseModel):
    """Payload for updating an existing Routine."""

    name: str | None = None
    description: str | None = None
    schedule_type: ScheduleType | None = None
    schedule_config: JSONObject | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_schedule_config(self) -> "RoutineUpdate":
        """Validate explicitly-provided schedule fields when enough context exists."""
        fields_set = self.model_fields_set
        schedule_type_provided = "schedule_type" in fields_set
        schedule_config_provided = "schedule_config" in fields_set

        if schedule_type_provided and self.schedule_type is not None:
            if (
                self.schedule_type == SCHEDULE_TYPE_MANUAL
                and not schedule_config_provided
            ):
                return self
            validate_routine_schedule(self.schedule_type, self.schedule_config)
        elif (
            schedule_config_provided
            and self.schedule_config is not None
            and not any(key in self.schedule_config for key in ("cron", "seconds"))
        ):
            raise ValueError(
                "schedule_config updates must include a supported key "
                'like "cron" or "seconds"'
            )
        return self


class RoutineResponse(BaseModel):
    """Response DTO for a Routine, including its nested Actions."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    schedule_type: ScheduleType
    schedule_config: JSONObject | None
    is_active: bool
    created_at: datetime
    actions: list[ActionResponse] = []


# ---------------------------------------------------------------------------
# Execution schemas
# ---------------------------------------------------------------------------


class RunRequest(BaseModel):
    """Optional body for the run endpoint.

    ``scheduled_for`` sets the earliest time the queue worker may start the
    execution.  Omit or pass ``null`` for immediate execution (scheduled_for
    defaults to the current time inside ``enqueue_routine_run``).
    """

    scheduled_for: datetime | None = None

    def utc_scheduled_for(self) -> datetime | None:
        """Return scheduled_for normalised to UTC, or None for immediate runs."""
        if self.scheduled_for is None:
            return None
        if self.scheduled_for.tzinfo is None:
            return self.scheduled_for.replace(tzinfo=timezone.utc)
        return self.scheduled_for.astimezone(timezone.utc)


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
    status: ExecutionStatus
    triggered_by: ExecutionTrigger
    queued_at: datetime
    scheduled_for: datetime
    started_at: datetime | None
    completed_at: datetime | None


class ActionExecutionResponse(BaseModel):
    """Response DTO for a single Action's execution record within a RoutineExecution."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    action_id: int
    position: int
    action_type: ActionType
    config: JSONObject
    status: ActionExecutionStatus
    started_at: datetime | None
    completed_at: datetime | None


class ActiveExecutionResponse(ExecutionResponse):
    """Execution response extended with per-action progress.

    Used by the ``GET /executions/active`` endpoint.
    """

    action_executions: list[ActionExecutionResponse] = []
