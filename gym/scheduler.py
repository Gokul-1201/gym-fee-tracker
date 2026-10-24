import logging

from django.conf import settings

log = logging.getLogger(__name__)


def start():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        log.warning("APScheduler not installed; automatic reminders disabled.")
        return
    from .services.reminders import run_reminders

    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_job(run_reminders, "cron", hour=settings.REMINDER_HOUR, minute=0,
                      id="daily_reminders", replace_existing=True)
    scheduler.start()
    log.info("Reminder scheduler started (daily at %02d:00).", settings.REMINDER_HOUR)
