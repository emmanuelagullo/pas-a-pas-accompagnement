"""Démonstration publique jetable ; aucune donnée réelle ni ressource persistante."""
import os
from django.core.exceptions import ImproperlyConfigured

if os.environ.get('ACCOMPAGNEMENT_DEMONSTRATION') != 'oui':
    raise ImproperlyConfigured('La démonstration exige un démarrage jetable explicite.')
if os.environ.get('DATABASE_URL') or os.environ.get('ACCOMPAGNEMENT_2FA', 'desactive') != 'desactive':
    raise ImproperlyConfigured('Démonstration : ni base distante ni second facteur persistant.')
from .settings_serveur import *  # noqa: E402,F403
DEMONSTRATION_PUBLIQUE = True
TEMPLATES = [{**TEMPLATES[0], 'OPTIONS': {**TEMPLATES[0]['OPTIONS'],
    'context_processors': [*TEMPLATES[0]['OPTIONS']['context_processors'],
        'pas_a_pas_accompagnement.demo.contexte']}}]
MIDDLEWARE = [*MIDDLEWARE, 'pas_a_pas_accompagnement.demo.ProtegerComptePublic']
