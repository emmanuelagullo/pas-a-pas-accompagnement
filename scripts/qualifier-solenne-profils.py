#!/usr/bin/env python3
"""Vraies vues Django des trois profils, sans simuler une fenêtre ou Pyodide.

Exige les dépendances serveur/PDF et pwa/requirements-pdf.txt existantes ;
aucun paquet n'est installé ici.
Les bases et comptes fictifs sont créés uniquement dans des dossiers temporaires.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

RACINE = Path(__file__).resolve().parent.parent
VERIFIER = r'''
import django
django.setup()
from datetime import date
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from personnes import bd6, famille, coordonnees, ouverture_prise
from personnes.models import Personne

call_command('migrate', interactive=False, verbosity=0)
if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
    call_command('collectstatic', interactive=False, verbosity=0)
u = get_user_model().objects.create_user('qualification-solenne-fictive')
call_command('autoriser_chrs7', u.username, verbosity=0)
call_command('autoriser_solenne', u.username, verbosity=0)
u = get_user_model().objects.get(pk=u.pk)
p = Personne.objects.create(designation='Personne fictive de qualification', cree_par=u)
a = ouverture_prise.ouvrir(u, p, [p], date(2026, 1, 1), date(2026, 6, 1), ouverture_prise.jeton(p),
    creer_menage=True, libelle_menage='Ménage fictif de qualification')
famille.renseigner(u, p, date(2026, 1, 1), 'Entretien fictif', bd6.jeton(p),
    situation_familiale='Célibataire', rapports_parentaux='', fratrie='',
    enfants_a_charge=0, enfants_non_a_charge=None, grossesse=None)
coordonnees.renseigner(u, p, date(2026, 1, 1), 'Entretien fictif', bd6.jeton(p),
    rue='Rue fictive', code_postal='00100', ville='Ville fictive', pays='Pays fictif',
    telephone='', courriel='personne@example.invalid', fax='')
client = Client(HTTP_HOST=settings.ALLOWED_HOSTS[0])
client.force_login(u, backend='django.contrib.auth.backends.ModelBackend')
prefixe = settings.FORCE_SCRIPT_NAME or ''
def chemin(route, *args):
    url = reverse(route, args=args)
    return url[len(prefixe):] if prefixe and url.startswith(prefixe) else url
for route, args, texte in [
    ('dossiers:prise', ['personne', p.pk, a.pk], 'Ville fictive'),
    ('dossiers:famille', [p.pk], 'Célibataire'),
    ('dossiers:coordonnees', [p.pk], '00100'),
    ('dossiers:rapport_familles', [], 'Célibataire'),
    ('dossiers:rapport_coordonnees', [], 'Ville fictive')]:
    response = client.get(chemin(route, *args), secure=True)
    assert response.status_code == 200, (route, response.status_code)
    assert texte in response.content.decode(), route
response = client.get(chemin('personnes:fiche_pdf', p.pk), secure=True)
assert response.status_code == 200 and response.content.startswith(b'%PDF-')
assert 'no-store' in response['Cache-Control']
bd6.corriger_prevision(u, a, None, 'Retrait fictif', bd6.jeton(a))
a.refresh_from_db()
assert a.fin is None and a.fin_prevue is None
print(settings.SETTINGS_MODULE + ' : ouverture, lectures BD, rapports, PDF et correction : OK')
'''


def main():
    for profil in ('pas_a_pas_accompagnement.settings_local',
                   'pas_a_pas_accompagnement.settings_serveur', 'pwa.settings'):
        with tempfile.TemporaryDirectory(prefix='solenne-profils-fictifs-') as temporaire:
            env = {k: v for k, v in os.environ.items() if not k.startswith(('ACCOMPAGNEMENT_', 'PWA_'))
                   and k not in {'DJANGO_SETTINGS_MODULE', 'DATABASE_URL'}}
            env.update(DJANGO_SETTINGS_MODULE=profil, ACCOMPAGNEMENT_DONNEES=temporaire,
                ACCOMPAGNEMENT_2FA='desactive', ACCOMPAGNEMENT_HOSTS='qualification.fictive.example',
                ACCOMPAGNEMENT_CSRF_ORIGINS='https://qualification.fictive.example',
                PWA_HOST='qualification.fictive.example', PWA_ORIGIN='https://qualification.fictive.example',
                PWA_BASE_PATH='/qualification/')
            subprocess.run([sys.executable, '-c', VERIFIER], cwd=RACINE, env=env, check=True)


if __name__ == '__main__':
    main()
