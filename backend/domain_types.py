"""Shared domain literals and JSON type aliases."""

from typing import Literal, TypeAlias

JSONPrimitive: TypeAlias = str | int | float | bool | None
JSONObject: TypeAlias = dict[str, JSONPrimitive]

ScheduleType: TypeAlias = Literal["cron", "interval", "manual"]
ActionType: TypeAlias = Literal["sleep", "echo"]
ExecutionStatus: TypeAlias = Literal["queued", "running", "completed", "failed"]
ExecutionTrigger: TypeAlias = Literal["cron", "interval", "manual"]
ActionExecutionStatus: TypeAlias = Literal["pending", "running", "completed", "failed"]

SCHEDULE_TYPE_CRON: ScheduleType = "cron"
SCHEDULE_TYPE_INTERVAL: ScheduleType = "interval"
SCHEDULE_TYPE_MANUAL: ScheduleType = "manual"

ACTION_TYPE_SLEEP: ActionType = "sleep"
ACTION_TYPE_ECHO: ActionType = "echo"

EXECUTION_STATUS_QUEUED: ExecutionStatus = "queued"
EXECUTION_STATUS_RUNNING: ExecutionStatus = "running"
EXECUTION_STATUS_COMPLETED: ExecutionStatus = "completed"
EXECUTION_STATUS_FAILED: ExecutionStatus = "failed"

EXECUTION_TRIGGER_CRON: ExecutionTrigger = "cron"
EXECUTION_TRIGGER_INTERVAL: ExecutionTrigger = "interval"
EXECUTION_TRIGGER_MANUAL: ExecutionTrigger = "manual"

ACTION_EXECUTION_STATUS_PENDING: ActionExecutionStatus = "pending"
ACTION_EXECUTION_STATUS_RUNNING: ActionExecutionStatus = "running"
ACTION_EXECUTION_STATUS_COMPLETED: ActionExecutionStatus = "completed"
ACTION_EXECUTION_STATUS_FAILED: ActionExecutionStatus = "failed"
