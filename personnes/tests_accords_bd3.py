"""BD3 : décisions, dépendances, droits, conflits et conservation de l'historique."""
from datetime import date
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from .tests_hebergement import Donnees
from . import accords, corrections, repas, hebergement as h, suivi
from .models import AccordRepas, AccordHebergement, EvolutionAccord, RepasDistribue, Sejour, OperationRepas


class AccordsBD3Tests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        call_command('autoriser_bd3', self.u.username, stdout=StringIO())
        self.u = type(self.u).objects.get(pk=self.u.pk)
        self.r = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), date(2026, 2, 1), 'dejeuner')
        self.vide = h.accorder(self.u, self.a, [self.p], date(2026, 1, 1), date(2026, 2, 1))
        self.client.force_login(self.u)

    def prolonger(self, objet, fin, **kw):
        return accords.prolonger(self.u, objet, fin, kw.get('motif', 'Décision fictive'), kw.get('attendu', accords.jeton(objet)))

    def annuler(self, objet):
        return accords.annuler(self.u, objet, 'Accord fictif saisi par erreur', accords.jeton(objet))

    def test_prolongation_deux_types_tracee_sans_realisation_ni_correction(self):
        for objet in (self.r, self.accord):
            ancien = objet.fin
            beneficiaires = set(objet.beneficiaires.values_list('pk', flat=True))
            self.prolonger(objet, date(2026, 4, 1))
            objet.refresh_from_db()
            self.assertEqual(objet.fin, date(2026, 4, 1))
            self.assertEqual(set(objet.beneficiaires.values_list('pk', flat=True)), beneficiaires)
            trace = EvolutionAccord.objects.latest('pk')
            self.assertEqual((trace.ancienne_fin, trace.nouvelle_fin), (ancien, objet.fin))
            self.assertEqual(trace.action, 'prolongation')
            self.assertEqual(trace.auteur, self.u)
        self.s.refresh_from_db(); self.a.refresh_from_db()
        self.assertEqual(self.s.debut, date(2026, 1, 3))
        self.assertIsNone(self.s.fin)
        self.assertIsNone(self.a.fin)
        self.assertEqual(Sejour.objects.count(), 1)
        self.assertFalse(RepasDistribue.objects.exists())
        self.assertFalse(self.a.corrections_periodes.exists())

    def test_prolongation_ouverte_et_refus_de_reduire_ou_deja_illimite(self):
        for fin in [date(2026, 1, 20), date(2026, 2, 1)]:
            with self.assertRaises(ValidationError): self.prolonger(self.r, fin)
        self.prolonger(self.r, None)
        self.r.refresh_from_db()
        with self.assertRaises(ValidationError): self.prolonger(self.r, date(2026, 6, 1))
        self.assertIsNone(self.r.fin)
        self.assertEqual(EvolutionAccord.objects.count(), 1)

    def test_borne_accompagnement_clos_refus_et_pas_de_reouverture(self):
        self.a.fin = date(2026, 3, 1); self.a.save(update_fields=['fin'])
        self.r.refresh_from_db()
        for fin in [None, date(2026, 3, 2)]:
            with self.assertRaises(ValidationError): self.prolonger(self.r, fin)
        self.prolonger(self.r, date(2026, 3, 1))
        self.a.refresh_from_db(); self.r.refresh_from_db()
        self.assertEqual(self.a.fin, self.r.fin)

    def test_motif_requis_et_rollback_si_journal_echoue(self):
        for texte in ['', '   ', 'x' * 241]:
            with self.assertRaises(ValidationError): self.prolonger(self.r, date(2026, 3, 1), motif=texte)
        self.m.refresh_from_db()
        avant = self.m.revision
        with patch('personnes.accords.tracer', side_effect=RuntimeError('Échec fictif')):
            with self.assertRaises(RuntimeError): self.prolonger(self.r, date(2026, 3, 1))
            with self.assertRaises(RuntimeError): self.annuler(self.r)
        self.r.refresh_from_db(); self.m.refresh_from_db()
        self.assertEqual(self.r.fin, date(2026, 2, 1))
        self.assertIsNone(self.r.annule_le)
        self.assertEqual(self.r.revision, 0)
        self.assertEqual(self.m.revision, avant)
        self.assertFalse(EvolutionAccord.objects.exists())

    def test_annulation_deux_types_conserve_donnees_et_journaux_originaux(self):
        historique = OperationRepas.objects.count()
        for objet in (self.r, self.vide):
            self.annuler(objet)
            objet.refresh_from_db()
            self.assertIsNotNone(objet.annule_le)
            self.assertEqual(objet.annule_par, self.u)
            self.assertEqual(objet.fin, date(2026, 2, 1))
            self.assertTrue(objet.beneficiaires.filter(pk=self.p.pk).exists())
            with self.assertRaises(ValidationError): self.annuler(objet)
        self.assertEqual(AccordRepas.objects.count(), 1)
        self.assertEqual(AccordHebergement.objects.count(), 2)
        self.assertEqual(OperationRepas.objects.count(), historique)
        self.assertEqual(EvolutionAccord.objects.filter(action='annulation').count(), 2)

    def test_annulation_refuse_sejour_meme_clos_et_distribution_meme_annulee(self):
        h.sortir(self.u, self.s, date(2026, 1, 10))
        distribution = repas.distribuer(self.u, self.r, self.p, date(2026, 1, 5), 1)
        repas.annuler(self.u, distribution, 'Erreur fictive')
        for objet in (self.accord, self.r):
            with self.assertRaises(ValidationError): self.annuler(objet)
            objet.refresh_from_db()
            self.assertIsNone(objet.annule_le)
        self.assertFalse(EvolutionAccord.objects.exists())

    def test_accord_annule_refuse_admission_distribution_prolongation_correction(self):
        ancien_token = corrections.jeton(self.r)
        self.annuler(self.r); self.annuler(self.vide)
        with self.assertRaises(ValidationError): repas.distribuer(self.u, self.r, self.p, date(2026, 1, 5), 1)
        with self.assertRaises(ValidationError): h.admettre_individuellement(self.u, self.vide, [self.p], date(2026, 1, 5))
        with self.assertRaises(ValidationError): self.prolonger(self.r, date(2026, 3, 1))
        with self.assertRaises(ValidationError): corrections.periode(self.u, self.r, date(2026, 1, 2), self.r.fin, 'Erreur', ancien_token)
        self.assertFalse(self.vide.sejours.exists())
        self.assertFalse(RepasDistribue.objects.exists())

    def test_formulaires_perimes_et_rejoues_et_aller_retour_aba(self):
        ancien = accords.jeton(self.r)
        ancien_correction = corrections.jeton(self.r)
        self.prolonger(self.r, date(2026, 3, 1))
        with self.assertRaises(ValidationError): self.prolonger(self.r, date(2026, 4, 1), attendu=ancien)
        with self.assertRaises(ValidationError): corrections.periode(self.u, self.r, self.r.debut, date(2026, 4, 1), 'Ancien formulaire', ancien_correction)
        self.r.refresh_from_db()
        corrections.periode(self.u, self.r, self.r.debut, date(2026, 2, 1), 'Fin fictive rectifiée', corrections.jeton(self.r))
        self.r.refresh_from_db()
        with self.assertRaises(ValidationError): self.prolonger(self.r, date(2026, 4, 1), attendu=ancien)

    def test_changement_parent_ou_dependances_invalide_le_formulaire(self):
        token = accords.jeton(self.r)
        repas.distribuer(self.u, self.r, self.p, date(2026, 1, 5), 1)
        with self.assertRaises(ValidationError): self.prolonger(self.r, date(2026, 3, 1), attendu=token)
        self.r.refresh_from_db(); token = accords.jeton(self.r)
        self.a.fin = date(2026, 6, 1); self.a.save(update_fields=['fin'])
        with self.assertRaises(ValidationError): self.prolonger(self.r, date(2026, 3, 1), attendu=token)
        for invalide in ['invalide', accords.jeton(self.vide)]:
            with self.assertRaises(ValidationError): self.prolonger(self.r, date(2026, 3, 1), attendu=invalide)

    def test_aucun_droit_implicite_et_refus_get_post_service(self):
        self.u.user_permissions.remove(Permission.objects.get(content_type__app_label='personnes', codename='prolonger_accordrepas'))
        self.u = type(self.u).objects.get(pk=self.u.pk)
        url = reverse('suivi:prolonger_accord', args=['repas', self.r.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, {'fin': '2026-04-01', 'motif': 'Fictif', 'attendu': accords.jeton(self.r), 'confirmer': True}).status_code, 403)
        with self.assertRaises(PermissionDenied): self.prolonger(self.r, date(2026, 3, 1))
        page = self.client.get(reverse('suivi:accompagnement', args=[self.a.pk]))
        self.assertNotContains(page, url)
        compte = get_user_model().objects.create_user('sans-droits-fictif')
        self.assertFalse(compte.has_perm('personnes.prolonger_accordrepas'))
        call_command('autoriser_bd3', compte.username, stdout=StringIO())
        compte = type(compte).objects.get(pk=compte.pk)
        self.assertTrue(compte.has_perm('personnes.prolonger_accordrepas'))
        self.assertFalse(compte.has_perm('personnes.view_personne'))
        self.assertFalse(compte.has_perm('personnes.delete_accordrepas'))
        self.assertFalse(compte.is_staff)

    def test_http_retour_dossier_confirmation_et_erreur(self):
        dossier = reverse('suivi:accompagnement', args=[self.a.pk])
        page = self.client.get(dossier, {'repas': self.r.pk, 'sejour': self.s.pk})
        token_dossier = page.context['contexte_dossier']; retour = page.context['retour_dossier']
        url = reverse('suivi:prolonger_accord', args=['repas', self.r.pk])
        valeurs = {'contexte_dossier': token_dossier, 'fin': '2026-03-01', 'motif': 'Décision fictive', 'attendu': accords.jeton(self.r)}
        page = self.client.post(url, valeurs)
        self.assertContains(page, 'Annuler et revenir')
        self.assertFalse(EvolutionAccord.objects.exists())
        valeurs['confirmer'] = True
        self.assertRedirects(self.client.post(url, valeurs), retour)
        self.assertEqual(self.client.get(retour).context['selection_repas'].pk, self.r.pk)
        # Replayed POST is an error and retains the return and the target.
        self.assertContains(self.client.post(url, valeurs), retour.replace('&', '&amp;'))
        self.assertEqual(EvolutionAccord.objects.count(), 1)

    def test_http_annulation_historique_et_refus_anciennes_urls(self):
        token = accords.jeton(self.r)
        url = reverse('suivi:annuler_accord', args=['repas', self.r.pk])
        self.assertRedirects(self.client.post(url, {'attendu': token, 'confirmer': True, 'motif': 'Erreur fictive'}),
            reverse('suivi:accord_repas', args=[self.r.pk]))
        page = self.client.get(reverse('suivi:accord_repas', args=[self.r.pk]))
        self.assertContains(page, 'Erreur fictive')
        self.assertContains(page, 'Accord annulé')
        self.assertNotContains(page, 'Enregistrer une distribution')
        for route, args in [('distribuer_repas', [self.r.pk]), ('corriger_saisie', ['accordrepas', self.r.pk])]:
            self.assertEqual(self.client.get(reverse('suivi:' + route, args=args)).status_code, 409)
        self.assertContains(self.client.get(reverse('suivi:accompagnement', args=[self.a.pk]), {'repas': self.r.pk}), 'Annulé')
        page = self.client.get(reverse('suivi:jour'), {'date': '2026-01-05'})
        self.assertFalse(page.context['lignes'])
        page = self.client.get(reverse('suivi:resume', args=[self.a.pk]))
        self.assertNotContains(page, 'Déjeuner')

    def test_resume_et_rapports_realisations_inchanges_apres_prolongation(self):
        repas.distribuer(self.u, self.r, self.p, date(2026, 1, 5), 1)
        from .statistiques import ventilation_repas
        avant = ventilation_repas(date(2026, 1, 1), date(2026, 2, 1))
        self.prolonger(self.r, date(2026, 4, 1))
        self.assertEqual(ventilation_repas(date(2026, 1, 1), date(2026, 2, 1)), avant)
        self.assertEqual(RepasDistribue.objects.count(), 1)
        self.assertEqual(self.r.operations.filter(action='distribue').count(), 1)
        self.assertContains(self.client.get(reverse('suivi:resume', args=[self.a.pk])), 'avril')

    def test_contraintes_journal_et_annulation_coherente(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            EvolutionAccord.objects.create(action='annulation', motif='Erreur', auteur=self.u)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AccordRepas.objects.filter(pk=self.r.pk).update(motif_annulation='Erreur seule')

    def test_correction_du_suivi_ignore_accord_annule_sans_realisation(self):
        self.annuler(self.r)
        # Historical agreement is preserved, but no longer constrains an active period.
        autre = suivi.ouvrir(self.u, self.m, [self.p], date(2026, 1, 1))
        r = repas.accorder(self.u, autre, [self.p], date(2026, 1, 1), None, 'diner')
        self.annuler(r)
        corrections.periode(self.u, autre, date(2026, 1, 2), None, 'Début fictif rectifié', corrections.jeton(autre))
        r.refresh_from_db()
        self.assertEqual(r.debut, date(2026, 1, 1))


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import sleep
from django.db import connections, close_old_connections, OperationalError
from django.test import TransactionTestCase


class ConcurrenceAccordsBD3(Donnees, TransactionTestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        call_command('autoriser_bd3', self.u.username, stdout=StringIO())
        self.u = type(self.u).objects.get(pk=self.u.pk)
        self.r = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), date(2026, 2, 1), 'dejeuner')
        self.token = accords.jeton(self.r)

    def parallele(self, fonctions):
        depart = Barrier(2)
        def lancer(i):
            close_old_connections()
            try:
                u = get_user_model().objects.get(pk=self.u.pk)
                depart.wait(10)
                for tentative in range(6):
                    try:
                        fonctions[i](u)
                        return True, ''
                    except ValidationError as erreur:
                        return False, str(erreur)
                    except OperationalError as erreur:
                        if connections['default'].vendor != 'sqlite' or 'locked' not in str(erreur).lower() or tentative == 5:
                            raise
                        sleep(.01 * (tentative + 1))
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(lancer, [0, 1]))

    def test_deux_prolongations_un_seul_journal(self):
        resultats = self.parallele([
            lambda u: accords.prolonger(u, self.r, date(2026, 3, 1), 'Décision fictive', self.token),
            lambda u: accords.prolonger(u, self.r, date(2026, 4, 1), 'Autre décision fictive', self.token)])
        self.assertEqual(sum(ok for ok, _ in resultats), 1, resultats)
        self.assertEqual(EvolutionAccord.objects.count(), 1)
        self.assertFalse(RepasDistribue.objects.exists())

    def test_annulation_contre_distribution_aucun_orphelin(self):
        resultats = self.parallele([
            lambda u: accords.annuler(u, self.r, 'Saisie fictive erronée', self.token),
            lambda u: repas.distribuer(u, self.r, self.p, date(2026, 1, 5), 1)])
        self.assertEqual(sum(ok for ok, _ in resultats), 1, resultats)
        self.r.refresh_from_db()
        self.assertEqual(self.r.annule_le is not None, not RepasDistribue.objects.exists())
        self.assertEqual(EvolutionAccord.objects.count(), int(self.r.annule_le is not None))

    def test_annulation_contre_admission_meme_verrou_menage(self):
        vide = h.accorder(self.u, self.a, [self.p], date(2026, 1, 1), date(2026, 2, 1))
        token = accords.jeton(vide)
        resultats = self.parallele([
            lambda u: accords.annuler(u, vide, 'Saisie fictive erronée', token),
            lambda u: h.admettre_individuellement(u, vide, [self.p], date(2026, 1, 5))])
        self.assertEqual(sum(ok for ok, _ in resultats), 1, resultats)
        vide.refresh_from_db()
        self.assertEqual(vide.annule_le is not None, not vide.sejours.exists())

    def test_deux_annulations_un_seul_journal(self):
        resultats = self.parallele([
            lambda u: accords.annuler(u, self.r, 'Saisie fictive erronée', self.token),
            lambda u: accords.annuler(u, self.r, 'Même erreur fictive', self.token)])
        self.assertEqual(sum(ok for ok, _ in resultats), 1, resultats)
        self.assertEqual(EvolutionAccord.objects.count(), 1)


class RepriseAccordsBD3(Donnees, TransactionTestCase):
    def test_zip_restaure_decisions_annulation_et_identites(self):
        from django.db import connection
        if connection.vendor != 'sqlite':
            self.skipTest('Paquet natif SQLite ; PostgreSQL possède une procédure distincte.')
        from contextlib import closing
        from pathlib import Path
        import sqlite3
        from tempfile import TemporaryDirectory
        from django.test import override_settings
        from pas_a_pas_accompagnement.paquets import PROFIL
        self.preparer()
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        call_command('autoriser_bd3', self.u.username, stdout=StringIO())
        self.u = type(self.u).objects.get(pk=self.u.pk)
        r = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), date(2026, 2, 1), 'dejeuner')
        r = accords.prolonger(self.u, r, date(2026, 3, 1), 'Décision fictive conservée', accords.jeton(r))
        accords.annuler(self.u, r, 'Saisie fictive annulée', accords.jeton(r))
        with TemporaryDirectory() as temporaire:
            racine = Path(temporaire)
            source = racine / 'source'; source.mkdir()
            (source / 'secret-key').write_text('cle-fictive')
            with closing(sqlite3.connect(source / PROFIL.base)) as db:
                connection.connection.backup(db)
            archive = racine / 'reprise.zip'
            destination = racine / 'restauree'
            with override_settings(LOCAL_DIR=source):
                call_command('sauvegarder_paquet', str(archive), stdout=StringIO())
                call_command('restaurer_copie', str(archive), str(destination), stdout=StringIO())
            with closing(sqlite3.connect(destination / PROFIL.base)) as db:
                self.assertEqual(db.execute('SELECT action, motif FROM personnes_evolutionaccord ORDER BY id').fetchall(),
                    [('prolongation', 'Décision fictive conservée'), ('annulation', 'Saisie fictive annulée')])
                valeur = db.execute('SELECT fin, annule_le, motif_annulation FROM personnes_accordrepas').fetchone()
                self.assertEqual(valeur[0], '2026-03-01')
                self.assertIsNotNone(valeur[1])
                self.assertEqual(valeur[2], 'Saisie fictive annulée')
                self.assertEqual(db.execute('SELECT id FROM personnes_personne').fetchone()[0], self.p.pk.hex)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM personnes_operationrepas').fetchone()[0], 1)
