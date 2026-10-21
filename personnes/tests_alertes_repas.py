from datetime import date
from django.test import TestCase
from django.urls import reverse
from . import tests_jour, repas, statistiques
from .models import RepasDistribue


class AlertesRepasTests(TestCase):
    def setUp(self):
        tests_jour.JourTests.setUp(self)
        self.autre = repas.accorder(self.u, self.a, [self.p], date(2026,1,1), None, 'dejeuner')

    def test_cumul_averti_sans_interdiction_globale(self):
        premiere = repas.distribuer(self.u, self.accord, self.p, date(2026,1,3), 2)
        repas.distribuer(self.u, self.autre, self.p, date(2026,1,3), 1)
        page = self.client.get(reverse('suivi:accord_repas', args=[self.accord.pk]))
        self.assertContains(page, 'quantité supérieure à un')
        self.assertContains(page, 'plusieurs distributions pour le même service')
        self.assertEqual(statistiques.bilan(date(2026,1,3), date(2026,1,4))['repas_distribues'], 3)
        repas.annuler(self.u, premiere, 'Erreur fictive')
        page = self.client.get(reverse('suivi:accord_repas', args=[self.autre.pk]))
        self.assertNotContains(page, 'plusieurs distributions pour le même service')

    def test_service_ou_date_differents_ne_sont_pas_des_cumuls(self):
        repas.distribuer(self.u, self.autre, self.p, date(2026,1,4), 1)
        diner = repas.accorder(self.u, self.a, [self.p], date(2026,1,1), None, 'diner')
        repas.distribuer(self.u, diner, self.p, date(2026,1,3), 1)
        r = repas.distribuer(self.u, self.accord, self.p, date(2026,1,3), 1)
        self.assertEqual(repas.avertissements([r]), [])

    def test_lot_signale_accords_et_distributions_multiples(self):
        self.assertContains(self.client.get(self.url), 'Plusieurs accords actifs')
        donnees = tests_jour.JourTests.donnees(self)
        donnees.update({'repas-TOTAL_FORMS':'2', 'repas-INITIAL_FORMS':'2',
            'repas-1-accord':str(self.autre.pk), 'repas-1-beneficiaire':str(self.p.pk), 'repas-1-quantite':'1'})
        page = self.client.post(self.url, donnees, follow=True)
        self.assertEqual(RepasDistribue.objects.count(), 2)
        self.assertContains(page, 'plusieurs distributions pour le même service')

    def test_pas_dexposition_sans_droits(self):
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(reverse('suivi:accord_repas', args=[self.accord.pk])).status_code, 403)
        self.assertEqual(self.client.get(self.url).status_code, 403)
