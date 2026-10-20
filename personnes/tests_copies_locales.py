"""Parcours propriétaire natif, refus et annulation sans toucher à la source."""
from contextlib import closing
from io import BytesIO
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from pas_communs.paquets import creer_sauvegarde, RestaurationLocale
from pas_a_pas_accompagnement import copies_locales, paquets


class CopiesLocalesTests(TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.source = Path(t.name) / "paquet-autonome"
        self.source.mkdir()
        self.etat = RestaurationLocale()
        p = patch.object(copies_locales, "restauration", self.etat)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self.etat.annuler)
        self.parametres = override_settings(LOCAL_DIR=self.source, OUTILS_COPIES_BUREAU=True)
        self.parametres.enable()
        self.addCleanup(self.parametres.disable)
        (self.source / "secret-key").write_text("cle-fictive")
        (self.source / "media").mkdir()
        (self.source / "media/fictif.txt").write_bytes(b"media fictif")
        with closing(sqlite3.connect(self.source / paquets.PROFIL.base)) as db, db:
            db.execute('CREATE TABLE django_migrations (app, name)')
            db.execute('CREATE TABLE django_session (valeur)')
            db.execute("INSERT INTO django_session VALUES ('session-fictive')")
        self.avant = (self.source / paquets.PROFIL.base).read_bytes()
        self.url = reverse("copies_locales")

    def archive(self):
        zip = BytesIO()
        creer_sauvegarde(self.source, zip, profil=paquets.PROFIL)
        zip.seek(0)
        return zip

    def test_inaccessible_sur_serveur_et_pwa(self):
        with override_settings(OUTILS_COPIES_BUREAU=False):
            self.assertEqual(self.client.get(self.url).status_code, 404)
            self.assertEqual(self.client.post(self.url, {"action": "sauvegarder"}).status_code, 404)

    def test_verifier_annuler_et_refuser_conservent_source(self):
        reponse = self.client.post(self.url, {"action": "restaurer", "archive": self.archive()})
        self.assertEqual(reponse.status_code, 302)
        self.assertContains(self.client.get(self.url), "Copie vérifiée")
        etape = self.etat.preparation().etape
        with closing(sqlite3.connect(etape / paquets.PROFIL.base)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM django_session').fetchone()[0], 0)
        self.client.post(self.url, {"action": "annuler"})
        self.assertFalse(etape.exists())
        mauvais = BytesIO(b'archive invalide')
        self.client.post(self.url, {"action": "restaurer", "archive": mauvais})
        self.assertIsNone(self.etat.preparation())
        self.assertEqual((self.source / paquets.PROFIL.base).read_bytes(), self.avant)
        self.assertEqual((self.source / "media/fictif.txt").read_bytes(), b"media fictif")

    def test_confirmation_sans_activation_dans_requete(self):
        self.client.post(self.url, {"action": "restaurer", "archive": self.archive()})
        self.client.post(self.url, {"action": "confirmer"})
        self.assertIsNotNone(self.etat.attente())
        self.assertContains(self.client.get(self.url), "Appliquer la restauration et redémarrer")
        self.assertEqual((self.source / paquets.PROFIL.base).read_bytes(), self.avant)
        # Le lanceur applique après arrêt HTTP et close_all, jamais la vue.
        import shutil
        shutil.rmtree(self.etat.attente().etape)
