"""Profil réseau HTTPS fictif ; aucun changement du profil local par défaut."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

# Exiger un emplacement volontaire avant toute création de clé ou de base.
_chemin = os.environ.get("ACCOMPAGNEMENT_DONNEES", "")
if not _chemin or not Path(_chemin).is_absolute():
    raise ImproperlyConfigured("Définir ACCOMPAGNEMENT_DONNEES vers un dossier persistant absolu.")
from .settings import *  # noqa: F403, E402
from pas_communs.serveur import configuration_https  # noqa: E402

try:
    globals().update(configuration_https(
        cle=SECRET_KEY, hotes=os.environ.get("ACCOMPAGNEMENT_HOSTS", ""),
        origines=os.environ.get("ACCOMPAGNEMENT_CSRF_ORIGINS", ""),
        proxy_https=os.environ.get("ACCOMPAGNEMENT_PROXY_HTTPS", "non"),
        hsts=os.environ.get("ACCOMPAGNEMENT_HSTS_SECONDES", "3600")))
except ValueError as erreur:
    raise ImproperlyConfigured(str(erreur)) from None

# La clé stable reste LOCAL_DIR/secret-key : même contrat que les copies SOC2.
MODE_LOCAL = False
STATIC_ROOT = Path(os.environ.get("ACCOMPAGNEMENT_STATIC_ROOT", LOCAL_DIR / "staticfiles"))
STATIC_URL = "/static/"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MIDDLEWARE = [*MIDDLEWARE]
MIDDLEWARE.insert(MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware")
