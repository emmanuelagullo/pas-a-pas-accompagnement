from datetime import date
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase
from django.urls import reverse
from . import tests_hebergement, hebergement as h, hebergement_collectif as service
from .models import Personne, OperationHebergement


class SelectionTests(TestCase):
    def setUp(self):
        tests_hebergement.Donnees.preparer(self)
        self.p2 = Personne.objects.create(designation='Enfant fictif', cree_par=self.u)
        self.a.beneficiaires.add(self.p2)
        self.accord.beneficiaires.add(self.p2)
        self.s2 = h.admettre(self.u, self.accord, [self.p2], date(2026,1,3))

    def appliquer(self, action, jour, selection=None, attendu=None):
        sejours = list(service.sejours_ouverts(self.accord))
        return service.appliquer(self.u, self.accord, selection or sejours, action, date(2026,1,jour),
            self.lieu, attendu or service.jeton(self.accord, sejours))

    def test_selection_absence_retour_et_sortie_partielle(self):
        self.appliquer('affecter', 3)
        self.appliquer('absence', 5)
        self.appliquer('retour', 7)
        self.appliquer('sortie', 10, [self.s2])
        self.s.refresh_from_db(); self.s2.refresh_from_db()
        self.assertIsNone(self.s.fin)
        self.assertEqual(self.s2.fin, date(2026,1,10))
        self.assertEqual(self.s.absences.get().fin, date(2026,1,7))
        self.assertEqual(self.s.affectations.get().fin, None)

    def test_echec_deuxieme_sejour_annule_tout_le_lot(self):
        h.ajouter_periode(self.u, self.s2, date(2026,1,4), None, absence=True)
        avant = OperationHebergement.objects.count()
        with self.assertRaises(ValidationError): self.appliquer('absence', 5)
        self.assertFalse(self.s.absences.exists())
        self.assertEqual(OperationHebergement.objects.count(), avant)

    def test_refus_perime_et_droits(self):
        attendu = service.jeton(self.accord, service.sejours_ouverts(self.accord))
        h.ajouter_periode(self.u, self.s, date(2026,1,3), None, self.lieu)
        with self.assertRaises(ValidationError): self.appliquer('absence', 5, attendu=attendu)
        self.u.user_permissions.clear()
        self.u = type(self.u).objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied): self.appliquer('sortie', 10)

    def test_http_selection_sans_action_implicite(self):
        self.client.force_login(self.u)
        url = reverse('suivi:selection_sejours', args=[self.accord.pk])
        self.assertContains(self.client.get(url), 'Enfant fictif')
        self.assertFalse(self.s.absences.exists())
        response = self.client.post(url, {'sejours': [str(self.s2.pk)], 'action': 'absence',
            'date': '2026-01-05', 'lieu': '', 'attendu': service.jeton(self.accord, service.sejours_ouverts(self.accord))})
        self.assertRedirects(response, reverse('suivi:accord_hebergement', args=[self.accord.pk]))
        self.assertTrue(self.s2.absences.exists())
        self.assertFalse(self.s.absences.exists())


from django.test import TransactionTestCase


class ConcurrenceSelection(TransactionTestCase):
    def test_deux_lots_ne_creent_pas_deux_absences(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections, OperationalError
        SelectionTests.setUp(self)
        selection = list(service.sejours_ouverts(self.accord))
        attendu = service.jeton(self.accord, selection)
        barriere = Barrier(2)
        def ecrire(_):
            close_old_connections()
            try:
                acteur = type(self.u).objects.get(pk=self.u.pk)
                acteur.get_all_permissions()
                barriere.wait(10)
                try:
                    service.appliquer(acteur, self.accord, selection, 'absence', date(2026,1,5), None, attendu)
                    return True
                except (ValidationError, OperationalError):
                    return False
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultats = list(pool.map(ecrire, range(2)))
        self.assertEqual(sum(resultats), 1)
        self.assertEqual(self.s.absences.count(), 1)
        self.assertEqual(self.s2.absences.count(), 1)
