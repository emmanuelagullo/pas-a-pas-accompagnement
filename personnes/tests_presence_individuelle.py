from datetime import date
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from . import hebergement as h, statistiques
from .models import Personne, Sejour
from .tests_hebergement import Donnees


class PresenceFamilialeTests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        self.enfant = Personne.objects.create(designation='Enfant fictif', cree_par=self.u)
        self.a.beneficiaires.add(self.enfant)
        self.accord.beneficiaires.add(self.enfant)
        # Le séjour historique du parent demeure distinct et fermé avant ce lot.
        h.sortir(self.u, self.s, date(2026,1,4))

    def admettre(self):
        sejours = h.admettre_individuellement(self.u, self.accord, [self.p, self.enfant], date(2026,1,5))
        return {s.beneficiaires.get().pk: s for s in sejours}

    def test_famille_admise_ensemble_sans_conversion_historique(self):
        sejours = self.admettre()
        self.assertEqual(len(sejours), 2)
        self.assertEqual(Sejour.objects.count(), 3)
        self.s.refresh_from_db()
        self.assertEqual(self.s.fin, date(2026,1,4))
        self.assertEqual(self.s.beneficiaires.count(), 1)
        self.assertEqual(statistiques.bilan(date(2026,1,5), date(2026,1,7))['nuitees_theoriques'], 4)

    def test_enfant_absent_parent_present(self):
        sejours = self.admettre()
        h.ajouter_periode(self.u, sejours[self.enfant.pk], date(2026,1,5), date(2026,1,6), absence=True)
        self.assertFalse(sejours[self.p.pk].absences.exists())
        self.assertEqual(statistiques.bilan(date(2026,1,5), date(2026,1,7))['nuits_hors_absences_declarees'], 3)

    def test_sorties_a_des_dates_differentes(self):
        sejours = self.admettre()
        h.sortir(self.u, sejours[self.enfant.pk], date(2026,1,6))
        sejours[self.p.pk].refresh_from_db()
        self.assertIsNone(sejours[self.p.pk].fin)
        self.assertEqual(statistiques.bilan(date(2026,1,5), date(2026,1,7))['nuitees_theoriques'], 3)

    def test_lieux_differents_et_ancien_collectif_preserve(self):
        sejours = self.admettre()
        autre = h.creer_lieu(self.u, 'Lieu enfant fictif')
        h.ajouter_periode(self.u, sejours[self.p.pk], date(2026,1,5), None, self.lieu)
        h.ajouter_periode(self.u, sejours[self.enfant.pk], date(2026,1,5), None, autre)
        ancien = h.admettre(self.u, self.accord, [self.p, self.enfant], date(2026,1,1))
        self.assertEqual(ancien.beneficiaires.count(), 2)
        h.ajouter_periode(self.u, ancien, date(2026,1,2), date(2026,1,3), absence=True)
        self.assertEqual(ancien.absences.count(), 1)

    def test_selection_invalide_ne_cree_rien(self):
        autre = Personne.objects.create(designation='Hors accord fictif', cree_par=self.u)
        with self.assertRaises(ValidationError):
            h.admettre_individuellement(self.u, self.accord, [self.p, autre], date(2026,1,5))
        self.assertEqual(Sejour.objects.count(), 1)

    def test_http_selection_collective_cree_deux_sejours(self):
        self.client.force_login(self.u)
        response = self.client.post(reverse('suivi:admettre', args=[self.accord.pk]),
            {'beneficiaires': [str(self.p.pk), str(self.enfant.pk)], 'debut': '2026-01-05'})
        self.assertRedirects(response, reverse('suivi:accord_hebergement', args=[self.accord.pk]))
        self.assertEqual(Sejour.objects.count(), 3)
