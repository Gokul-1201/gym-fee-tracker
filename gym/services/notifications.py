"""SMS / WhatsApp delivery through Twilio, with a console fallback for development."""
import logging
import re

from django.conf import settings

log = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """'98765 43210' -> '+919876543210' (uses DEFAULT_COUNTRY_CODE when none is given)."""
    phone = re.sub(r"[^\d+]", "", phone or "")
    if phone.startswith("+"):
        return phone
    phone = phone.lstrip("0")
    return f"{settings.DEFAULT_COUNTRY_CODE}{phone}"


def send_message(phone: str, text: str, channel: str):
    """Returns (ok: bool, error: str)."""
    to = normalize_phone(phone)

    if channel == "console":
        print(f"[console notification] to {to}: {text}")
        return True, ""

    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN):
        return False, "Twilio credentials are not configured."
    try:
        from twilio.rest import Client
    except ImportError:
        return False, "twilio package is not installed (pip install twilio)."

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        if channel == "whatsapp":
            if not settings.TWILIO_WHATSAPP_FROM:
                return False, "TWILIO_WHATSAPP_FROM is not set."
            client.messages.create(body=text, from_=settings.TWILIO_WHATSAPP_FROM, to=f"whatsapp:{to}")
        elif channel == "sms":
            if not settings.TWILIO_SMS_FROM:
                return False, "TWILIO_SMS_FROM is not set."
            client.messages.create(body=text, from_=settings.TWILIO_SMS_FROM, to=to)
        else:
            return False, f"Unknown channel '{channel}'."
        return True, ""
    except Exception as exc:  # network, auth, invalid number...
        log.exception("Notification failed")
        return False, str(exc)[:290]
