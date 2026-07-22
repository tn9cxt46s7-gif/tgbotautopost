import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import SCHEDULER_TICK_SECONDS
from services.poster import run_posting_cycle

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_bot = None


async def _tick():
    if _bot is None:
        return
    try:
        await run_posting_cycle(_bot)
    except Exception:
        logger.exception("Posting cycle failed")
    try:
        from services.reminders import run_subscription_reminders
        await run_subscription_reminders(_bot)
    except Exception:
        logger.exception("Reminders failed")


def start_scheduler(bot):
    global _bot
    _bot = bot
    if scheduler.running:
        return
    scheduler.add_job(
        _tick,
        "interval",
        seconds=SCHEDULER_TICK_SECONDS,
        id="autopost_tick",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Scheduler started (every %ss)", SCHEDULER_TICK_SECONDS)


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
