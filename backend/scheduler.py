"""APScheduler wrapper — registers and manages routine jobs."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.execution_engine import run_routine
from backend.models import Routine

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _job_id(routine_id: int) -> str:
    return f"routine_{routine_id}"


def register_routine(routine: Routine) -> None:
    """Add or replace the APScheduler job for a routine.

    Args:
        routine: The Routine ORM instance to register.
    """
    jid = _job_id(routine.id)
    if routine.schedule_type == "cron":
        cfg = routine.schedule_config or {}
        trigger: CronTrigger | IntervalTrigger = CronTrigger.from_crontab(  # pyright: ignore[reportUnknownMemberType]
            str(cfg.get("cron", ""))
        )
    elif routine.schedule_type == "interval":
        cfg = routine.schedule_config or {}
        trigger = IntervalTrigger(seconds=int(cfg.get("seconds", 60)))
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
