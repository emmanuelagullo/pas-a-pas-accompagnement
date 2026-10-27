"""Profil #SOC1 : développement local, exclusivement sur données fictives."""
from pathlib import Path
import secrets
import os

BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_DIR = Path(os.environ.get("ACCOMPAGNEMENT_DONNEES", BASE_DIR / ".local")).expanduser().resolve()
LOCAL_DIR.mkdir(mode=0o700, exist_ok=True)
_cle = LOCAL_DIR / "secret-key"
try:
    with _cle.open("x", encoding="utf-8") as fichier:
        _cle.chmod(0o600)
        fichier.write(secrets.token_urlsafe(64))
except FileExistsError:
    pass
SECRET_KEY = _cle.read_text(encoding="utf-8").strip()
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "identites", "personnes", "acteurs",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "identites.middleware.DoubleFacteurMiddleware",
    "acteurs.middleware.PerimetreMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "pas_a_pas_accompagnement.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "pas_a_pas_accompagnement.version.contexte",
        "acteurs.context_processors.acteurs",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "pas_a_pas_accompagnement.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": LOCAL_DIR / "accompagnement.sqlite3"}}
AUTH_USER_MODEL = "identites.Utilisateur"
AUTHENTICATION_BACKENDS = [
    "acteurs.backend.HabilitationsBackend",
    "pas_communs.authentification.mots_de_passe.PlafondMotDePasse",
    "django.contrib.auth.backends.ModelBackend",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "pas_communs.authentification.mots_de_passe.MaximumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "connexion"
LOGIN_REDIRECT_URL = "accueil"
LOGOUT_REDIRECT_URL = "connexion"
SESSION_COOKIE_AGE = 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

MEDIA_ROOT = LOCAL_DIR / "media"

MODE_LOCAL = False

# Identités de cookies propres au produit, y compris avec runserver.
SESSION_COOKIE_NAME = "pas_accompagnement_sessionid"
CSRF_COOKIE_NAME = "pas_accompagnement_csrftoken"

# #SOC4b : politique technique d’un seul espace fictif, sans rôle social.
from identites.configuration import lire as _lire_double_facteur
DOUBLE_FACTEUR_POLITIQUE, DOUBLE_FACTEUR_CLES = _lire_double_facteur(os.environ)
DOUBLE_FACTEUR_EMETTEUR = "Pas à Pas — Accompagnement"
AUTH_FENETRE_SECONDES = 15 * 60
AUTH_TENTATIVES_COMPTE = 5
AUTH_TENTATIVES_IP = 30

LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "handlers": {"securite_console": {"class": "logging.StreamHandler"}},
    "loggers": {"identites.securite": {
        "handlers": ["securite_console"], "level": "INFO", "propagate": False,
    }},
}

DEFAULT_EXCEPTION_REPORTER_FILTER = "identites.diagnostics.FiltreSecurite"

from .version import version_application as _version_application
VERSION_APPLICATION = _version_application()
