from datetime import date, timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from . import identite
from .forms import PersonneForm
from .models import Personne, RevisionIdentite
from . import tests_navigation


class IdentiteTests(TestCase):
    def setUp(self):
        tests_navigation.NavigationTests.setUp(self)
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        self.u = type(self.u).objects.get(pk=self.u.pk)
        self.client.force_login(self.u)

    def donnees(self, **kw):
        valeurs = dict(designation='Nom fictif corrigé', prenom='Camille', date_naissance=None,
                       annee_naissance=1990, precision_naissance='annee_estimee')
        valeurs.update(kw)
        return valeurs

    def corriger(self, **kw):
        return identite.corriger(self.u, self.p, 'Information précisée', identite.jeton(self.p), **self.donnees(**kw))

    def test_naissance_facultative_et_precisions(self):
        self.assertTrue(PersonneForm({'designation': 'Provisoire'}).is_valid())
        for precision in ('exacte', 'estimee', 'annee', 'annee_estimee'):
            valeurs = self.donnees(precision_naissance=precision)
            if precision in ('exacte', 'estimee'):
                valeurs.update(date_naissance=date(1990,3,4), annee_naissance=None)
            form = PersonneForm(valeurs)
            self.assertTrue(form.is_valid(), form.errors)
        for valeurs in [self.donnees(precision_naissance=''), self.donnees(date_naissance=date(1990,1,1)),
                        self.donnees(precision_naissance='exacte'), self.donnees(annee_naissance=0),
                        self.donnees(annee_naissance=timezone.localdate().year+1),
                        self.donnees(precision_naissance='exacte', annee_naissance=None,
                                     date_naissance=timezone.localdate()+timedelta(days=1))]:
            self.assertFalse(PersonneForm(valeurs).is_valid(), valeurs)

    def test_correction_tracee_conserve_liens_et_auteur_origine(self):
        auteur_origine = self.p.cree_par_id
        corrigee = self.corriger()
        self.assertEqual(corrigee.pk, self.p.pk)
        self.assertEqual(self.a.beneficiaires.get(), corrigee)
        self.assertEqual(corrigee.cree_par_id, auteur_origine)
        self.assertIsNone(corrigee.date_naissance)
        self.assertEqual(corrigee.naissance_affichee, '1990 (Année estimée seulement)')
        trace = RevisionIdentite.objects.get()
        self.assertEqual(trace.ancienne_designation, 'Navigation fictive')
        self.assertEqual(trace.nouvelle_annee_naissance, 1990)
        self.assertEqual(trace.auteur, self.u)
        page = self.client.get(reverse('personnes:detail', args=[self.p.pk]))
        self.assertContains(page, 'Information précisée', count=1)
        self.assertContains(page, 'Année estimée seulement')

    def test_formulaire_perime_motif_et_rollback(self):
        attendu = identite.jeton(self.p)
        self.corriger()
        with self.assertRaises(ValidationError):
            identite.corriger(self.u, self.p, 'Périmé', attendu, **self.donnees(designation='Écrasement'))
        self.p.refresh_from_db()
        with self.assertRaises(ValidationError):
            identite.corriger(self.u, self.p, ' ', identite.jeton(self.p), **self.donnees(designation='Autre'))
        with patch.object(RevisionIdentite.objects, 'create', side_effect=RuntimeError('échec fictif')):
            with self.assertRaises(RuntimeError): self.corriger(designation='À annuler')
        self.p.refresh_from_db()
        self.assertEqual(self.p.designation, 'Nom fictif corrigé')
        self.assertEqual(RevisionIdentite.objects.count(), 1)

    def test_parcours_et_refus_direct(self):
        url = reverse('personnes:corriger_identite', args=[self.p.pk])
        page = self.client.get(url)
        self.assertContains(page, 'Motif de correction')
        valeurs = self.donnees(motif='Complément fictif', attendu=identite.jeton(self.p))
        valeurs['date_naissance'] = ''
        self.assertRedirects(self.client.post(url, valeurs), reverse('personnes:detail', args=[self.p.pk]))
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, valeurs).status_code, 403)
        with self.assertRaises(PermissionDenied):
            identite.corriger(type(self.u).objects.get(pk=self.u.pk), self.p, **valeurs)

    def test_formulaire_http_perime_garde_texte_sans_ecrasement(self):
        url = reverse('personnes:corriger_identite', args=[self.p.pk])
        attendu = identite.jeton(self.p)
        self.corriger()
        valeurs = self.donnees(designation='Proposition tardive', date_naissance='',
                              motif='Tardif', attendu=attendu)
        page = self.client.post(url, valeurs)
        self.assertEqual(page.status_code, 409)
        self.assertContains(page, 'Proposition tardive', status_code=409)
        self.p.refresh_from_db()
        self.assertEqual(self.p.designation, 'Nom fictif corrigé')
        self.assertEqual(RevisionIdentite.objects.count(), 1)

    def test_aucun_changement_annule_reservation_et_csrf_exige(self):
        avant = self.p.revision_identite
        with self.assertRaises(ValidationError):
            self.corriger(designation=self.p.designation, prenom=self.p.prenom,
                          annee_naissance=None, precision_naissance='')
        self.p.refresh_from_db()
        self.assertEqual(self.p.revision_identite, avant)
        self.assertFalse(RevisionIdentite.objects.exists())
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.u)
        self.assertEqual(client.post(reverse('personnes:corriger_identite', args=[self.p.pk]), {}).status_code, 403)

    def test_historique_masque_sans_droit_et_textes_echappes(self):
        self.corriger(designation='<script>fictif</script>')
        page = self.client.get(reverse('personnes:detail', args=[self.p.pk]))
        self.assertNotContains(page, '<script>fictif</script>')
        self.u.user_permissions.remove(*self.u.user_permissions.filter(codename='view_revisionidentite'))
        page = self.client.get(reverse('personnes:detail', args=[self.p.pk]))
        self.assertNotContains(page, 'Historique de l’identité')
        self.assertNotContains(page, 'Information précisée')

    def test_pdf_navigateur_ne_transforme_pas_annee_en_date(self):
        personne = self.corriger()
        from .pdf import produire
        with patch('pas_communs.pdf.fiche_texte', return_value=b'pdf') as moteur:
            self.assertEqual(produire(personne, navigateur=True), b'pdf')
        self.assertIn('Naissance : 1990 (Année estimée seulement)', moteur.call_args.args[1])


class ConcurrenceIdentiteTests(TransactionTestCase):
    def test_un_seul_formulaire_consomme_la_revision(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections, OperationalError
        IdentiteTests.setUp(self)
        attendu = identite.jeton(self.p)
        barriere = Barrier(2)
        def essayer(nom):
            close_old_connections()
            try:
                acteur = get_user_model().objects.get(pk=self.u.pk)
                acteur.get_all_permissions()
                barriere.wait(10)
                try:
                    identite.corriger(acteur, self.p, 'Concurrent fictif', attendu,
                        designation=nom, prenom='', date_naissance=None,
                        annee_naissance=None, precision_naissance='')
                    return True
                except (ValidationError, OperationalError):
                    return False
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultats = list(pool.map(essayer, ['Fictif A', 'Fictif B']))
        self.assertEqual(sum(resultats), 1)
        self.assertEqual(RevisionIdentite.objects.count(), 1)


class CompatibiliteIdentiteTests(TransactionTestCase):
    def test_migration_depuis_identite_incomplete_sans_attribution(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        compte = get_user_model().objects.create_user('migration-identite-fictive')
        cible = [('personnes', '0010_identite_naissance_et_corrections')]
        try:
            executor = MigrationExecutor(connection)
            ancienne = [('personnes', '0009_modelerapport')]
            executor.migrate(ancienne)
            apps = executor.loader.project_state(ancienne).apps
            p = apps.get_model('personnes', 'Personne').objects.create(
                designation='Identité historique fictive', cree_par_id=compte.pk)
            MigrationExecutor(connection).migrate(cible)
            actuelle = Personne.objects.get(pk=p.pk)
            self.assertIsNone(actuelle.date_naissance)
            self.assertIsNone(actuelle.annee_naissance)
            self.assertEqual(actuelle.precision_naissance, '')
            self.assertEqual(actuelle.designation, 'Identité historique fictive')
            self.assertFalse(compte.user_permissions.exists())
        finally:
            MigrationExecutor(connection).migrate(cible)

    def test_journal_et_naissance_conserves_par_reprise_zip(self):
        from django.db import connection
        if connection.vendor != "sqlite":
            self.skipTest("Les copies autonomes utilisent SQLite.")
        from contextlib import closing
        from pathlib import Path
        from tempfile import TemporaryDirectory
        import sqlite3
        from django.db import connection
        from pas_communs.paquets import creer_sauvegarde
        from pas_a_pas_accompagnement import paquets
        IdentiteTests.setUp(self)
        identite.corriger(self.u, self.p, 'Naissance précisée', identite.jeton(self.p),
            designation='Fictif corrigé', prenom='', date_naissance=None,
            annee_naissance=1990, precision_naissance='annee_estimee')
        with TemporaryDirectory() as temporaire:
            racine = Path(temporaire)
            source = racine / 'source'
            source.mkdir()
            (source / 'secret-key').write_text('cle-fictive-identite')
            (source / 'media').mkdir()
            with closing(sqlite3.connect(source / paquets.PROFIL.base)) as copie:
                connection.connection.backup(copie)
            archive = racine / 'identite.zip'
            creer_sauvegarde(source, archive, profil=paquets.PROFIL)
            preparation = paquets.verifier(archive, racine, 'preparation')
            destination = racine / 'restauree'
            paquets.installer_copie(preparation, destination)
            with closing(sqlite3.connect(destination / paquets.PROFIL.base)) as db:
                self.assertEqual(db.execute('SELECT annee_naissance, precision_naissance FROM personnes_personne WHERE designation=?',
                    ['Fictif corrigé']).fetchone(), (1990, 'annee_estimee'))
                self.assertEqual(db.execute('SELECT ancienne_designation, nouvelle_designation, motif FROM personnes_revisionidentite').fetchone(),
                    ('Navigation fictive', 'Fictif corrigé', 'Naissance précisée'))
