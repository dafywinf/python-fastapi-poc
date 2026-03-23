"""APScheduler wrapper — registers and manages routine jobs."""

import logging
from dataclasses import dataclass

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.domain_types import (
    SCHEDULE_TYPE_CRON,
    SCHEDULE_TYPE_INTERVAL,
    JSONObject,
    ScheduleType,
)
from backend.execution_engine import run_routine
from backend.models import Routine

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


@dataclass(frozen=True)
class RoutineSchedulerSnapshot:
    """Minimal immutable routine data needed for scheduler registration."""

    id: int
    is_active: bool
    schedule_type: ScheduleType
    schedule_config: JSONObject | None


def _job_id(routine_id: int) -> str:
    return f"routine_{routine_id}"


def register_routine(routine: Routine | RoutineSchedulerSnapshot) -> None:
    """Add or replace the APScheduler job for a routine.

    Args:
        routine: The Routine ORM instance to register.
    """
    jid = _job_id(routine.id)
    if routine.schedule_type == SCHEDULE_TYPE_CRON:
        cfg = routine.schedule_config or {}
        cron_expr = str(cfg.get("cron", ""))
        try:
            trigger: CronTrigger | IntervalTrigger = CronTrigger.from_crontab(  # pyright: ignore[reportUnknownMemberType]
                cron_expr
            )
        except ValueError as err:
            raise ValueError(
                f"Routine {routine.id}: invalid cron expression '{cron_expr}'"
            ) from err
    elif routine.schedule_type == SCHEDULE_TYPE_INTERVAL:
        cfg = routine.schedule_config or {}
        seconds = cfg.get("seconds", 60)
        if not isinstance(seconds, int):
            raise ValueError("interval routines require integer seconds")
        trigger = IntervalTrigger(seconds=seconds)
    else:
        return  # manual — no job registered
    scheduler.add_job(  # pyright: ignore[reportUnknownMemberType]
        run_routine,
        trigger,
        id=jid,
        replace_existing=True,
        args=[routine.id, routine.schedule_type],
    )
    logger.info("Registered scheduler job %s", jid)


def unregister_routine(routine_id: int) -> None:
    """Remove the APScheduler job for a routine if it exists.

    Args:
        routine_id: The ID of the routine to unregister.
    """
    jid = _job_id(routine_id)
    if scheduler.get_job(jid) is not None:  # pyright: ignore[reportUnknownMemberType]
        scheduler.remove_job(jid)  # pyright: ignore[reportUnknownMemberType]
        logger.info("Unregistered scheduler job %s", jid)
