from django.conf import settings
from django.utils import timezone


def branding(request):
    return {
        "GYM_NAME": settings.GYM_NAME,
        "GYM_TAGLINE": settings.GYM_TAGLINE,
        "CURRENCY": settings.CURRENCY,
        "TODAY": timezone.localdate(),
    }
