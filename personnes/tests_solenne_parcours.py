"""L1 : confirmations explicites, refus sans écritures et gestes quotidiens BD."""
from datetime import date
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from . import bd6, hebergement, ouverture_prise, suivi
from .models import Personne, Menage, Accompagnement, Appartenance, EvolutionPriseEnCharge
from .tests_hebergement import Donnees


class ParcoursSolenneTests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        call_command('autoriser_bd6', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        self.client.force_login(self.u)
        self.prise = reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk])

    def test_premiere_prise_individuelle_cree_explicitement_menage_sans_prestation(self):
        p = Personne.objects.create(designation='Accueil fictif sans ménage', cree_par=self.u)
        url = reverse('dossiers:nouvelle_prise', args=['personne', p.pk])
        page = self.client.get(url, {'q': 'Accueil', 'mode': 'personne', 'page': '2'})
        self.assertContains(page, 'Créer un ménage avec cette personne')
        self.assertFalse(p.appartenances.exists())
        data = {'beneficiaires': [p.pk], 'debut': '2026-02-01', 'fin_prevue': '',
            'rattachement': 'nouveau', 'libelle_menage': 'Ménage Accueil fictif',
            'attendu': page.context['form'].initial['attendu']}
        with patch('personnes.suivi.ouvrir', side_effect=ValidationError('Échec fictif')):
            self.assertEqual(self.client.post(url, data).status_code, 409)
        self.assertFalse(p.appartenances.exists())
        page = self.client.post(url + '?q=Accueil&mode=personne&page=2', data)
        self.assertEqual(page.status_code, 302)
        self.assertIn('q=Accueil', page.url)
        self.assertIn('page=2', page.url)
        a = p.accompagnements.get()
        self.assertEqual(a.menage.libelle, data['libelle_menage'])
        self.assertEqual(list(a.beneficiaires.all()), [p])
        self.assertEqual(a.menage.appartenances.get().debut, date(2026, 2, 1))
        self.assertFalse(a.accords_hebergement.exists())
        self.assertEqual(self.client.post(url, data).status_code, 409)
        self.assertEqual(p.accompagnements.count(), 1)
        self.assertEqual(p.appartenances.count(), 1)

    def test_rattachement_existant_ne_cree_pas_menage_et_refuse_etat_perime(self):
        token = ouverture_prise.jeton(self.p)
        a = ouverture_prise.ouvrir(self.u, self.p, [self.p], date(2026, 2, 1), None, token, menage=self.m)
        self.assertEqual(a.menage_id, self.m.pk)
        self.assertEqual(Menage.objects.count(), 1)
        with self.assertRaises(ValidationError):
            ouverture_prise.ouvrir(self.u, self.p, [self.p], date(2026, 2, 1), None, token, menage=self.m)
        autre = Personne.objects.create(designation='Autre fictive', cree_par=self.u)
        with self.assertRaises(ValidationError):
            ouverture_prise.ouvrir(self.u, autre, [autre], date(2026, 2, 1), None, token, menage=self.m)

    def test_creation_menage_sans_droit_et_champs_vides_refusee(self):
        p = Personne.objects.create(designation='Isolée fictive', cree_par=self.u)
        url = reverse('dossiers:nouvelle_prise', args=['personne', p.pk])
        token = ouverture_prise.jeton(p)
        self.assertContains(self.client.post(url, {'beneficiaires': [p.pk], 'debut': '2026-02-01',
            'rattachement': 'nouveau', 'libelle_menage': '', 'attendu': token}), 'Nommez le ménage')
        self.u.user_permissions.remove(Permission.objects.get(codename='add_menage'))
        u = get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):
            ouverture_prise.ouvrir(u, p, [p], date(2026, 2, 1), None, token,
                creer_menage=True, libelle_menage='Refus fictif')
        self.assertFalse(p.appartenances.exists())

    def test_correction_prevision_retrait_motif_et_journal_distincts(self):
        bd6.prolonger(self.u, self.a, date(2026, 7, 1), 'Prévision initiale fictive', bd6.jeton(self.a))
        token = bd6.jeton(self.a)
        bd6.corriger_prevision(self.u, self.a, date(2026, 6, 1), 'Mauvais mois fictif', token)
        self.a.refresh_from_db(); self.accord.refresh_from_db(); self.s.refresh_from_db()
        self.assertEqual(self.a.fin_prevue, date(2026, 6, 1))
        self.assertEqual(self.accord.fin, date(2026, 3, 1))
        self.assertIsNone(self.s.fin)
        self.assertIsNone(self.a.fin)
        self.assertEqual(EvolutionPriseEnCharge.objects.first().action, 'correction')
        with self.assertRaises(ValidationError):
            bd6.corriger_prevision(self.u, self.a, None, 'Fictif', token)
        for fin, motif in [(date(2026, 6, 1), 'Inchangée'), (self.a.debut, 'Mauvaise date')]:
            with self.assertRaises(ValidationError):
                bd6.corriger_prevision(self.u, self.a, fin, motif, bd6.jeton(self.a))
        bd6.corriger_prevision(self.u, self.a, None, '', bd6.jeton(self.a))
        self.assertEqual(EvolutionPriseEnCharge.objects.first().motif, '')
        self.a.refresh_from_db()
        self.assertIsNone(self.a.fin_prevue)
        self.assertIsNone(EvolutionPriseEnCharge.objects.first().nouvelle_fin)
        self.assertEqual(EvolutionPriseEnCharge.objects.count(), 3)

    def test_droit_correction_prevision_independant_et_retour_form3(self):
        url = reverse('dossiers:corriger_prevision', args=['menage', self.m.pk, self.a.pk])
        bd6.prolonger(self.u, self.a, date(2026, 7, 1), 'Fictif', bd6.jeton(self.a))
        page = self.client.post(url + '?q=Fictif&sejour=' + str(self.s.pk),
            {'fin_prevue': '2026-06-01', 'motif': 'Erreur fictive', 'attendu': bd6.jeton(self.a)})
        self.assertEqual(page.status_code, 302)
        self.assertIn('/prises/' + str(self.a.pk), page.url)
        self.assertIn('sejour=' + str(self.s.pk), page.url)
        self.u.user_permissions.remove(Permission.objects.get(codename='corriger_prevision_accompagnement'))
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_cloture_directe_refuse_sejour_ouvert_et_formulaire_perime(self):
        url = reverse('dossiers:clore_prise', args=['menage', self.m.pk, self.a.pk])
        self.assertContains(self.client.get(self.prise), 'Clôturer la prise')
        data = {'fin': '2026-02-01', 'attendu': bd6.jeton(self.a)}
        self.assertEqual(self.client.post(url, data).status_code, 409)
        hebergement.sortir(self.u, self.s, date(2026, 1, 15))
        # Le journal d'hébergement ne change pas nécessairement la révision
        # sociale ; une modification explicite de prévision, elle, le fait.
        data['attendu'] = bd6.jeton(self.a)
        bd6.prolonger(self.u, self.a, date(2026, 3, 1), 'Fictif', data['attendu'])
        self.assertEqual(self.client.post(url, data).status_code, 409)
        data['attendu'] = bd6.jeton(self.a)
        page = self.client.post(url + '?q=Fictif', data)
        self.assertEqual(page.status_code, 302)
        self.assertIn('q=Fictif', page.url)
        self.a.refresh_from_db()
        self.assertEqual(self.a.fin, date(2026, 2, 1))
        self.assertNotContains(self.client.get(self.prise), 'Clôturer la prise')

    def test_actions_du_jour_hors_details_et_retour_absence(self):
        hebergement.ajouter_periode(self.u, self.s, date(2026, 1, 3), None, self.lieu)
        page = self.client.get(self.prise)
        html = page.content.decode()
        self.assertLess(html.index('Changer de lieu'), html.index('Autres actions et informations'))
        self.assertLess(html.index('Enregistrer une absence'), html.index('Autres actions et informations'))
        hebergement.ajouter_periode(self.u, self.s, date(2026, 1, 12), None, absence=True)
        self.assertContains(self.client.get(self.prise), 'Enregistrer le retour d’absence')

    def test_lieu_actuel_dernier_connu_et_futur_non_affiche(self):
        hebergement.ajouter_periode(self.u, self.s, date(2026, 1, 3), date(2026, 1, 10), self.lieu)
        autre = hebergement.creer_lieu(self.u, 'Lieu suivant fictif')
        hebergement.ajouter_periode(self.u, self.s, date(2026, 1, 20), None, autre)
        self.s.lieux_dossier = list(self.s.affectations.select_related('lieu'))
        texte = bd6.resume_prestations(self.a, [self.s], [], date(2026, 1, 8), True)
        self.assertIn('Lieu actuel : Chambre fictive', texte)
        self.assertNotIn('Lieu suivant', texte)
        texte = bd6.resume_prestations(self.a, [self.s], [], date(2026, 1, 15), True)
        self.assertIn('Dernier lieu connu : Chambre fictive', texte)
        self.assertNotIn('Lieu suivant', texte)
        hebergement.sortir(self.u, self.s, date(2026, 1, 25))
        self.s.refresh_from_db()
        self.s.lieux_dossier = list(self.s.affectations.select_related('lieu'))
        texte = bd6.resume_prestations(self.a, [self.s], [], date(2026, 2, 1), True)
        self.assertIn('Dernier lieu connu : Lieu suivant fictif', texte)
        self.assertNotIn('Lieu actuel', texte)


class ConfirmationConcurrenteTests(Donnees, TransactionTestCase):
    def test_deux_ouvertures_ne_creent_quun_menage_et_une_prise(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections, OperationalError
        self.preparer()
        p = Personne.objects.create(designation='Concurrente fictive', cree_par=self.u)
        token = ouverture_prise.jeton(p)
        depart = Barrier(2)
        def ouvrir(_):
            close_old_connections()
            try:
                u = get_user_model().objects.get(pk=self.u.pk); u.get_all_permissions()
                personne = Personne.objects.get(pk=p.pk)
                depart.wait(timeout=10)
                try:
                    ouverture_prise.ouvrir(u, personne, [personne], date(2026, 2, 1), None,
                        token, creer_menage=True, libelle_menage='Concurrent fictif')
                    return True
                except (ValidationError, OperationalError):
                    return False
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultats = list(pool.map(ouvrir, range(2)))
        self.assertEqual(sum(resultats), 1, resultats)
        self.assertEqual(p.appartenances.count(), 1)
        self.assertEqual(p.accompagnements.count(), 1)
