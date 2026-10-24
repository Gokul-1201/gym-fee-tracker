import os
import sys

from django.apps import AppConfig

_SKIP_COMMANDS = {
    "makemigrations", "migrate", "collectstatic", "shell", "test",
    "createsuperuser", "send_reminders", "seed_demo", "check",
}


class GymConfig(AppConfig):
    name = "gym"
    verbose_name = "Gym fee tracker"

    def ready(self):
        # Optional in-process scheduler: set RUN_SCHEDULER=1 to send reminders daily.
        if os.environ.get("RUN_SCHEDULER") != "1":
            return
        if _SKIP_COMMANDS.intersection(sys.argv):
            return
        if "runserver" in sys.argv and "--noreload" not in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return  # let only the reloaded child process start the scheduler
        from .scheduler import start
        start()
