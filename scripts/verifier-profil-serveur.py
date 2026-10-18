#!/usr/bin/env python3
"""Banc WSGI Django du profil HTTPS, sans serveur exposé ni données réelles."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent
VERIFICATION=r"""
import django
from django.conf import settings
from django.test import Client
django.setup()
client=Client(enforce_csrf_checks=True,HTTP_HOST='serveur.fictif.example')
assert not settings.DEBUG
assert settings.MODE_LOCAL is False
assert settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE
assert client.get('/health/').status_code==301
assert client.get('/health/',HTTP_X_FORWARDED_PROTO='https').status_code==301
reponse=client.get('/health/',secure=True)
assert reponse.status_code==200 and reponse.json()['status']=='ok'
assert client.get('/static/application.css',secure=True).status_code==200
assert reponse['X-Frame-Options']=='DENY'
assert reponse['Strict-Transport-Security']=='max-age=3600'
assert client.get('/health/',secure=True,HTTP_HOST='etranger.fictif.example').status_code==400
assert client.post('/connexion/',{'username':'fictif'},secure=True).status_code==403
reponse=client.get('/connexion/',secure=True)
assert reponse.status_code==200
assert reponse.cookies[settings.CSRF_COOKIE_NAME]['secure']
assert client.get('/installer/',secure=True).status_code==404
# Le déployeur doit avoir protégé le backend avant d'activer cette confiance.
settings.SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
assert client.get('/health/',HTTP_X_FORWARDED_PROTO='https').status_code==200
assert settings.USE_X_FORWARDED_HOST is False
print('WSGI HTTPS : redirection, hôte, cookies, CSRF et confiance proxy explicite : OK')
"""

with tempfile.TemporaryDirectory(prefix='serveur-fictif-') as temp:
    racine=Path(temp)
    env={k:v for k,v in os.environ.items() if not k.startswith(('CARNET_', 'ACCOMPAGNEMENT_'))
        and k not in {'DATABASE_URL', 'DJANGO_SETTINGS_MODULE'}}
    env['DJANGO_SETTINGS_MODULE']='pas_a_pas_accompagnement.settings_serveur'
    env.update(ACCOMPAGNEMENT_DONNEES=str(racine/'donnees'),ACCOMPAGNEMENT_HOSTS='serveur.fictif.example',
        ACCOMPAGNEMENT_CSRF_ORIGINS='https://serveur.fictif.example')
    env['ACCOMPAGNEMENT_PROXY_HTTPS']='non'
    def lancer(*args,attendu=0):
        resultat=subprocess.run([sys.executable,*args],cwd=ROOT,env=env,capture_output=True,text=True)
        if attendu==0 and resultat.returncode:
            sys.stderr.write(resultat.stdout+resultat.stderr)
            raise SystemExit('Échec du banc serveur fictif.')
        if attendu!=0 and not resultat.returncode:
            raise AssertionError('Configuration invalide acceptée.')
        return resultat
    lancer('manage.py','migrate','--noinput')
    lancer('manage.py','collectstatic','--noinput')
    controle=lancer('manage.py','check','--deploy','--fail-level','ERROR')
    sys.stdout.write(controle.stdout);sys.stderr.write(controle.stderr)
    resultat=lancer('-c',VERIFICATION);print(resultat.stdout.strip())
    env['ACCOMPAGNEMENT_HOSTS']='*'
    echec=lancer('manage.py','check',attendu=1)
    assert 'joker' in echec.stderr
    env['ACCOMPAGNEMENT_HOSTS']='serveur.fictif.example'
    env['ACCOMPAGNEMENT_CSRF_ORIGINS']='http://serveur.fictif.example'
    echec=lancer('manage.py','check',attendu=1)
    assert 'origines CSRF' in echec.stderr
    print('Configuration ambiguë refusée avant ouverture du service : OK')

    del env['ACCOMPAGNEMENT_DONNEES']
    echec=lancer('manage.py','check',attendu=1)
    assert 'dossier persistant absolu' in echec.stderr
