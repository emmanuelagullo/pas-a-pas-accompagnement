"""Démonstration publique jetable ; aucune donnée réelle ni ressource persistante."""
import os
from django.core.exceptions import ImproperlyConfigured

if os.environ.get('ACCOMPAGNEMENT_DEMONSTRATION') != 'oui':
    raise ImproperlyConfigured('La démonstration exige un démarrage jetable explicite.')
if os.environ.get('DATABASE_URL') or os.environ.get('ACCOMPAGNEMENT_2FA', 'desactive') != 'desactive':
    raise ImproperlyConfigured('Démonstration : ni base distante ni second facteur persistant.')
# Le serveur public conserve le contrat HTTPS strict. Le serveur de captures
# utilise un profil HTTP distinct, uniquement sur l'interface de bouclage.
if os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
    from .settings_serveur import *  # noqa: E402,F403
else:
    _hotes = [h.strip() for h in os.environ.get('ACCOMPAGNEMENT_HOSTS', '').split(',') if h.strip()]
    _bouclage = {'127.0.0.1', 'localhost', '[::1]', '::1'}
    if (not _hotes or not set(_hotes) <= _bouclage
            or os.environ.get('ACCOMPAGNEMENT_BIND', '') not in ('127.0.0.1', '::1')
            or os.environ.get('ACCOMPAGNEMENT_CSRF_ORIGINS')
            or os.environ.get('ACCOMPAGNEMENT_PROXY_HTTPS', 'non') != 'non'):
        raise ImproperlyConfigured('Démonstration HTTP réservée au bouclage local explicite.')
    from .settings import *  # noqa: E402,F403
    from pathlib import Path
    DEBUG = False
    ALLOWED_HOSTS = _hotes
    STATIC_ROOT = Path(LOCAL_DIR) / 'staticfiles'
    STATIC_URL = '/static/'
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
    }
    MIDDLEWARE = [*MIDDLEWARE]
    MIDDLEWARE.insert(MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1,
                      'whitenoise.middleware.WhiteNoiseMiddleware')
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

DEMONSTRATION_PUBLIQUE = True
TEMPLATES = [{**TEMPLATES[0], 'OPTIONS': {**TEMPLATES[0]['OPTIONS'],
    'context_processors': [*TEMPLATES[0]['OPTIONS']['context_processors'],
        'pas_a_pas_accompagnement.demo.contexte']}}]
MIDDLEWARE = [*MIDDLEWARE, 'pas_a_pas_accompagnement.demo.ProtegerComptePublic']
