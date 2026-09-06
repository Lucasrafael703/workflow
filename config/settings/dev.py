from .base import *  # noqa: F401,F403
from .base import BASE_DIR, env

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Prints e-mails to the console instead of requiring real SMTP during local
# development -- still django.core.mail, just a different backend.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
