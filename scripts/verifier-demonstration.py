#!/usr/bin/env python3
"""Aller-retour privé du jeu métier via les commandes de copie existantes."""
from contextlib import closing
import json
import os
import queue
import signal
import threading
import time
import urllib.request
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def ouvrir_programme(env, habituel, essai):
    """Vrai serveur du lanceur ; aucun moteur graphique ni port fixe."""
    args = [sys.executable, str(ROOT/'scripts/lancer-local.py'), '--paquet', str(habituel), '--sans-fenetre']
    if essai:
        args.append('--essai')
    p = subprocess.Popen(args, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    lignes, recus = [], queue.Queue()
    def lire():
        for ligne in p.stdout:
            recus.put(ligne)
    threading.Thread(target=lire, daemon=True).start()
    try:
        limite = time.monotonic() + 120
        while time.monotonic() < limite:
            try:
                ligne = recus.get(timeout=.25)
            except queue.Empty:
                if p.poll() is not None:
                    raise AssertionError('Lanceur arrêté avant ouverture : ' + ''.join(lignes))
                continue
            lignes.append(ligne)
            if ligne.startswith('Adresse locale : '):
                adresse = ligne.split(' : ', 1)[1].strip()
                with urllib.request.urlopen(adresse+'connexion/', timeout=10) as r:
                    connexion = r.read().decode()
                assert ('Espace d’essai Établissement Les Passerelles' in connexion) == essai
                with urllib.request.urlopen(adresse+'essai-local/', timeout=10) as r:
                    selection = r.read().decode()
                assert ('data-espace="habituel"' if essai else 'data-espace="essai"') in selection
                return
        raise AssertionError('Ouverture locale non confirmée : ' + ''.join(lignes))
    finally:
        if p.poll() is None:
            if os.name == 'nt':
                p.terminate()
            else:
                p.send_signal(signal.SIGINT)
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill(); p.wait(timeout=5)
        p.stdout.close()


def verifier_commande_fenetre(env, habituel, depuis_essai=False, restauration=False):
    # Seul le moteur graphique est simulé ; le vrai lanceur, HTTP et fermeture
    # sont exercés. Ne pas remplacer un espace pour tester le bouton.
    code = """
import importlib.util,sys,types
from unittest.mock import patch
from pathlib import Path
spec=importlib.util.spec_from_file_location('lanceur',Path('scripts/lancer-local.py'))
lanceur=importlib.util.module_from_spec(spec);spec.loader.exec_module(lanceur)
habituel=sys.argv[1];depuis_essai=sys.argv[2]=='oui';restaurer=sys.argv[3]=='oui'
# Le chemin vient de l’environnement ; le redémarrage doit le rendre explicite.
sys.argv=['scripts/lancer-local.py']+(['--essai'] if depuis_essai else [])
class Fenetre:
    detruite=False
    def destroy(self):self.detruite=True
fenetre=Fenetre();api=None;redemarrages=[]
def creer(*args,commandes):
    global api
    api=commandes
    return fenetre
def demarrer():
    from pas_a_pas_accompagnement.paquets import restauration
    origine=list(sys.argv)
    assert not api.changer_espace('chemin-arbitraire')
    for methode in ('preparation','attente'):
        with patch.object(restauration,methode,return_value=object()):
            assert not api.changer_espace('habituel' if depuis_essai else 'essai')
        assert sys.argv==origine and not fenetre.detruite
    if restaurer:
        with patch.object(restauration,'attente',return_value=object()):
            assert api.appliquer_et_redemarrer()
    else:
        assert api.changer_espace('habituel' if depuis_essai else 'essai')
    assert fenetre.detruite
with patch.dict(sys.modules,{'webview':types.SimpleNamespace(start=demarrer)}), \
     patch.object(lanceur.bureau,'creer_fenetre',creer), \
     patch.object(lanceur.os,'execv',lambda executable,arguments:redemarrages.append(arguments)):
    lanceur.main()
assert len(redemarrages)==1
args=redemarrages[0]
assert ('--essai' in args)==(depuis_essai if restaurer else not depuis_essai)
assert args[args.index('--paquet')+1]==habituel
"""
    subprocess.check_call([sys.executable, '-c', code, str(habituel), 'oui' if depuis_essai else 'non', 'oui' if restauration else 'non'],
                          cwd=ROOT, env=env)


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
        # Le premier patch a pu remplir l’espace habituel : il doit rester intact.
        env_local = {**env, 'XDG_DATA_HOME': str(racine/'xdg'), 'LOCALAPPDATA': str(racine/'windows')}
        ouvrir_programme(env_local, source, True)
        from pas_communs.local import paquet_par_defaut
        essai = paquet_par_defaut('pas-a-pas-accompagnement', environnement=env_local).parent/'essai-fictif'
        import sqlite3
        with closing(sqlite3.connect(essai/'accompagnement.sqlite3')) as db, db:
            assert db.execute('SELECT count(*) FROM personnes_personne').fetchone()[0] == 36
            assert db.execute('SELECT count(*) FROM identites_utilisateur').fetchone()[0] == 4
            db.execute("UPDATE personnes_personne SET designation='Essai conservé' WHERE designation='Alex (fictif)'")
        ouvrir_programme(env_local, source, False)
        ouvrir_programme(env_local, source, True)
        with closing(sqlite3.connect(essai/'accompagnement.sqlite3')) as db, db:
            assert db.execute("SELECT count(*) FROM personnes_personne WHERE designation='Essai conservé'").fetchone()[0] == 1
        verifier_commande_fenetre(env_local, source)
        verifier_commande_fenetre(env_local, source, True)
        verifier_commande_fenetre(env_local, source, True, restauration=True)
        assert signature(source) == avant, 'L’espace habituel a été modifié par l’essai'
        print('Programme : essai distinct, retour personnalisé, réouverture, commandes de fenêtre et blocages de restauration : OK')
        print('Établissement Les Passerelles : copie, vérification, restauration, relations et reconnexion : OK')


if __name__ == '__main__':
    verifier()
