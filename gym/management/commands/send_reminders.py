from django.core.management.base import BaseCommand

from gym.services.reminders import run_reminders


class Command(BaseCommand):
    help = "Send WhatsApp/SMS reminders to members whose fee is due soon or overdue."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Ignore the cooldown between reminders")

    def handle(self, *args, **opts):
        contacted, messages = run_reminders(force=opts["force"])
        self.stdout.write(self.style.SUCCESS(f"Reminded {contacted} member(s), {messages} message(s) sent."))
