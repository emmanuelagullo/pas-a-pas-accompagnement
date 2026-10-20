"""Profil du programme local #SOC3, distinct du serveur de développement."""
from .settings import *  # noqa: F403

MODE_LOCAL = True
DEBUG = False
STATIC_URL = "/static/"
STATIC_ROOT = LOCAL_DIR / "staticfiles"
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

OUTILS_COPIES_BUREAU = True
