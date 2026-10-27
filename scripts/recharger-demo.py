#!/usr/bin/env python3
"""Migrer puis recharger une démonstration locale Linux existante, sans la recréer."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys

RACINE=Path(__file__).resolve().parent.parent

def environnement(pid,proc=Path('/proc')):
    if pid<2:raise ValueError('PID de serveur invalide.')
    dossier=proc/str(pid)
    if dossier.stat().st_uid!=os.getuid():raise ValueError('Le serveur doit appartenir au compte courant.')
    if b'gunicorn' not in (dossier/'cmdline').read_bytes():raise ValueError('Le PID ne désigne pas Gunicorn.')
    valeurs=dict(x.split('=',1) for x in (dossier/'environ').read_bytes().decode(errors='surrogateescape').split('\0') if '=' in x)
    if valeurs.get('DJANGO_SETTINGS_MODULE')!='pas_a_pas_accompagnement.settings_demo' or valeurs.get('ACCOMPAGNEMENT_DEMONSTRATION')!='oui':
        raise ValueError('Ce processus n’est pas une démonstration Pas à Pas.')
    if valeurs.get('RENDER_EXTERNAL_HOSTNAME') or valeurs.get('ACCOMPAGNEMENT_BIND') not in ('127.0.0.1','::1'):
        raise ValueError('Cette commande est réservée à la démonstration locale sur bouclage.')
    donnees=Path(valeurs.get('ACCOMPAGNEMENT_DONNEES',''))
    if not donnees.is_absolute() or not donnees.is_dir():raise ValueError('Dossier de démonstration introuvable.')
    # La commande ne journalise aucun environnement ni secret.
    return valeurs

def recharger(pid_file):
    pid=int(Path(pid_file).read_text().strip())
    serveur=environnement(pid)
    env={**os.environ,**serveur}
    subprocess.run([sys.executable,str(RACINE/'manage.py'),'migrate','--noinput'],cwd=RACINE,env=env,check=True)
    subprocess.run([sys.executable,str(RACINE/'manage.py'),'collectstatic','--noinput'],cwd=RACINE,env=env,check=True)
    # Revalider le processus après les opérations avant de lui envoyer le signal.
    courant=environnement(pid)
    if courant.get('ACCOMPAGNEMENT_DONNEES')!=serveur['ACCOMPAGNEMENT_DONNEES']:
        raise ValueError('Le processus a changé ; aucun signal envoyé.')
    os.kill(pid,signal.SIGHUP)
    print('Démonstration migrée, ressources mises à jour et code rechargé ; données conservées.')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pid-file',type=Path,required=True)
    args=p.parse_args()
    if not sys.platform.startswith('linux'):p.error('Commande Linux ; utilisez le démarrage propre de votre plateforme.')
    try:recharger(args.pid_file)
    except (OSError,ValueError,subprocess.CalledProcessError) as e:raise SystemExit('Rechargement non confirmé : '+str(e))

if __name__=='__main__':main()
