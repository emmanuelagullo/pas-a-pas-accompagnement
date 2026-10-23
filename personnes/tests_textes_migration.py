"""Reprise historique et copie ZIP privée du nouveau format."""
import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from unittest import skipUnless
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from pas_communs.paquets import creer_sauvegarde
from pas_a_pas_accompagnement.paquets import PROFIL, verifier, installer_copie
from .tests_textes_riches import document


class MigrationTextesTests(TransactionTestCase):
    @skipUnless(connection.vendor == 'sqlite', 'Les copies locales portent sur SQLite.')
    def test_ancien_texte_non_converti_et_copie_integrale(self):
        executor = MigrationExecutor(connection)
        anciennes = [('personnes', '0013_parcours_bd6')]
        feuilles = executor.loader.graph.leaf_nodes()
        executor.migrate(anciennes)
        try:
            apps = executor.loader.project_state(anciennes).apps
            u = apps.get_model('identites', 'Utilisateur').objects.create(username='migration-texte-fictive', password='!')
            t = apps.get_model('personnes', 'Transmission').objects.create(contenu='**ancien** <à compléter>', auteur_id=u.pk)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(feuilles)
        from .models import Transmission, RevisionContribution
        ancien = Transmission.objects.get(pk=t.pk)
        self.assertIsNone(ancien.contenu_document)
        self.assertEqual(ancien.contenu, '**ancien** <à compléter>')
        with tempfile.TemporaryDirectory() as temporaire:
            racine = Path(temporaire)
            source = racine / 'source'; source.mkdir()
            (source / 'secret-key').write_text('cle-fictive')
            doc = document()
            nouveau = Transmission.objects.create(contenu='Texte fictif', contenu_document=doc, auteur_id=u.pk)
            RevisionContribution.objects.create(transmission=nouveau, auteur_id=u.pk,
                ancien_texte='Ancien fictif', nouveau_texte='Texte fictif', motif='Précision fictive',
                ancien_texte_document=None, nouveau_texte_document=doc)
            with closing(sqlite3.connect(source / PROFIL.base)) as db:
                db.executescript('\n'.join(connection.connection.iterdump()))
            archive = racine / 'copie.zip'
            creer_sauvegarde(source, archive, profil=PROFIL)
            preparation = verifier(archive, racine)
            destination = racine / 'restauree'
            installer_copie(preparation, destination)
            with closing(sqlite3.connect(destination / PROFIL.base)) as db:
                texte, brut = db.execute('SELECT contenu, contenu_document FROM personnes_transmission WHERE id=?', (ancien.pk,)).fetchone()
                self.assertEqual((texte, brut), (ancien.contenu, None))
                brut = db.execute('SELECT contenu_document FROM personnes_transmission WHERE id=?', (nouveau.pk,)).fetchone()[0]
                self.assertEqual(json.loads(brut), doc)
                avant, apres = db.execute('SELECT ancien_texte_document, nouveau_texte_document FROM personnes_revisioncontribution WHERE transmission_id=?', (nouveau.pk,)).fetchone()
                self.assertIsNone(avant); self.assertEqual(json.loads(apres), doc)
