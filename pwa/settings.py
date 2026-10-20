from pas_a_pas_accompagnement.settings import *  # noqa: F403

MODE_LOCAL = True
MODE_PWA = True
DEBUG = False
PWA_BASE_PATH = os.environ.get("PWA_BASE_PATH", "/")
FORCE_SCRIPT_NAME = PWA_BASE_PATH.rstrip("/") + "/app"
STATIC_URL = PWA_BASE_PATH + "static/"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_SAVE_EVERY_REQUEST = False
X_FRAME_OPTIONS = "SAMEORIGIN"
ALLOWED_HOSTS = [os.environ["PWA_HOST"]]
CSRF_TRUSTED_ORIGINS = [os.environ["PWA_ORIGIN"]]
DATABASES["default"]["OPTIONS"] = {"init_command":"PRAGMA journal_mode=DELETE"}

ESPACE_ESSAI = os.environ.get("ACCOMPAGNEMENT_ESPACE_ESSAI") == "oui"
MIDDLEWARE.append("pas_a_pas_accompagnement.demo.ProtegerComptePublic")
