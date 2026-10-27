#!/usr/bin/env python3
"""Vues et PDF avec contrôle actif dans les trois configurations Django.

Ne simule ni Pyodide/OPFS ni une fenêtre bureau. Bases et comptes fictifs
uniquement, dans des dossiers temporaires ; aucune dépendance installée ici.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

RACINE=Path(__file__).resolve().parent.parent
VERIFIER=r'''
import django;django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from acteurs.essai import preparer
from acteurs.models import DossierService,Habilitation,Service
from acteurs import services as s
call_command('migrate',interactive=False,verbosity=0)
if getattr(settings,'STATIC_ROOT',None):call_command('collectstatic',interactive=False,verbosity=0)
u=get_user_model().objects.create_user('social-fictif-profils')
c=get_user_model().objects.create_user('coordination-fictive-profils')
service=preparer(u,coordination=c)
prefixe=settings.FORCE_SCRIPT_NAME or ''
def chemin(route,*args):
    url=reverse(route,args=args)
    return url[len(prefixe):] if prefixe and url.startswith(prefixe) else url
client=Client(HTTP_HOST=settings.ALLOWED_HOSTS[0]);client.force_login(u,backend='django.contrib.auth.backends.ModelBackend')
r=client.get(chemin('accueil'),secure=True);assert r.status_code==200
assert 'Dossier réservé à un autre service' not in r.content.decode()
ds=DossierService.objects.get(menage__libelle='Essai — Mon dossier en cours')
with CaptureQueriesContext(connection) as requetes:
    r=client.get(chemin('dossiers:detail','menage',ds.menage_id),secure=True)
assert r.status_code==200 and 'Qui s’en occupe' in r.content.decode()
print(settings.SETTINGS_MODULE+' : dossier, '+str(len(requetes))+' requêtes SQL',flush=True)
pdf=client.get(chemin('personnes:fiche_pdf',ds.menage.appartenances.first().personne_id),secure=True)
assert pdf.status_code==200 and pdf.content.startswith(b'%PDF-'),pdf.status_code
Habilitation.objects.filter(compte=u).update(exporter=False)
assert client.get(chemin('personnes:fiche_pdf',ds.menage.appartenances.first().personne_id),secure=True).status_code==403
client.force_login(c,backend='django.contrib.auth.backends.ModelBackend')
params={'rapport':'synthese','portee_statistiques':'service'}
r=client.get(chemin('statistiques'),params,secure=True);assert r.status_code==200
assert client.get(chemin('dossiers:detail','menage',ds.menage_id),secure=True).status_code==403
assert client.get(chemin('statistiques'),{**params,'format':'csv'},secure=True).status_code==403
Habilitation.objects.filter(compte=c).update(exporter=True)
r=client.get(chemin('statistiques'),{**params,'format':'csv'},secure=True)
assert r.status_code==200 and b'Mon dossier' not in r.content
h=Habilitation.objects.get(compte=c);s.revoquer(u,h,s.jeton(h))
assert client.get(chemin('statistiques'),params,secure=True).status_code==403
print(settings.SETTINGS_MODULE+' : accès directs, statistiques/justificatifs séparés, PDF réel, exports et révocation : OK',flush=True)
'''


def main():
    for profil in ('pas_a_pas_accompagnement.settings_local','pas_a_pas_accompagnement.settings_serveur','pwa.settings'):
        with tempfile.TemporaryDirectory(prefix='acteurs-profils-fictifs-') as temporaire:
            env={k:v for k,v in os.environ.items() if not k.startswith(('ACCOMPAGNEMENT_','PWA_')) and k not in {'DJANGO_SETTINGS_MODULE','DATABASE_URL'}}
            env.update(DJANGO_SETTINGS_MODULE=profil,ACCOMPAGNEMENT_DONNEES=temporaire,ACCOMPAGNEMENT_2FA='desactive',
                ACCOMPAGNEMENT_HOSTS='qualification.fictive.example',ACCOMPAGNEMENT_CSRF_ORIGINS='https://qualification.fictive.example',
                PWA_HOST='qualification.fictive.example',PWA_ORIGIN='https://qualification.fictive.example',PWA_BASE_PATH='/qualification/')
            subprocess.run([sys.executable,'-c',VERIFIER],cwd=RACINE,env=env,check=True)


if __name__=='__main__':main()
