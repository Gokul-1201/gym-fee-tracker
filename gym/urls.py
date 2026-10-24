from django.urls import path

from . import views

app_name = "gym"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("", views.dashboard, name="dashboard"),
    path("members/", views.member_list, name="member_list"),
    path("members/new/", views.member_form, name="member_create"),
    path("members/<int:pk>/", views.member_detail, name="member_detail"),
    path("members/<int:pk>/edit/", views.member_form, name="member_edit"),
    path("members/<int:pk>/delete/", views.member_delete, name="member_delete"),
    path("members/<int:pk>/qr.png", views.member_qr, name="member_qr"),
    path("members/<int:pk>/card/", views.member_card, name="member_card"),
    path("members/<int:pk>/app-login/", views.member_app_login, name="member_app_login"),
    path("payments/", views.payment_list, name="payment_list"),
    path("payments/new/", views.payment_create, name="payment_create"),
    path("payments/<int:pk>/receipt/", views.receipt, name="receipt"),
    path("plans/", views.plan_list, name="plan_list"),
    path("dues/", views.dues, name="dues"),
    path("dues/remind/<int:pk>/", views.send_reminder, name="send_reminder"),
    path("dues/remind-all/", views.send_all_reminders, name="send_all_reminders"),
    path("reminders/", views.reminder_log, name="reminder_log"),
    path("attendance/", views.attendance_list, name="attendance"),
    path("attendance/scan/", views.attendance_scan, name="scan"),
    path("reports/", views.reports, name="reports"),
    path("export/payments.csv", views.export_payments_csv, name="export_payments"),
    path("export/members.csv", views.export_members_csv, name="export_members"),
]
