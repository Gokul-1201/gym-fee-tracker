import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from gym.models import Attendance, Member, Payment, Plan

NAMES = ["Arun Kumar", "Priya Lakshmi", "Karthik Raja", "Divya Bharathi", "Suresh Babu", "Meena Devi",
         "Vignesh S", "Anitha R", "Harish Chandran", "Nandhini K", "Prakash M", "Swetha Rani",
         "Dinesh Kumar", "Kavya Sri", "Manoj Pandian", "Ramya J"]


class Command(BaseCommand):
    help = "Create demo plans, members, payments and attendance so the dashboard has data."

    def handle(self, *args, **opts):
        random.seed(7)
        today = timezone.localdate()
        monthly, _ = Plan.objects.get_or_create(name="Standard", billing_cycle="monthly", defaults={"price": Decimal("1000")})
        premium, _ = Plan.objects.get_or_create(name="Premium + Cardio", billing_cycle="monthly", defaults={"price": Decimal("1500")})
        annual, _ = Plan.objects.get_or_create(name="Annual Saver", billing_cycle="annual", defaults={"price": Decimal("10000")})
        if Member.objects.exists():
            self.stdout.write("Members already exist - skipping demo data.")
            return
        for i, name in enumerate(NAMES):
            plan = random.choice([monthly, monthly, premium, annual])
            join = today - timedelta(days=random.randint(20, 220))
            m = Member.objects.create(name=name, phone=f"90000000{i:02d}", plan=plan, join_date=join,
                                      gender=random.choice(["M", "F"]))
            # monthly payers pay each month since joining; leave some lapsed on purpose
            cursor = join
            skip_last = random.random() < 0.3
            while cursor <= today:
                if skip_last and (cursor + timedelta(days=35)) > today:
                    break
                p = Payment(member=m, amount=plan.price, method=random.choice(["cash", "upi", "upi", "card"]), paid_on=cursor)
                p.save()
                cursor = p.period_end
                if plan.billing_cycle == "annual":
                    break
            for d in range(30):
                day = today - timedelta(days=d)
                if random.random() < 0.45 and day >= join:
                    Attendance.objects.get_or_create(
                        member=m, date=day,
                        defaults={"check_in": timezone.now() - timedelta(days=d), "method": random.choice(["qr", "qr", "manual"])})
        self.stdout.write(self.style.SUCCESS(f"Created {len(NAMES)} demo members with payments and attendance."))
