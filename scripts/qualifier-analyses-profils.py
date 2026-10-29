#!/usr/bin/env python3
"""Vues Django et exports réels des trois profils, sous préfixe et droits actifs.

Ce banc ne lance ni Pyodide/OPFS ni les fenêtres natives Windows/Linux.
"""
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

RACINE=Path(__file__).resolve().parent.parent
BASE=runpy.run_path(str(RACINE/'scripts/qualifier-acteurs-profils.py'))['VERIFIER']
AJOUT=r'''
from personnes import analyses,assemblages
from django.contrib.auth.models import Permission
# Droits de conservation explicitement attribués au seul compte fictif du banc.
u.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes',codename__in=['view_modelerapport','add_modelerapport']))
import json
analyse=analyses.defaut();analyse.update(filtre='mes',mesures=[dict(source='personnes',mesure='personnes')])
payload=dict(definition=analyses.encoder(analyse))
r=client.get(chemin('dossiers:analyse'),payload,secure=True)
assert r.status_code==200,(r.status_code,__import__('re').findall(r'<p role="alert">(.*?)</p>',r.content.decode()))
assert 'Dossier réservé à un autre service' not in r.content.decode()
for format in ('csv','pdf'):
    x=client.post(chemin('dossiers:analyse'),{**payload,'format':format},secure=True)
    assert x.status_code==200,x.content[:500]
    if format=='pdf':assert x.content.startswith(b'%PDF-')
compose=assemblages.defaut();compose['parties']=[dict(titre='Mes dossiers',description='',source='analyse',parametres=analyses.parametres(analyse),modele=None,empreinte='',periode_commune=False)]
payload=dict(definition=analyses.encoder(compose))
r=client.get(chemin('dossiers:assemblage'),payload,secure=True);assert r.status_code==200,(r.status_code,__import__('re').findall(r'<p role="alert">(.*?)</p>',r.content.decode()))
for format in ('csv','pdf'):
    x=client.post(chemin('dossiers:assemblage'),{**payload,'format':format},secure=True)
    assert x.status_code==200,x.content[:500]
    if format=='pdf':assert x.content.startswith(b'%PDF-')
print(settings.SETTINGS_MODULE+' : analyses indépendantes et assemblage, HTML/CSV/PDF, préfixe et droits actifs : OK',flush=True)
'''
VERIFIER=BASE.replace("Habilitation.objects.filter(compte=u).update(exporter=False)",AJOUT+"\nHabilitation.objects.filter(compte=u).update(exporter=False)",1)


def main():
    for profil in ('pas_a_pas_accompagnement.settings_local','pas_a_pas_accompagnement.settings_serveur','pwa.settings'):
        with tempfile.TemporaryDirectory(prefix='analyses-profils-fictifs-') as temporaire:
            env={k:v for k,v in os.environ.items() if not k.startswith(('ACCOMPAGNEMENT_','PWA_')) and k not in {'DJANGO_SETTINGS_MODULE','DATABASE_URL'}}
            env.update(DJANGO_SETTINGS_MODULE=profil,ACCOMPAGNEMENT_DONNEES=temporaire,ACCOMPAGNEMENT_2FA='desactive',
                ACCOMPAGNEMENT_HOSTS='qualification.fictive.example',ACCOMPAGNEMENT_CSRF_ORIGINS='https://qualification.fictive.example',
                PWA_HOST='qualification.fictive.example',PWA_ORIGIN='https://qualification.fictive.example',PWA_BASE_PATH='/qualification/')
            subprocess.run([sys.executable,'-c',VERIFIER],cwd=RACINE,env=env,check=True)


if __name__=='__main__':main()
