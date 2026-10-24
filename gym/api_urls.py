from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from . import api_views as v

urlpatterns = [
    path("auth/token/", obtain_auth_token, name="api_token"),
    path("me/", v.MeView.as_view()),
    path("me/payments/", v.MyPaymentsView.as_view()),
    path("me/attendance/", v.MyAttendanceView.as_view()),
    path("me/qr/", v.MyQRView.as_view()),
    path("checkin/", v.CheckInView.as_view()),
    path("members/", v.MemberListView.as_view()),
    path("summary/", v.SummaryView.as_view()),
]
