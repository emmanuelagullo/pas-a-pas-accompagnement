from datetime import date
from django.test import TestCase
from django.urls import reverse
from .tests_navigation import NavigationTests
from .models import Personne, Sejour, AccordHebergement, RepasDistribue
from . import repas
from .statistiques import bilan


class StatistiquesTests(TestCase):
    def setUp(self):
        NavigationTests.setUp(self)

    def test_periode_et_dedoublonnage(self):
        accord = AccordHebergement.objects.create(accompagnement=self.a, debut=date(2026, 1, 1), cree_par=self.u)
        accord.beneficiaires.add(self.p)
        for debut, fin in [(date(2026, 1, 1), date(2026, 1, 4)),
                           (date(2026, 1, 3), date(2026, 1, 6))]:
            sejour = Sejour.objects.create(accord=accord, debut=debut, fin=fin, cree_par=self.u)
            sejour.beneficiaires.add(self.p)
        resultat = bilan(date(2026, 1, 2), date(2026, 1, 5))
        self.assertEqual(resultat['personnes_avec_sejour'], 1)
        self.assertEqual(resultat['sejours'], 2)
        # Deux séjours contribuent chacun deux nuits sur [2, 5[.
        # La nuit commune du 3 janvier est comptée deux fois par définition.
        self.assertEqual(resultat['nuitees_theoriques'], 4)
        self.assertEqual(resultat['admissions'], 1)
        self.assertEqual(resultat['sorties'], 1)
        self.assertEqual(resultat['menages_accompagnes'], 1)

    def test_distributions_non_annulees_et_frontiere(self):
        accord = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), None, 'dejeuner')
        RepasDistribue.objects.create(accord=accord, beneficiaire=self.p, date=date(2026, 1, 2), quantite=2, cree_par=self.u)
        self.assertEqual(bilan(date(2026, 1, 2), date(2026, 1, 3))['repas_distribues'], 2)
        self.assertEqual(bilan(date(2026, 1, 3), date(2026, 1, 4))['repas_distribues'], 0)

    def test_consultation_droits_et_validation(self):
        url = reverse('statistiques')
        self.assertEqual(self.client.get(url, {'debut': '2026-01-02', 'fin': '2026-01-02'}).status_code, 200)
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_periode_invalide(self):
        with self.assertRaises(ValueError):
            bilan(date(2026, 1, 2), date(2026, 1, 2))

    def test_nuits_distinctes_et_absences(self):
        from .models import Absence
        accord = AccordHebergement.objects.create(
            accompagnement=self.a, debut=date(2026, 1, 1), cree_par=self.u)
        accord.beneficiaires.add(self.p)
        for debut, fin in [(date(2026, 1, 1), date(2026, 1, 4)),
                           (date(2026, 1, 3), date(2026, 1, 6))]:
            sejour = Sejour.objects.create(accord=accord, debut=debut, fin=fin, cree_par=self.u)
            sejour.beneficiaires.add(self.p)
            if debut.day == 1:
                Absence.objects.create(sejour=sejour, debut=date(2026, 1, 2),
                                       fin=date(2026, 1, 3))
        resultat = bilan(date(2026, 1, 2), date(2026, 1, 5))
        self.assertEqual(resultat['nuitees_theoriques'], 4)
        self.assertEqual(resultat['nuits_distinctes'], 3)
        self.assertEqual(resultat['nuits_hors_absences_declarees'], 2)

    def test_export_csv_et_permissions(self):
        url = reverse('statistiques')
        params = {'debut': '2026-01-02', 'fin': '2026-01-05', 'format': 'csv'}
        reponse = self.client.get(url, params)
        self.assertEqual(reponse.status_code, 200)
        self.assertIn('text/csv', reponse['Content-Type'])
        self.assertIn(b'nuits_distinctes', reponse.content)
        self.assertIn(b'2026-01-02,2026-01-05', reponse.content)
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(url, params).status_code, 403)
