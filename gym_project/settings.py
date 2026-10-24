"""Settings for the gokulRaj Gym fee tracker."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me-gokulraj-gym")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "gym.apps.GymConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "gym_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "gym.context_processors.branding",
            ],
        },
    },
]

WSGI_APPLICATION = "gym_project.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "gym:dashboard"
LOGOUT_REDIRECT_URL = "login"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

# ---------------------------------------------------------------- Branding
GYM_NAME = os.environ.get("GYM_NAME", "Gym tracker")
# Code new staff must enter on the Create account page (after the first account exists). CHANGE THIS.
STAFF_SIGNUP_CODE = os.environ.get("STAFF_SIGNUP_CODE", "gokul-gym-2026")
GYM_TAGLINE = os.environ.get("GYM_TAGLINE", "Fitness & Fees, tracked.")
CURRENCY = "₹"

# ------------------------------------------------------- Fees & reminders
REMINDER_DAYS_BEFORE = int(os.environ.get("REMINDER_DAYS_BEFORE", "3"))
REMINDER_COOLDOWN_DAYS = int(os.environ.get("REMINDER_COOLDOWN_DAYS", "2"))
REMINDER_HOUR = int(os.environ.get("REMINDER_HOUR", "9"))      # daily run, local time
ALLOW_OVERDUE_CHECKIN = True                                   # warn, but don't block

# console = just print to the terminal (safe for development)
# Real sending: set to "sms", "whatsapp" or "sms,whatsapp" and fill Twilio keys.
NOTIFY_CHANNELS = [c.strip() for c in os.environ.get("NOTIFY_CHANNELS", "console").split(",") if c.strip()]
DEFAULT_COUNTRY_CODE = os.environ.get("DEFAULT_COUNTRY_CODE", "+91")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_SMS_FROM = os.environ.get("TWILIO_SMS_FROM", "")                 # e.g. +1415XXXXXXX
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "")       # e.g. whatsapp:+14155238886

# ---------------------------------------------------------------- Production
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
CSRF_TRUSTED_ORIGINS = ["https://*.onrender.com"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
if os.environ.get("DATABASE_URL"):
    import dj_database_url
    DATABASES["default"] = dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=600)