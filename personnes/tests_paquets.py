from contextlib import closing
from io import BytesIO, StringIO
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase, override_settings
from pas_communs.paquets import ProfilPaquet, creer_sauvegarde, preparer_restauration
from pas_a_pas_accompagnement.paquets import PROFIL


class PaquetsTests(TestCase):
    def setUp(self):
        temporaire = tempfile.TemporaryDirectory()
        self.addCleanup(temporaire.cleanup)
        self.racine = Path(temporaire.name)
        self.source = self.racine / "source"
        self.source.mkdir()
        (self.source / "secret-key").write_text("cle-fictive")
        self.archive = self.racine / "copie.zip"
        with closing(sqlite3.connect(self.source / PROFIL.base)) as db, db:
            db.execute("CREATE TABLE django_migrations (app TEXT, name TEXT)")
            migrations = MigrationLoader(connection).disk_migrations
            db.executemany("INSERT INTO django_migrations VALUES (?,?)", migrations)
            db.execute("CREATE TABLE donnees_fictives (valeur TEXT)")
            db.execute("INSERT INTO donnees_fictives VALUES ('identite-incomplete')")
            db.execute("CREATE TABLE django_session (session_key TEXT)")
            db.execute("INSERT INTO django_session VALUES ('session-fictive')")

    def test_sauvegarde_verification_et_copie_independante(self):
        with override_settings(LOCAL_DIR=self.source):
            call_command("sauvegarder_paquet", str(self.archive), stdout=StringIO())
            call_command("verifier_sauvegarde", str(self.archive), stdout=StringIO())
        destination = self.racine / "restauree"
        call_command("restaurer_copie", str(self.archive), str(destination), stdout=StringIO())
        with closing(sqlite3.connect(destination / PROFIL.base)) as db:
            self.assertEqual(db.execute("SELECT valeur FROM donnees_fictives").fetchone(), ("identite-incomplete",))
            self.assertEqual(db.execute("SELECT count(*) FROM django_session").fetchone(), (0,))
        self.assertEqual((destination / "secret-key").read_text(), "cle-fictive")
        with closing(sqlite3.connect(self.source / PROFIL.base)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM django_session").fetchone(), (1,))
        self.assertFalse(list(self.racine.glob(".restauration-*")))

    def test_refus_ecrasement_zip_et_dossier(self):
        self.archive.write_bytes(b"a-conserver")
        with override_settings(LOCAL_DIR=self.source):
            with self.assertRaises(CommandError):
                call_command("sauvegarder_paquet", str(self.archive))
        self.assertEqual(self.archive.read_bytes(), b"a-conserver")
        with self.assertRaises(CommandError):
            call_command("restaurer_copie", str(self.archive), str(self.source))
        self.assertEqual((self.source / "secret-key").read_text(), "cle-fictive")

    def test_refus_croise_dans_les_deux_sens_avant_extraction(self):
        autre = ProfilPaquet("petits-pas", "petits-pas-paquet", "carnet.sqlite3", True)
        (self.source / "accompagnement.sqlite3").rename(self.source / "carnet.sqlite3")
        creer_sauvegarde(self.source, self.archive, profil=autre)
        with self.assertRaises(CommandError):
            call_command("restaurer_copie", str(self.archive), str(self.racine / "interdite"))
        self.assertFalse((self.racine / "interdite").exists())
        (self.source / "carnet.sqlite3").rename(self.source / "accompagnement.sqlite3")
        archive = BytesIO()
        creer_sauvegarde(self.source, archive, profil=PROFIL)
        with patch("pas_communs.paquets.tempfile.mkdtemp") as creer:
            with self.assertRaises(ValueError):
                preparer_restauration(archive, self.racine, profil=autre)
            creer.assert_not_called()
