#!/usr/bin/env python3
"""Aller-retour privé du jeu métier via les commandes de copie existantes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def verifier():
    with tempfile.TemporaryDirectory(prefix='demonstration-chrs-fictive-') as temporaire:
        racine = Path(temporaire)
        source, cible = racine/'source', racine/'restauree'
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('ACCOMPAGNEMENT_', 'CARNET_')) and k != 'DATABASE_URL'}
        env.update(DJANGO_SETTINGS_MODULE='pas_a_pas_accompagnement.settings',
                   ACCOMPAGNEMENT_DONNEES=str(source))
        def commande(*args, dossier=source):
            return subprocess.check_output([sys.executable, str(ROOT/'manage.py'), *args],
                cwd=ROOT, env={**env, 'ACCOMPAGNEMENT_DONNEES': str(dossier)}, text=True)
        commande('migrate', '--noinput')
        commande('shell', '-c', "from django.contrib.auth import get_user_model; "
                 "from personnes.demonstration import generer; "
                 "generer(get_user_model().objects.create_user('visiteur-prive',password='Phrase-fictive-privee-2026!')); "
                 "from django.contrib.sessions.models import Session; from django.utils import timezone; "
                 "Session.objects.create(session_key='session-fictive',session_data='fictif',expire_date=timezone.now())")
        def signature(dossier):
            return json.loads(commande('dumpdata', 'personnes', 'identites.Utilisateur', dossier=dossier))
        avant = signature(source)
        copie = racine/'copie-privee.zip'
        commande('sauvegarder_paquet', str(copie))
        commande('verifier_sauvegarde', str(copie))
        commande('restaurer_copie', str(copie), str(cible))
        commande('migrate', '--noinput', dossier=cible)
        assert signature(cible) == avant, 'Objets, identités, droits ou relations modifiés'
        assert signature(source) == avant, 'Source modifiée'
        assert (source/'secret-key').read_bytes() == (cible/'secret-key').read_bytes()
        verification = "from django.contrib.sessions.models import Session; assert not Session.objects.exists(); " \
            "from django.test import Client; c=Client(HTTP_HOST='localhost'); assert c.get('/menages/').status_code==302; " \
            "assert c.login(username='visiteur-prive',password='Phrase-fictive-privee-2026!'); " \
            "assert c.get('/decouverte/').status_code==200"
        commande('shell', '-c', verification, dossier=cible)
        commande('shell', '-c', "from django.contrib.sessions.models import Session; assert Session.objects.filter(session_key='session-fictive').exists()")
        print('Les Passerelles : copie, vérification, restauration, relations et reconnexion : OK')


if __name__ == '__main__':
    verifier()
