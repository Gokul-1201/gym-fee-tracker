from django.conf import settings
from django.utils import timezone

from ..models import Attendance, Member


def check_in(member: Member, method="qr"):
    """Returns (ok, level, message). level is one of: success, warning, error."""
    if member.status != "active":
        return False, "error", f"{member.name} is {member.get_status_display().lower()} — membership not active."
    if member.fee_state == "overdue" and not settings.ALLOW_OVERDUE_CHECKIN:
        return False, "error", f"{member.name}'s fee is overdue. Collect payment before entry."

    attendance, created = Attendance.objects.get_or_create(
        member=member, date=timezone.localdate(),
        defaults={"check_in": timezone.now(), "method": method},
    )
    if not created:
        t = timezone.localtime(attendance.check_in).strftime("%I:%M %p")
        return True, "warning", f"{member.name} already checked in today at {t}."
    if member.fee_state == "overdue":
        return True, "warning", f"Welcome {member.name}! Fee is overdue by {abs(member.days_left)} day(s) — please renew."
    return True, "success", f"Welcome, {member.name}! Checked in."
