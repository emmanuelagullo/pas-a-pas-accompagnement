from datetime import date
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from . import tests_hebergement


class DatesServiceTests(TestCase):
    def setUp(self):
        tests_hebergement.Donnees.preparer(self)
        self.client.force_login(self.u)

    def test_jour_consulte_prefill_et_annulation_sans_ecriture(self):
        for route, champ in [('affecter', 'debut'), ('absence', 'debut'), ('sortir', 'fin')]:
            url = reverse('suivi:'+route, args=[self.s.pk])
            page = self.client.get(url, {'retour': 'jour', 'date_service': '2026-01-10'})
            self.assertEqual(page.context['form'].initial[champ], date(2026,1,10))
            self.assertContains(page, reverse('suivi:jour')+'?date=2026-01-10')
        self.assertFalse(self.s.affectations.exists())
        self.assertFalse(self.s.absences.exists())
        self.s.refresh_from_db()
        self.assertIsNone(self.s.fin)

    def test_pas_de_cloture_a_duree_nulle_et_parametres_bornes(self):
        url = reverse('suivi:sortir', args=[self.s.pk])
        page = self.client.get(url, {'retour': 'jour', 'date_service': '2026-01-03'})
        self.assertNotIn('fin', page.context['form'].initial)
        with patch('personnes.vues_hebergement.timezone.localdate', return_value=date(2026,1,20)):
            for parametres in [{'retour':'jour', 'date_service':'invalide'},
                               {'retour':'https://example.test/', 'date_service':'2026-01-10'}]:
                page = self.client.get(url, parametres)
                self.assertEqual(page.context['form'].initial['fin'], date(2026,1,20))
