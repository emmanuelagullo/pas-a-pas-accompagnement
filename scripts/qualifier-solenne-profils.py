#!/usr/bin/env python3
"""Vraies vues Django des trois profils, sans simuler une fenêtre ou Pyodide.

Exige les dépendances serveur/PDF et pwa/requirements-pdf.txt existantes ;
aucun paquet n'est installé ici.
Les bases et comptes fictifs sont créés uniquement dans des dossiers temporaires.
"""
import os
import argparse
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile

RACINE = Path(__file__).resolve().parent.parent
VERIFIER = r'''
import os
import django
django.setup()
from datetime import date
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from personnes import bd6, famille, coordonnees, ouverture_prise, contacts_menage, partenaires, intervenants, interventions, complements_identite, relations_personnelles
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
contacts_menage.designer(u, a.menage, p, date(2026, 1, 1), 'Choix fictif', bd6.jeton(a.menage))
organisme = partenaires.creer(u, date(2026, 1, 1), 'Source fictive', partenaires.jeton_creation(),
    nom='Organisme fictif de qualification', rue='', code_postal='', ville='Ville partenaire fictive', pays='',
    telephone='', courriel='', fax='', informations='')
professionnel = intervenants.creer(u, date(2026, 1, 1), 'Source fictive', intervenants.jeton_creation(),
    nom='Professionnel fictif de qualification', fonction='Travail social', organisme=organisme,
    telephone='', courriel='professionnel@example.invalid', fax='')
interventions.affecter(u, a, date(2026, 1, 1), None, 'referent', professionnel, None,
    'Décision fictive', bd6.jeton(a))
complements_identite.renseigner(u,p,date(2026,1,1),'Source fictive',bd6.jeton(p),
    sexe_declare='',naissance_lieu='',naissance_ville='Ville natale fictive',naissance_pays='Pays fictif',
    nationalites=['Nationalité fictive A','Nationalité fictive B'],apatridie_declaree=None)
proche=Personne.objects.create(designation='Proche fictif de qualification',cree_par=u)
relations_personnelles.enregistrer(u,p,proche,date(2026,1,1),None,'proche','','Source fictive',bd6.jeton(p))
client = Client(HTTP_HOST=settings.ALLOWED_HOSTS[0])
client.force_login(u, backend='django.contrib.auth.backends.ModelBackend')
prefixe = settings.FORCE_SCRIPT_NAME or ''
def chemin(route, *args):
    url = reverse(route, args=args)
    return url[len(prefixe):] if prefixe and url.startswith(prefixe) else url
for route, args, texte in [
    ('dossiers:prise', ['personne', p.pk, a.pk], 'Ville fictive'),
    ('dossiers:famille', [p.pk], 'Célibataire'),
    ('dossiers:contact_menage', [a.menage_id], 'Personne fictive de qualification'),
    ('dossiers:intervenants', [], 'Professionnel fictif de qualification'),
    ('dossiers:intervenant', [professionnel.pk], 'Travail social'),
    ('dossiers:complements_identite', [p.pk], 'Ville natale fictive'),
    ('dossiers:relations_personnelles', [p.pk], 'Proche fictif de qualification'),
    ('dossiers:rapport_complements_identite', [], 'Nationalité fictive B'),
    ('dossiers:rapport_relations', [], 'Proche fictif de qualification'),
    ('dossiers:interventions', [a.pk], 'Professionnel fictif de qualification'),
    ('dossiers:partenaires', [], 'Organisme fictif de qualification'),
    ('dossiers:partenaire', [organisme.pk], 'Ville partenaire fictive'),
    ('dossiers:coordonnees', [p.pk], '00100'),
    ('dossiers:rapport_familles', [], 'Célibataire'),
    ('dossiers:rapport_coordonnees', [], 'Ville fictive')]:
    response = client.get(chemin(route, *args), secure=True)
    assert response.status_code == 200, (route, response.status_code)
    assert texte in response.content.decode(), route
if os.environ.get('SOLENNE_VERIFIER_PDF') == 'oui':
    response = client.get(chemin('personnes:fiche_pdf', p.pk), secure=True)
    assert response.status_code == 200 and response.content.startswith(b'%PDF-')
    assert 'no-store' in response['Cache-Control']
bd6.corriger_prevision(u, a, None, 'Retrait fictif', bd6.jeton(a))
a.refresh_from_db()
assert a.fin is None and a.fin_prevue is None
print(settings.SETTINGS_MODULE + ' : ouverture, lectures BD, rapports et correction : OK ; PDF : ' + ('OK' if os.environ.get('SOLENNE_VERIFIER_PDF') == 'oui' else 'NON TESTÉ (--sans-pdf)'))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sans-pdf', action='store_true', help='Valider les parcours HTML sans qualifier les moteurs PDF.')
    args = parser.parse_args()
    if not args.sans_pdf:
        absents = [nom for nom in ('weasyprint', 'fpdf') if importlib.util.find_spec(nom) is None]
        if absents:
            parser.error('Dépendances PDF absentes : ' + ', '.join(absents) + '. '
                'Installer les dépendances existantes de requirements-pdf.txt et pwa/requirements-pdf.txt '
                '(fpdf est fourni par fpdf2), ou relancer explicitement avec --sans-pdf. '
                'Aucune base de qualification créée.')
    for profil in ('pas_a_pas_accompagnement.settings_local',
                   'pas_a_pas_accompagnement.settings_serveur', 'pwa.settings'):
        with tempfile.TemporaryDirectory(prefix='solenne-profils-fictifs-') as temporaire:
            env = {k: v for k, v in os.environ.items() if not k.startswith(('ACCOMPAGNEMENT_', 'PWA_'))
                   and k not in {'DJANGO_SETTINGS_MODULE', 'DATABASE_URL'}}
            env.update(SOLENNE_VERIFIER_PDF='non' if args.sans_pdf else 'oui', DJANGO_SETTINGS_MODULE=profil, ACCOMPAGNEMENT_DONNEES=temporaire,
                ACCOMPAGNEMENT_2FA='desactive', ACCOMPAGNEMENT_HOSTS='qualification.fictive.example',
                ACCOMPAGNEMENT_CSRF_ORIGINS='https://qualification.fictive.example',
                PWA_HOST='qualification.fictive.example', PWA_ORIGIN='https://qualification.fictive.example',
                PWA_BASE_PATH='/qualification/')
            subprocess.run([sys.executable, '-c', VERIFIER], cwd=RACINE, env=env, check=True)


if __name__ == '__main__':
    main()
