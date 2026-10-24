import csv
import json
from datetime import datetime, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.crypto import constant_time_compare, get_random_string
from django.views.decorators.http import require_POST

from .forms import ManualAttendanceForm, MemberForm, PaymentForm, PlanForm, RegisterForm
from .models import Attendance, Member, Payment, Plan, ReminderLog
from .services.checkin import check_in
from .services.qr import make_qr_png
from .services.reminders import members_needing_reminder, run_reminders, send_reminder_for

User = get_user_model()


def staff_required(view):
    return user_passes_test(lambda u: u.is_active and u.is_staff, login_url=settings.LOGIN_URL)(view)


def register(request):
    """Create a staff account in the browser. First account becomes the owner (superuser)."""
    first_user = not User.objects.filter(is_superuser=True).exists()
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data.get("signup_code", "")
        if not first_user and not constant_time_compare(code, settings.STAFF_SIGNUP_CODE):
            form.add_error("signup_code", "Wrong signup code. Ask the gym owner for it.")
        else:
            user = form.save(commit=False)
            user.is_staff = True
            user.is_superuser = first_user
            user.save()
            login(request, user)
            messages.success(request, f"Account created. Welcome, {user.username}!")
            return redirect("gym:dashboard")
    return render(request, "gym/register.html", {"form": form, "first_user": first_user})


def month_start(d):
    return d.replace(day=1)


# ------------------------------------------------------------------ Dashboard
@staff_required
def dashboard(request):
    today = timezone.localdate()
    active = Member.objects.filter(status="active")
    overdue_qs = active.filter(next_due_date__lt=today)

    stats = {
        "members": Member.objects.count(),
        "active": active.count(),
        "collected": Payment.objects.filter(paid_on__gte=month_start(today)).aggregate(s=Sum("amount"))["s"] or 0,
        "overdue": overdue_qs.count(),
        "pending": overdue_qs.aggregate(s=Sum("plan__price"))["s"] or 0,
        "today_checkins": Attendance.objects.filter(date=today).count(),
    }

    revenue = []
    for i in range(5, -1, -1):
        start = month_start(today) - relativedelta(months=i)
        end = start + relativedelta(months=1)
        total = Payment.objects.filter(paid_on__gte=start, paid_on__lt=end).aggregate(s=Sum("amount"))["s"] or 0
        revenue.append({"label": start.strftime("%b"), "value": float(total)})

    attendance = []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        attendance.append({"label": day.strftime("%d %b"), "value": Attendance.objects.filter(date=day).count()})

    ctx = {
        "stats": stats,
        "charts": {"revenue": revenue, "attendance": attendance},
        "due_soon": active.filter(next_due_date__gte=today,
                                  next_due_date__lte=today + timedelta(days=settings.REMINDER_DAYS_BEFORE)
                                  ).select_related("plan").order_by("next_due_date")[:6],
        "overdue_list": overdue_qs.select_related("plan").order_by("next_due_date")[:6],
        "recent_payments": Payment.objects.select_related("member")[:6],
        "todays_checkins": Attendance.objects.filter(date=today).select_related("member")[:8],
    }
    return render(request, "gym/dashboard.html", ctx)


# -------------------------------------------------------------------- Members
@staff_required
def member_list(request):
    today = timezone.localdate()
    q = request.GET.get("q", "").strip()
    state = request.GET.get("state", "")
    qs = Member.objects.select_related("plan")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q) | Q(member_id__icontains=q))
    if state == "overdue":
        qs = qs.filter(status="active", next_due_date__lt=today)
    elif state == "due_soon":
        qs = qs.filter(status="active", next_due_date__gte=today,
                       next_due_date__lte=today + timedelta(days=settings.REMINDER_DAYS_BEFORE))
    elif state == "paid":
        qs = qs.filter(status="active", next_due_date__gt=today + timedelta(days=settings.REMINDER_DAYS_BEFORE))
    elif state in ("paused", "left", "active"):
        qs = qs.filter(status=state)
    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    return render(request, "gym/member_list.html", {"page": page, "q": q, "state": state})


@staff_required
def member_form(request, pk=None):
    member = get_object_or_404(Member, pk=pk) if pk else None
    form = MemberForm(request.POST or None, request.FILES or None, instance=member)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, f"{saved.name} saved.")
        return redirect("gym:member_detail", pk=saved.pk)
    return render(request, "gym/member_form.html", {"form": form, "member": member})


@staff_required
def member_detail(request, pk):
    member = get_object_or_404(Member.objects.select_related("plan", "user"), pk=pk)
    today = timezone.localdate()
    ctx = {
        "member": member,
        "payments": member.payments.all()[:12],
        "attendance": member.attendance.all()[:15],
        "visits_this_month": member.attendance.filter(date__gte=month_start(today)).count(),
        "total_paid": member.payments.aggregate(s=Sum("amount"))["s"] or 0,
    }
    return render(request, "gym/member_detail.html", ctx)


@staff_required
def member_delete(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        name = member.name
        member.delete()
        messages.success(request, f"{name} was deleted.")
        return redirect("gym:member_list")
    return render(request, "gym/member_confirm_delete.html", {"member": member})


@staff_required
def member_qr(request, pk):
    member = get_object_or_404(Member, pk=pk)
    return HttpResponse(make_qr_png(member.qr_token), content_type="image/png")


@staff_required
def member_card(request, pk):
    return render(request, "gym/member_card.html", {"member": get_object_or_404(Member, pk=pk)})


@staff_required
@require_POST
def member_app_login(request, pk):
    """Create (or reset) the mobile-app login for a member."""
    member = get_object_or_404(Member, pk=pk)
    password = get_random_string(8, "abcdefghjkmnpqrstuvwxyz23456789")
    if member.user:
        member.user.set_password(password)
        member.user.save()
    else:
        user = User.objects.create_user(username=member.member_id.lower(), password=password,
                                        first_name=member.name.split()[0])
        member.user = user
        member.save(update_fields=["user"])
    messages.success(request, f"App login for {member.name} — username: {member.user.username} · password: {password} "
                              "(shown once, share it with the member).")
    return redirect("gym:member_detail", pk=pk)


# ------------------------------------------------------------------- Payments
@staff_required
def payment_list(request):
    q = request.GET.get("q", "").strip()
    month = request.GET.get("month", "")
    qs = Payment.objects.select_related("member")
    if q:
        qs = qs.filter(Q(member__name__icontains=q) | Q(receipt_no__icontains=q))
    if month:
        try:
            y, m = map(int, month.split("-"))
            qs = qs.filter(paid_on__year=y, paid_on__month=m)
        except ValueError:
            pass
    total = qs.aggregate(s=Sum("amount"))["s"] or 0
    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    return render(request, "gym/payment_list.html", {"page": page, "q": q, "month": month, "total": total})


@staff_required
def payment_create(request):
    initial = {}
    if request.GET.get("member"):
        initial["member"] = request.GET["member"]
        m = Member.objects.filter(pk=request.GET["member"]).select_related("plan").first()
        if m and m.plan:
            initial["amount"] = m.plan.price
    form = PaymentForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        payment = form.save()
        messages.success(request, f"Payment recorded — receipt {payment.receipt_no}. "
                                  f"{payment.member.name} is covered until {payment.period_end:%d %b %Y}.")
        return redirect("gym:receipt", pk=payment.pk)
    prices = {str(m.pk): float(m.plan.price) for m in Member.objects.select_related("plan") if m.plan}
    return render(request, "gym/payment_form.html", {"form": form, "plan_prices": prices})


@staff_required
def receipt(request, pk):
    return render(request, "gym/receipt.html", {"payment": get_object_or_404(Payment.objects.select_related("member", "member__plan"), pk=pk)})


@staff_required
def plan_list(request):
    plan = get_object_or_404(Plan, pk=request.GET["edit"]) if request.GET.get("edit") else None
    form = PlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Plan saved.")
        return redirect("gym:plan_list")
    plans = Plan.objects.annotate(member_count=Count("members"))
    return render(request, "gym/plan_list.html", {"plans": plans, "form": form, "editing": plan})


# ----------------------------------------------------------------------- Dues
@staff_required
def dues(request):
    today = timezone.localdate()
    active = Member.objects.filter(status="active").select_related("plan")
    ctx = {
        "overdue": active.filter(next_due_date__lt=today).order_by("next_due_date"),
        "due_soon": active.filter(next_due_date__gte=today,
                                  next_due_date__lte=today + timedelta(days=settings.REMINDER_DAYS_BEFORE)).order_by("next_due_date"),
        "channels": ", ".join(settings.NOTIFY_CHANNELS),
    }
    return render(request, "gym/dues.html", ctx)


@staff_required
@require_POST
def send_reminder(request, pk):
    member = get_object_or_404(Member, pk=pk)
    sent = send_reminder_for(member, force=True)
    if sent:
        messages.success(request, f"Reminder sent to {member.name}.")
    else:
        messages.error(request, f"Could not send to {member.name}. Check the reminder log for the reason.")
    return redirect(request.POST.get("next") or "gym:dues")


@staff_required
@require_POST
def send_all_reminders(request):
    contacted, sent = run_reminders(force=request.POST.get("force") == "1")
    messages.success(request, f"Reminded {contacted} member(s) — {sent} message(s) sent.")
    return redirect("gym:reminder_log")


@staff_required
def reminder_log(request):
    page = Paginator(ReminderLog.objects.select_related("member"), 20).get_page(request.GET.get("page"))
    return render(request, "gym/reminder_log.html", {
        "page": page, "channels": ", ".join(settings.NOTIFY_CHANNELS),
        "pending_count": members_needing_reminder().count(),
    })


# ----------------------------------------------------------------- Attendance
@staff_required
def attendance_list(request):
    today = timezone.localdate()
    try:
        day = datetime.strptime(request.GET.get("date", ""), "%Y-%m-%d").date()
    except ValueError:
        day = today
    form = ManualAttendanceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ok, level, msg = check_in(form.cleaned_data["member"], method="manual")
        getattr(messages, "success" if level == "success" else "warning" if level == "warning" else "error")(request, msg)
        return redirect("gym:attendance")
    records = Attendance.objects.filter(date=day).select_related("member")
    return render(request, "gym/attendance_list.html", {"records": records, "day": day, "form": form})


@staff_required
def attendance_scan(request):
    if request.method == "POST":
        try:
            token = json.loads(request.body or "{}").get("token", "").strip()
        except json.JSONDecodeError:
            token = ""
        member = Member.objects.filter(qr_token=token).select_related("plan").first()
        if not member:
            return JsonResponse({"ok": False, "level": "error", "message": "QR code not recognised."}, status=404)
        ok, level, msg = check_in(member, method="qr")
        return JsonResponse({"ok": ok, "level": level, "message": msg, "name": member.name,
                             "member_id": member.member_id, "fee": member.fee_label})
    return render(request, "gym/scan.html")


# -------------------------------------------------------------------- Reports
@staff_required
def reports(request):
    today = timezone.localdate()
    try:
        y, m = map(int, request.GET.get("month", "").split("-"))
        start = today.replace(year=y, month=m, day=1)
    except ValueError:
        start = month_start(today)
    end = start + relativedelta(months=1)

    pays = Payment.objects.filter(paid_on__gte=start, paid_on__lt=end)
    by_method = list(pays.values("method").annotate(total=Sum("amount"), n=Count("id")).order_by("-total"))
    method_names = dict(Payment.METHODS)
    for row in by_method:
        row["label"] = method_names.get(row["method"], row["method"])

    days_in_month = (end - start).days
    daily_att = []
    for i in range(days_in_month):
        d = start + timedelta(days=i)
        daily_att.append({"label": d.strftime("%d"), "value": Attendance.objects.filter(date=d).count()})

    year_rev = []
    for i in range(11, -1, -1):
        s = month_start(today) - relativedelta(months=i)
        total = Payment.objects.filter(paid_on__gte=s, paid_on__lt=s + relativedelta(months=1)).aggregate(t=Sum("amount"))["t"] or 0
        year_rev.append({"label": s.strftime("%b %y"), "value": float(total)})

    top = (Attendance.objects.filter(date__gte=start, date__lt=end).values("member__name", "member__member_id")
           .annotate(visits=Count("id")).order_by("-visits")[:8])
    plan_mix = list(Member.objects.filter(status="active").values("plan__name").annotate(n=Count("id")).order_by("-n"))

    ctx = {
        "start": start, "month_value": start.strftime("%Y-%m"),
        "revenue": pays.aggregate(s=Sum("amount"))["s"] or 0,
        "payment_count": pays.count(),
        "new_members": Member.objects.filter(join_date__gte=start, join_date__lt=end).count(),
        "visits": Attendance.objects.filter(date__gte=start, date__lt=end).count(),
        "by_method": by_method, "top": top, "plan_mix": plan_mix,
        "charts": {"year_rev": year_rev, "daily_att": daily_att},
    }
    return render(request, "gym/reports.html", ctx)


@staff_required
def export_payments_csv(request):
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="payments.csv"'
    w = csv.writer(resp)
    w.writerow(["Receipt", "Member ID", "Member", "Amount", "Method", "Paid on", "Covers from", "Covers until", "Note"])
    for p in Payment.objects.select_related("member"):
        w.writerow([p.receipt_no, p.member.member_id, p.member.name, p.amount, p.get_method_display(),
                    p.paid_on, p.period_start, p.period_end, p.note])
    return resp


@staff_required
def export_members_csv(request):
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="members.csv"'
    w = csv.writer(resp)
    w.writerow(["Member ID", "Name", "Phone", "Email", "Plan", "Joined", "Next due", "Status", "Fee state"])
    for m in Member.objects.select_related("plan"):
        w.writerow([m.member_id, m.name, m.phone, m.email, m.plan.name if m.plan else "", m.join_date,
                    m.next_due_date, m.get_status_display(), m.fee_label])
    return resp
