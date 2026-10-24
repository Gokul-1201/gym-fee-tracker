"""REST API for the mobile app (members) and for staff apps / kiosks."""
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Member, Payment
from .serializers import AttendanceSerializer, MemberSerializer, PaymentSerializer
from .services.checkin import check_in
from .services.qr import make_qr_png


def current_member(request) -> Member:
    try:
        return request.user.member_profile
    except Member.DoesNotExist:
        raise Http404("This account is not linked to a gym member.")


class MeView(APIView):
    """GET /api/me/ — the signed-in member's profile and fee status."""
    def get(self, request):
        return Response(MemberSerializer(current_member(request)).data)


class MyPaymentsView(APIView):
    def get(self, request):
        qs = current_member(request).payments.all()
        return Response(PaymentSerializer(qs, many=True).data)


class MyAttendanceView(APIView):
    def get(self, request):
        qs = current_member(request).attendance.all()[:60]
        return Response(AttendanceSerializer(qs, many=True).data)


class MyQRView(APIView):
    """GET /api/me/qr/ — PNG of the member's check-in QR code (show it at the gate)."""
    def get(self, request):
        return HttpResponse(make_qr_png(current_member(request).qr_token), content_type="image/png")


class CheckInView(APIView):
    """POST /api/checkin/ {"token": "..."} — staff only (gate tablet / staff app)."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        token = str(request.data.get("token", "")).strip()
        member = Member.objects.filter(qr_token=token).first()
        if not member:
            return Response({"ok": False, "level": "error", "message": "QR code not recognised."}, status=404)
        ok, level, message = check_in(member, method="qr")
        return Response({"ok": ok, "level": level, "message": message, "member": MemberSerializer(member).data})


class MemberListView(APIView):
    """GET /api/members/?q=name&state=overdue — staff only."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = Member.objects.select_related("plan")
        q = request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q) | Q(member_id__icontains=q))
        if request.query_params.get("state") == "overdue":
            qs = qs.filter(status="active", next_due_date__lt=timezone.localdate())
        return Response(MemberSerializer(qs[:200], many=True).data)


class SummaryView(APIView):
    """GET /api/summary/ — quick dashboard numbers for a staff app."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        today = timezone.localdate()
        active = Member.objects.filter(status="active")
        overdue = active.filter(next_due_date__lt=today)
        return Response({
            "active_members": active.count(),
            "overdue_members": overdue.count(),
            "pending_amount": overdue.aggregate(s=Sum("plan__price"))["s"] or 0,
            "collected_this_month": Payment.objects.filter(paid_on__gte=today.replace(day=1)).aggregate(s=Sum("amount"))["s"] or 0,
        })
