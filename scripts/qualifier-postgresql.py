#!/usr/bin/env python3
"""Bases fictives indépendantes : migrations, tests et dump/restauration PostgreSQL."""
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = 'pas_a_pas_accompagnement.settings_tests_postgresql'


def main():
    if os.environ.get('ACCOMPAGNEMENT_PG_QUALIFICATION') != 'oui':
        raise SystemExit('Activer explicitement ACCOMPAGNEMENT_PG_QUALIFICATION=oui sur un service jetable.')
    for cle in ('PGHOST', 'PGPORT', 'PGUSER', 'PGPASSWORD'):
        if not os.environ.get(cle):
            raise SystemExit(f'{cle} doit être explicite.')
    import psycopg
    from psycopg import sql
    # Attendre le service CI au plus 30 secondes ; aucune commande destructive.
    for tentative in range(15):
        try:
            admin = psycopg.connect(dbname='postgres', autocommit=True, connect_timeout=1)
            break
        except psycopg.OperationalError:
            if tentative == 14:
                raise
            time.sleep(1)
    # Noms générés ici ; aucune base préexistante n’est effacée ou réutilisée.
    source = 'pas_ci_' + uuid.uuid4().hex[:12]
    cible = 'pas_ci_' + uuid.uuid4().hex[:12]
    creees = []
    with tempfile.TemporaryDirectory(prefix='pas-ci-pg-') as dossier:
        env = {**os.environ, 'DJANGO_SETTINGS_MODULE': SETTINGS,
               'ACCOMPAGNEMENT_DONNEES': dossier, 'PGDATABASE': source}
        def commande(*args, database=source, capture=False):
            return subprocess.run(args, cwd=ROOT, env={**env, 'PGDATABASE': database},
                                  check=True, text=True, capture_output=capture).stdout
        def django(*args, database=source, capture=False):
            return commande(sys.executable, 'manage.py', *args, database=database, capture=capture)
        with admin:
            try:
                for nom in (source, cible):
                    admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(nom)))
                    creees.append(nom)
                version = admin.info.server_version
                print('Qualification PostgreSQL', version, ': bases fictives, Python', sys.version.split()[0], flush=True)
                if version // 10000 != 17:
                    raise RuntimeError('Cette matrice qualifie PostgreSQL 17.')
                for outil in ('pg_dump', 'pg_restore'):
                    version_client = commande(outil, '--version', capture=True)
                    print(version_client.strip(), flush=True)
                    if not re.search(r'\b17\.', version_client):
                        raise RuntimeError('La qualification exige les clients PostgreSQL 17.')
                django('check')
                django('migrate', '--noinput')
                django('makemigrations', '--check', '--dry-run')
                django('test', 'identites', 'personnes.tests', 'personnes.tests_pdf',
                       'personnes.tests_postgresql', '--noinput')
                # Compte sans mot de passe utilisable, personne UUID et relation protégée.
                django('shell', '-c', """
from django.contrib.auth import get_user_model
from django.test import override_settings
from personnes.models import Personne
from identites import double_facteur as facteur
from identites.tests_double_facteur import CLE
from pas_communs.authentification import totp
from django_otp.oath import TOTP
u = get_user_model().objects.create_user('qualification-fictive')
Personne.objects.create(designation='Personne fictive PostgreSQL', cree_par=u)
with override_settings(DOUBLE_FACTEUR_CLES=[CLE]):
    ligne = facteur.commencer(u)
    secret = totp.dechiffrer(ligne.cle_chiffree, cles=[CLE])
    t = TOTP(secret)
    t.time = 1800000000
    assert facteur.confirmer(u, f'{t.token():06d}', instant=t.time)
""")
                labels = ('identites', 'personnes', 'auth.permission', 'contenttypes')
                avant = json.loads(django('dumpdata', *labels, '--all', '--natural-foreign',
                                         '--indent', '2', capture=True))
                archive = str(Path(dossier) / 'fictif.dump')
                commande('pg_dump', '--format=custom', '--no-owner', '--no-acl', '--file', archive)
                commande('pg_restore', '--exit-on-error', '--no-owner', '--no-acl',
                         '--dbname', cible, archive, database=cible)
                apres = json.loads(django('dumpdata', *labels, '--all', '--natural-foreign',
                                         '--indent', '2', database=cible, capture=True))
                cle = lambda objet: (objet['model'], str(objet['pk']))
                if sorted(avant, key=cle) != sorted(apres, key=cle):
                    raise RuntimeError('Le dump restauré diffère des données source.')
                # Vérifie aussi la relation protégée et les séquences après restauration.
                django('shell', '-c', """
from django.contrib.auth import get_user_model
from personnes.models import Personne
from django.db import IntegrityError, transaction
User = get_user_model()
u = User.objects.get(username='qualification-fictive')
assert Personne.objects.get(cree_par=u).pk
nouveau = User.objects.create_user('apres-restauration-fictif')
assert nouveau.pk != u.pk
try:
    with transaction.atomic():
        User.objects.create_user('qualification-fictive')
except IntegrityError:
    pass
else:
    raise AssertionError('Unicité absente après restauration')
try:
    with transaction.atomic():
        Personne.objects.create(designation='Relation fictive invalide', cree_par_id=-1)
except IntegrityError:
    pass
else:
    raise AssertionError('Contrainte relationnelle absente après restauration')
""", database=cible)
                print('PostgreSQL : migrations, tests, UUID/comptes et dump restauré identiques.', flush=True)
            finally:
                for nom in reversed(creees):
                    admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(nom)))


if __name__ == '__main__':
    main()
