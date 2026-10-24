"""Builds and sends due-date reminders; used by the web UI, the CLI command and the scheduler."""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from ..models import Member, ReminderLog
from .notifications import send_message


def build_message(member: Member) -> str:
    gym = settings.GYM_NAME
    plan = member.plan
    amount = f"{settings.CURRENCY}{plan.price:g}" if plan else "your membership fee"
    d = member.days_left
    due = member.next_due_date.strftime("%d %b %Y")
    if d is None:
        return f"Hi {member.name}, this is {gym}. Please contact the front desk about your membership fee."
    if d < 0:
        return (f"Hi {member.name}, your {gym} fee of {amount} was due on {due} "
                f"({abs(d)} day(s) ago). Please pay at the desk or via UPI to keep your membership active. Thank you!")
    if d == 0:
        return f"Hi {member.name}, your {gym} fee of {amount} is due today ({due}). Thank you!"
    return f"Hi {member.name}, a friendly reminder: your {gym} fee of {amount} is due on {due} ({d} day(s) left)."


def send_reminder_for(member: Member, force=False):
    """Send one member's reminder on every configured channel. Returns number of successful sends."""
    if not force:
        since = timezone.now() - timedelta(days=settings.REMINDER_COOLDOWN_DAYS)
        if ReminderLog.objects.filter(member=member, success=True, sent_at__gte=since).exists():
            return 0
    text = build_message(member)
    sent = 0
    for channel in settings.NOTIFY_CHANNELS:
        ok, error = send_message(member.phone, text, channel)
        ReminderLog.objects.create(member=member, channel=channel, message=text, success=ok, error=error)
        sent += int(ok)
    return sent


def members_needing_reminder():
    today = timezone.localdate()
    horizon = today + timedelta(days=settings.REMINDER_DAYS_BEFORE)
    return Member.objects.filter(status="active", next_due_date__lte=horizon).select_related("plan")


def run_reminders(force=False):
    """Returns (members_contacted, messages_sent)."""
    contacted = messages = 0
    for member in members_needing_reminder():
        n = send_reminder_for(member, force=force)
        if n:
            contacted += 1
            messages += n
    return contacted, messages
