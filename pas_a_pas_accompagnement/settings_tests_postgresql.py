"""Qualification jetable uniquement ; aucun profil de déploiement."""
import os
import re
from django.core.exceptions import ImproperlyConfigured

if os.environ.get('ACCOMPAGNEMENT_PG_QUALIFICATION') != 'oui':
    raise ImproperlyConfigured('Profil PostgreSQL réservé à la qualification explicite.')
_nom = os.environ.get('PGDATABASE', '')
if not re.fullmatch(r'pas_ci_[a-f0-9]{12}', _nom):
    raise ImproperlyConfigured('La qualification exige une base jetable pas_ci_<12 hex>.')
for _cle in ('PGHOST', 'PGPORT', 'PGUSER', 'PGPASSWORD'):
    if not os.environ.get(_cle):
        raise ImproperlyConfigured(f'{_cle} doit être explicite pour la qualification.')

from .settings import *  # noqa: F403
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql', 'NAME': _nom,
    'HOST': os.environ['PGHOST'], 'PORT': os.environ['PGPORT'],
    'USER': os.environ['PGUSER'], 'PASSWORD': os.environ['PGPASSWORD'],
    'CONN_MAX_AGE': 0, 'OPTIONS': {'connect_timeout': 10},
    'TEST': {'NAME': 'test_' + _nom},
}}
