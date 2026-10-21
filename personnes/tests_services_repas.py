from datetime import date
from unittest.mock import patch
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from . import tests_navigation, repas
from .models import AccordRepas, RepasDistribue, OperationRepas


class ServicesRepasTests(TestCase):
    def setUp(self):
        tests_navigation.NavigationTests.setUp(self)

    def accorder(self, services=('dejeuner', 'diner'), attendu=None):
        self.a.refresh_from_db()
        return repas.accorder_services(self.u, self.a, [self.p], date(2026,1,1), date(2026,2,1),
            services, attendu or repas.jeton_services(self.a))

    def test_services_distincts_sans_distribution(self):
        accords = self.accorder()
        self.assertEqual([a.service for a in accords], ['dejeuner', 'diner'])
        self.assertTrue(all(a.beneficiaires.get() == self.p for a in accords))
        self.assertEqual(OperationRepas.objects.count(), 2)
        self.assertFalse(RepasDistribue.objects.exists())

    def test_echec_second_service_et_doublons_annulent_tout(self):
        original = repas.accorder
        appels = 0
        def creer(*args, **kwargs):
            nonlocal appels
            appels += 1
            if appels == 2:
                raise ValidationError('Échec fictif')
            return original(*args, **kwargs)
        with patch('personnes.repas.accorder', side_effect=creer):
            with self.assertRaises(ValidationError): self.accorder()
        for services in [(), ('diner', 'diner'), ('inconnu',)]:
            with self.assertRaises(ValidationError): self.accorder(services)
        self.assertFalse(AccordRepas.objects.exists())
        self.assertFalse(OperationRepas.objects.exists())

    def test_perime_et_parcours_http(self):
        url = reverse('suivi:accorder_services_repas', args=[self.a.pk])
        self.assertContains(self.client.get(url), 'aucune distribution automatique')
        attendu = repas.jeton_services(self.a)
        donnees = {'beneficiaires': [str(self.p.pk)], 'debut': '2026-01-01', 'fin': '2026-02-01',
            'services': ['dejeuner', 'diner'], 'prestataire': '', 'attendu': attendu}
        self.assertRedirects(self.client.post(url, donnees), reverse('suivi:accompagnement', args=[self.a.pk]))
        self.assertContains(self.client.post(url, donnees), 'Rechargez le formulaire')
        self.assertEqual(AccordRepas.objects.count(), 2)
        self.u.user_permissions.clear()
        self.assertEqual(self.client.post(url, donnees).status_code, 403)


class ConcurrenceServicesRepas(TransactionTestCase):
    def test_double_envoi_ne_cree_quun_lot(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections, OperationalError
        ServicesRepasTests.setUp(self)
        attendu = repas.jeton_services(self.a)
        depart = Barrier(2)
        def envoyer(_):
            close_old_connections()
            try:
                acteur = type(self.u).objects.get(pk=self.u.pk)
                acteur.get_all_permissions()
                depart.wait(10)
                try:
                    repas.accorder_services(acteur, self.a, [self.p], date(2026,1,1), None,
                        ['dejeuner', 'diner'], attendu)
                    return True
                except (ValidationError, OperationalError): return False
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultats = list(pool.map(envoyer, range(2)))
        self.assertEqual(sum(resultats), 1)
        self.assertEqual(AccordRepas.objects.count(), 2)
