from django.contrib import admin

from .models import Attendance, Member, Payment, Plan, ReminderLog


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "billing_cycle", "price", "is_active")


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("member_id", "name", "phone", "plan", "next_due_date", "status")
    list_filter = ("status", "plan")
    search_fields = ("name", "phone", "member_id")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("receipt_no", "member", "amount", "method", "paid_on", "period_end")
    list_filter = ("method", "paid_on")
    search_fields = ("member__name", "receipt_no")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("member", "date", "check_in", "method")
    list_filter = ("method", "date")


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    list_display = ("member", "channel", "success", "sent_at")
    list_filter = ("channel", "success")
