import uuid

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


def new_token():
    return uuid.uuid4().hex


def today():
    return timezone.localdate()


class Plan(models.Model):
    MONTHLY, ANNUAL = "monthly", "annual"
    CYCLES = [(MONTHLY, "Monthly"), (ANNUAL, "Annual")]

    name = models.CharField(max_length=80)
    billing_cycle = models.CharField(max_length=10, choices=CYCLES, default=MONTHLY)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["billing_cycle", "price"]

    def __str__(self):
        return f"{self.name} · {self.get_billing_cycle_display()} · {settings.CURRENCY}{self.price:g}"

    def add_cycle(self, start, count=1):
        delta = relativedelta(months=count) if self.billing_cycle == self.MONTHLY else relativedelta(years=count)
        return start + delta


class Member(models.Model):
    GENDERS = [("M", "Male"), ("F", "Female"), ("O", "Other")]
    STATUSES = [("active", "Active"), ("paused", "Paused"), ("left", "Left")]

    member_id = models.CharField(max_length=12, unique=True, blank=True, editable=False)
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="member_profile")
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, help_text="WhatsApp / SMS number, e.g. 9876543210")
    email = models.EmailField(blank=True)
    gender = models.CharField(max_length=1, choices=GENDERS, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    photo = models.ImageField(upload_to="members/", null=True, blank=True)
    plan = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.PROTECT, related_name="members")
    join_date = models.DateField(default=today)
    next_due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default="active")
    qr_token = models.CharField(max_length=32, unique=True, default=new_token, editable=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.member_id})"

    def save(self, *args, **kwargs):
        if self._state.adding and not self.next_due_date:
            self.next_due_date = self.join_date  # first fee is due on the joining day
        super().save(*args, **kwargs)
        if not self.member_id:
            self.member_id = f"GR{self.pk:04d}"
            Member.objects.filter(pk=self.pk).update(member_id=self.member_id)

    # -------- fee state helpers
    @property
    def days_left(self):
        return None if not self.next_due_date else (self.next_due_date - today()).days

    @property
    def fee_state(self):
        if self.status != "active":
            return "inactive"
        d = self.days_left
        if d is None:
            return "unpaid"
        if d < 0:
            return "overdue"
        if d <= settings.REMINDER_DAYS_BEFORE:
            return "due_soon"
        return "paid"

    @property
    def fee_label(self):
        return {
            "inactive": self.get_status_display(),
            "unpaid": "No fee set",
            "overdue": f"Overdue {abs(self.days_left)}d" if self.days_left is not None else "Overdue",
            "due_soon": "Due today" if self.days_left == 0 else f"Due in {self.days_left}d",
            "paid": "Paid up",
        }[self.fee_state]

    @property
    def fee_class(self):
        return {"inactive": "muted", "unpaid": "muted", "overdue": "danger",
                "due_soon": "warn", "paid": "ok"}[self.fee_state]

    @property
    def initials(self):
        parts = self.name.split()
        return "".join(p[0] for p in parts[:2]).upper() or "?"


class Payment(models.Model):
    METHODS = [("cash", "Cash"), ("upi", "UPI"), ("card", "Card"), ("bank", "Bank transfer")]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="payments")
    receipt_no = models.CharField(max_length=24, unique=True, null=True, blank=True, editable=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    periods = models.PositiveSmallIntegerField(default=1, help_text="How many months / years this payment covers")
    method = models.CharField(max_length=10, choices=METHODS, default="cash")
    paid_on = models.DateField(default=today)
    period_start = models.DateField(editable=False, null=True)
    period_end = models.DateField(editable=False, null=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_on", "-id"]

    def __str__(self):
        return f"{self.receipt_no or 'new'} · {self.member.name} · {self.amount}"

    def save(self, *args, **kwargs):
        creating = self._state.adding
        member = self.member
        if creating:
            # Renewing early extends from the current due date; paying late starts today.
            start = member.next_due_date if (member.next_due_date and member.next_due_date >= self.paid_on) else self.paid_on
            self.period_start = start
            if member.plan:
                self.period_end = member.plan.add_cycle(start, self.periods)
            else:
                self.period_end = start + relativedelta(months=self.periods)
        super().save(*args, **kwargs)
        if creating:
            self.receipt_no = f"GR-{self.paid_on:%y%m%d}-{self.pk:04d}"
            Payment.objects.filter(pk=self.pk).update(receipt_no=self.receipt_no)
            member.next_due_date = self.period_end
            member.save(update_fields=["next_due_date"])


class Attendance(models.Model):
    METHODS = [("qr", "QR scan"), ("manual", "Front desk")]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField(default=today)
    check_in = models.DateTimeField(default=timezone.now)
    method = models.CharField(max_length=10, choices=METHODS, default="qr")

    class Meta:
        ordering = ["-check_in"]
        constraints = [models.UniqueConstraint(fields=["member", "date"], name="one_checkin_per_day")]

    def __str__(self):
        return f"{self.member.name} · {self.date}"


class ReminderLog(models.Model):
    CHANNELS = [("sms", "SMS"), ("whatsapp", "WhatsApp"), ("console", "Console")]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="reminders")
    channel = models.CharField(max_length=10, choices=CHANNELS)
    message = models.TextField()
    success = models.BooleanField(default=False)
    error = models.CharField(max_length=300, blank=True)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.member.name} · {self.channel} · {'ok' if self.success else 'failed'}"
