"""Profil des copies locales CHRS ; aucune règle scolaire."""
from contextlib import closing
import shutil
import sqlite3

from django.db import connection
from django.db.migrations.loader import MigrationLoader
from pas_communs.paquets import ProfilPaquet, preparer_restauration

PROFIL = ProfilPaquet("pas-a-pas-accompagnement", "pas-a-pas-accompagnement-paquet", "accompagnement.sqlite3")


def verifier(source, parent):
    migrations = set(MigrationLoader(connection, ignore_no_migrations=True).disk_migrations)
    return preparer_restauration(source, parent, profil=PROFIL, migrations_connues=migrations)


def installer_copie(preparation, destination):
    """Nouveau dossier seulement ; ne remplace jamais l'espace courant."""
    destination.mkdir(mode=0o700)  # réservation exclusive, refuse aussi un lien
    try:
        with closing(sqlite3.connect(preparation.etape / PROFIL.base)) as db, db:
            for table in ("django_session", "identites_limiteauthentification"):
                if db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (table,)).fetchone():
                    db.execute(f'DELETE FROM "{table}"')
        for fichier in preparation.etape.iterdir():
            fichier.rename(destination / fichier.name)
    except BaseException:
        shutil.rmtree(destination)
        raise
    finally:
        shutil.rmtree(preparation.etape)
