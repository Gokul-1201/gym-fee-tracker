from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Attendance, Member, Payment, Plan


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs.setdefault("class", "form-select")
            elif isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "form-check-input")
            elif isinstance(w, forms.FileInput):
                w.attrs.setdefault("class", "form-control")
            else:
                w.attrs.setdefault("class", "form-control")


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        kwargs.setdefault("format", "%Y-%m-%d")
        super().__init__(**kwargs)


class MemberForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Member
        fields = ["name", "phone", "email", "gender", "date_of_birth", "address", "photo",
                  "plan", "join_date", "next_due_date", "status", "notes"]
        widgets = {
            "date_of_birth": DateInput(),
            "join_date": DateInput(),
            "next_due_date": DateInput(),
            "address": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }
        help_texts = {"next_due_date": "Leave empty for new members — the first fee is due on the joining date."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plan"].queryset = Plan.objects.filter(is_active=True)
        self.fields["next_due_date"].required = False


class PaymentForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["member", "periods", "amount", "method", "paid_on", "note"]
        widgets = {"paid_on": DateInput(), "note": forms.TextInput(attrs={"placeholder": "Optional"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["member"].queryset = Member.objects.exclude(status="left").order_by("name")
        self.fields["periods"].min_value = 1

    def clean_periods(self):
        value = self.cleaned_data["periods"]
        if value < 1:
            raise forms.ValidationError("Enter at least 1.")
        return value


class ManualAttendanceForm(BootstrapMixin, forms.Form):
    member = forms.ModelChoiceField(queryset=Member.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["member"].queryset = Member.objects.filter(status="active").order_by("name")


class PlanForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Plan
        fields = ["name", "billing_cycle", "price", "description", "is_active"]


class RegisterForm(BootstrapMixin, UserCreationForm):
    email = forms.EmailField(required=False)
    signup_code = forms.CharField(label="Signup code", required=False, widget=forms.PasswordInput)

    class Meta:
        model = get_user_model()
        fields = ("username", "email")
