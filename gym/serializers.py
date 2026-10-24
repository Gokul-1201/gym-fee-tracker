from rest_framework import serializers

from .models import Attendance, Member, Payment


class MemberSerializer(serializers.ModelSerializer):
    plan = serializers.CharField(source="plan.name", default=None, read_only=True)
    plan_price = serializers.DecimalField(source="plan.price", max_digits=10, decimal_places=2, default=None, read_only=True)
    billing_cycle = serializers.CharField(source="plan.billing_cycle", default=None, read_only=True)
    fee_state = serializers.CharField(read_only=True)
    fee_label = serializers.CharField(read_only=True)
    days_left = serializers.IntegerField(read_only=True)

    class Meta:
        model = Member
        fields = ["id", "member_id", "name", "phone", "email", "plan", "plan_price", "billing_cycle",
                  "join_date", "next_due_date", "days_left", "fee_state", "fee_label", "status"]


class PaymentSerializer(serializers.ModelSerializer):
    method = serializers.CharField(source="get_method_display")

    class Meta:
        model = Payment
        fields = ["receipt_no", "amount", "method", "paid_on", "period_start", "period_end", "note"]


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["date", "check_in", "method"]
