#!/usr/bin/env python3
"""Exercer les vrais scripts de démarrage Unix, dans un espace fictif isolé."""
import argparse
import http.client
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent


def requete(port, path, **headers):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        c.request('GET', path, headers={'Host': 'localhost', **headers})
        r = c.getresponse()
        return r.status, dict(r.getheaders()), r.read()
    finally:
        c.close()


def attendre_demarrage(processus, port, journal, delai):
    """Borne réelle incluant migrations/statiques ; ne pas compter les sondages."""
    limite = time.monotonic() + delai
    while time.monotonic() < limite:
        code = processus.poll()
        if code is not None:
            raise RuntimeError(f'Démarrage interrompu (code {code}) : '+journal.read_text())
        try:
            status, _, body = requete(port, '/health/', **{'X-Forwarded-Proto': 'https'})
            if status == 200 and json.loads(body).get('status') == 'ok':
                return
        except (OSError, ValueError):
            pass
        time.sleep(.2)
    raise RuntimeError(f'Démarrage expiré après {delai:g} s (préparation et HTTP) : '+journal.read_text())


def exercer(mode, delai_demarrage=180):
    with tempfile.TemporaryDirectory(prefix='deploiement-chrs-fictif-') as t:
        temp = Path(t)
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('ACCOMPAGNEMENT_', 'CARNET_'))
               and k not in {'DATABASE_URL', 'DJANGO_SETTINGS_MODULE', 'PORT'}}
        env.update(ACCOMPAGNEMENT_HOSTS='localhost',
                   ACCOMPAGNEMENT_CSRF_ORIGINS='https://localhost',
                   ACCOMPAGNEMENT_PROXY_HTTPS='oui',
                   ACCOMPAGNEMENT_BIND='127.0.0.1',
                   PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1',
                   TMPDIR=str(temp), PATH=str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH',''))
        if mode == 'persistant':
            env.update(ACCOMPAGNEMENT_DONNEES=str(temp/'donnees'),
                       ACCOMPAGNEMENT_SAUVEGARDES=str(temp/'sauvegardes'),
                       ACCOMPAGNEMENT_MAINTENANCE='oui')
        script = ROOT / ('start-render.sh' if mode == 'ephemere' else 'start-persistent.sh')
        cles = []
        for tour in range(2):
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            env['PORT'] = str(port)
            log = temp / f'demarrage-{tour}.log'
            with log.open('wb') as out:
                p = subprocess.Popen(['bash', str(script)], cwd=ROOT, env=env,
                    stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    attendre_demarrage(p, port, log, delai_demarrage)
                    assert requete(port, '/health/')[0] == 301
                    status, headers, body = requete(port, '/connexion/', **{'X-Forwarded-Proto': 'https'})
                    assert status == 200 and 'Secure' in headers['Set-Cookie']
                    assert requete(port, '/static/application.css', **{'X-Forwarded-Proto': 'https'})[0] == 200
                    assert requete(port, '/installer/', **{'X-Forwarded-Proto': 'https'})[0] == 404
                    if mode == 'ephemere':
                        assert requete(port, '/mon-compte/mot-de-passe/', **{'X-Forwarded-Proto': 'https'})[0] == 403
                    assert ('Démonstration publique partagée' in body.decode()) == (mode == 'ephemere')
                finally:
                    if p.poll() is None:
                        os.killpg(p.pid, signal.SIGTERM)
                    try:
                        p.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid, signal.SIGKILL)
                        p.wait()
            donnees = temp/'donnees' if mode == 'persistant' else sorted(temp.glob('pas-a-pas-demo-*'))[-1]
            # Retrouver le dernier dossier sans supposer l'ordre aléatoire mktemp.
            if mode == 'ephemere':
                donnees = max(temp.glob('pas-a-pas-demo-*'), key=lambda p: p.stat().st_mtime_ns)
            cles.append((donnees/'secret-key').read_bytes())
            # La préparation publique ne doit jamais être une commande de reset.
            demo_env = {**env, 'ACCOMPAGNEMENT_DONNEES': str(donnees),
                        'ACCOMPAGNEMENT_DEMONSTRATION': 'oui',
                        'DJANGO_SETTINGS_MODULE': 'pas_a_pas_accompagnement.settings_demo' if mode == 'ephemere' else 'pas_a_pas_accompagnement.settings_serveur'}
            refus_demo = subprocess.run([sys.executable,'manage.py','preparer_demonstration'],
                cwd=ROOT,env=demo_env,capture_output=True)
            assert refus_demo.returncode != 0
            assert (b'Base non vide' if mode == 'ephemere' else b'jetable') in refus_demo.stderr

            inspect_env = {**env, 'ACCOMPAGNEMENT_DONNEES': str(donnees),
                           'DJANGO_SETTINGS_MODULE': 'pas_a_pas_accompagnement.settings'}
            code = "from personnes.models import Personne; from django.contrib.auth import get_user_model; "
            if mode == 'ephemere':
                code += "assert Personne.objects.count()==1; u=get_user_model().objects.get(username='essai'); assert not u.is_staff and not u.is_superuser"
            elif tour == 0:
                code += "assert not Personne.objects.exists(); assert not get_user_model().objects.exists(); u=get_user_model().objects.create_user('ci-fictif'); Personne.objects.create(designation='Persistance fictive',cree_par=u)"
            else:
                code += "assert Personne.objects.get().designation=='Persistance fictive'"
            subprocess.run([sys.executable, 'manage.py', 'shell', '-c', code], cwd=ROOT, env=inspect_env, check=True)
        assert (cles[0] == cles[1]) == (mode == 'persistant')
        if mode == 'persistant':
            from pas_communs.paquets import preparer_restauration
            sys.path.insert(0, str(ROOT))
            from pas_a_pas_accompagnement.paquets import PROFIL
            copies = list((temp/'sauvegardes').glob('*.zip'))
            assert len(copies) == 1
            copie = preparer_restauration(copies[0], temp, profil=PROFIL)
            assert (copie.etape/'accompagnement.sqlite3').is_file()
            import sqlite3
            with sqlite3.connect(copie.etape/'accompagnement.sqlite3') as sql:
                assert sql.execute('SELECT designation FROM personnes_personne').fetchall() == [('Persistance fictive',)]
            assert (copie.etape/'secret-key').read_bytes() == cles[-1]

        # Une configuration dangereuse est refusée avant migration/démarrage.
        env['DATABASE_URL'] = 'postgresql://interdit.invalid/fictif'
        refus = subprocess.run(['bash', str(script)], cwd=ROOT, env=env, capture_output=True)
        assert refus.returncode != 0 and b'Refus' in refus.stderr
        print(f'Déploiement {mode} : HTTP, statiques, refus, arrêt et redémarrage : OK')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['ephemere', 'persistant'])
    parser.add_argument('--delai-demarrage', type=float, default=180,
                        help='Délai par démarrage, préparation incluse (secondes, défaut : 180).')
    args = parser.parse_args()
    if not 0 < args.delai_demarrage <= 900:
        parser.error('Choisir un délai entre 0 exclu et 900 secondes.')
    exercer(args.mode, args.delai_demarrage)
