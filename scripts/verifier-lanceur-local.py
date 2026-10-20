"""Parcours HTTP réel, sans ouvrir de fenêtre et sans données utilisateur."""
from pathlib import Path
import http.cookiejar
import os
import re
import signal
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

import argparse
import sys
source=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description='Vérifier le lanceur sur des données fictives isolées.')
parser.add_argument('--programme',type=Path,help='exécutable Linux à vérifier au lieu des sources')
args=parser.parse_args()
if args.programme and os.name=='nt':
    parser.error('La fenêtre native Windows nécessite un essai graphique distinct.')
prefixe=[str(args.programme.resolve())] if args.programme else [sys.executable,str(source/'scripts/lancer-local.py')]
with tempfile.TemporaryDirectory() as t:
    t=Path(t); paquet=t/'paquet'; log=t/'sortie.log'
    env={**os.environ,'PYTHONUNBUFFERED':'1','PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1'}
    def start():
        sortie=log.open('w',encoding='utf-8')
        p=subprocess.Popen([*prefixe,'--paquet',str(paquet),'--sans-fenetre'],cwd=source,env=env,stdout=sortie,stderr=subprocess.STDOUT)
        for _ in range(200):
            texte=log.read_text(encoding='utf-8')
            match=re.search(r'Adresse locale : (http://127\.0\.0\.1:\d+/)',texte)
            if match:
                return p,sortie,match[1]
            if p.poll() is not None:
                raise RuntimeError(texte)
            time.sleep(.05)
        p.terminate();p.wait();raise RuntimeError('Démarrage expiré : '+log.read_text(encoding='utf-8'))
    def stop(p,sortie):
        if p.poll() is None:
            if os.name=='nt':
                p.terminate()
            else:
                p.send_signal(signal.SIGINT)
        try:
            p.wait(timeout=10)
        finally:
            if p.poll() is None:
                p.kill();p.wait()
            sortie.close()
        if os.name!='nt':
            assert p.returncode==0,log.read_text(encoding='utf-8')
    cookies=http.cookiejar.CookieJar()
    client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
    def post(base,path,data):
        token=next(c.value for c in cookies if c.name=='pas_accompagnement_csrftoken')
        return client.open(base+path,urllib.parse.urlencode({**data,'csrfmiddlewaretoken':token}).encode(),timeout=5)
    p,sortie,base=start()
    try:
        first=client.open(base).read().decode()
        assert 'Préparer mon espace' in first
        with post(base,'installer/',{'username':'fictif-soc3','password1':'mot-de-passe-fictif-2026!','password2':'mot-de-passe-fictif-2026!'}) as response:
            assert '/personnes/' in response.url
        client.open(base+'personnes/creer/').read()
        with post(base,'personnes/creer/',{'designation':'Identité fictive SOC3'}) as response:
            assert 'Identité fictive SOC3' in response.read().decode()
        with client.open(base+'mon-compte/securite/',timeout=5) as r:
            assert 'Le second facteur n’est pas activé' in r.read().decode()
        with client.open(base+'mon-compte/mot-de-passe/',timeout=5) as r:
            assert 'Changer mon mot de passe' in r.read().decode()
        second=subprocess.run([*prefixe,'--paquet',str(paquet),'--sans-fenetre'],cwd=source,env=env,capture_output=True,text=True,encoding='utf-8',timeout=5)
        assert second.returncode!=0 and 'déjà ouvert' in second.stderr, (
            second.returncode, second.stdout, second.stderr
        )
        cle=(paquet/'secret-key').read_text()
    finally:
        stop(p,sortie)
    p,sortie,base=start()
    try:
        assert (paquet/'secret-key').read_text()==cle
        assert 'Préparer mon espace d’essai' not in client.open(base).read().decode()
        # La session est conservée dans le même processus navigateur/profil.
        assert 'Identité fictive SOC3' in client.open(base+'personnes/').read().decode()
    finally:
        stop(p,sortie)
    # Le programme Linux/Windows emploie les mêmes vues et le même moteur.
    p,sortie,base=start()
    try:
        client.open(base+'copies-locales/').read()
        sauvegarde=post(base,'copies-locales/',{'action':'sauvegarder'}).read()
        with post(base,'personnes/creer/',{'designation':'Après sauvegarde fictive'}) as r:
            assert 'Après sauvegarde fictive' in r.read().decode()
        def verifier_copie():
            token=next(c.value for c in cookies if c.name=='pas_accompagnement_csrftoken')
            frontiere='frontiere-copie-fictive'
            contenu=(f'--{frontiere}\r\nContent-Disposition: form-data; name="csrfmiddlewaretoken"\r\n\r\n{token}\r\n'
                f'--{frontiere}\r\nContent-Disposition: form-data; name="action"\r\n\r\nrestaurer\r\n'
                f'--{frontiere}\r\nContent-Disposition: form-data; name="archive"; filename="copie.zip"\r\nContent-Type: application/zip\r\n\r\n').encode()+sauvegarde+f'\r\n--{frontiere}--\r\n'.encode()
            req=urllib.request.Request(base+'copies-locales/',contenu,
                {'Content-Type':'multipart/form-data; boundary='+frontiere})
            assert 'Copie vérifiée' in client.open(req,timeout=10).read().decode()
        verifier_copie()
        post(base,'copies-locales/',{'action':'annuler'}).close()
        assert 'Après sauvegarde fictive' in client.open(base+'personnes/').read().decode()
        verifier_copie()
        post(base,'copies-locales/',{'action':'confirmer'}).close()
        try:
            post(base,'personnes/creer/',{'designation':'Écriture interdite'})
        except urllib.error.HTTPError as erreur:
            assert erreur.code==423
        else:
            raise AssertionError('Écriture acceptée après confirmation')
    finally:
        stop(p,sortie)
    import sqlite3
    from contextlib import closing
    with closing(sqlite3.connect(paquet/'accompagnement.sqlite3')) as db:
        assert db.execute('SELECT count(*) FROM personnes_personne').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM django_session').fetchone()[0]==0
    anciens=list(t.glob('.paquet-avant-restauration-*'))
    assert len(anciens)==1
    with closing(sqlite3.connect(anciens[0]/'accompagnement.sqlite3')) as db:
        assert db.execute('SELECT count(*) FROM personnes_personne').fetchone()[0]==2
    p,sortie,base=start()
    try:
        assert 'Se connecter' in client.open(base+'personnes/').read().decode()
        assert 'Restauration appliquée' in client.open(base+'copies-locales/').read().decode()
    finally:
        stop(p,sortie)
    print('Lanceur : téléchargement, annulation intacte, confirmation, écritures bloquées, arrêt/remplacement, état précédent et reconnexion : OK')
    print('Lanceur CHRS : premier compte -> fiche -> second lancement refusé -> fermeture -> relance et persistance : OK')
