"""Profil des copies locales CHRS ; aucune règle scolaire."""
import shutil

from django.db import connection
from django.db.migrations.loader import MigrationLoader
from pas_communs.paquets import ProfilPaquet, preparer_restauration, vider_tables_copie, RestaurationLocale

PROFIL = ProfilPaquet("pas-a-pas-accompagnement", "pas-a-pas-accompagnement-paquet", "accompagnement.sqlite3")


restauration = RestaurationLocale()


def neutraliser_copie(dossier):
    vider_tables_copie(dossier / PROFIL.base, ("django_session", "identites_limiteauthentification"))


def verifier(source, parent, nom_paquet="paquet-autonome"):
    migrations = set(MigrationLoader(connection, ignore_no_migrations=True).disk_migrations)
    return preparer_restauration(source, parent, nom_paquet, profil=PROFIL, migrations_connues=migrations)


def installer_copie(preparation, destination):
    """Nouveau dossier seulement ; ne remplace jamais l'espace courant."""
    destination.mkdir(mode=0o700)  # réservation exclusive, refuse aussi un lien
    try:
        neutraliser_copie(preparation.etape)
        for fichier in preparation.etape.iterdir():
            fichier.rename(destination / fichier.name)
    except BaseException:
        shutil.rmtree(destination)
        raise
    finally:
        shutil.rmtree(preparation.etape)
