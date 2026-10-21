from datetime import date
from io import StringIO

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from . import corrections, hebergement as h
from .models import CorrectionPeriode, OperationHebergement
from .tests_hebergement import Donnees


class DepassementAccordTests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        self.u = type(self.u).objects.get(pk=self.u.pk)

    def test_mouvements_et_sortie_sans_prolonger_accord(self):
        affectation = h.ajouter_periode(self.u, self.s, date(2026,3,2), None, self.lieu)
        absence = h.ajouter_periode(self.u, self.s, date(2026,3,3), None, absence=True)
        h.terminer_periode(self.u, absence, date(2026,3,4))
        h.sortir(self.u, self.s, date(2026,3,5))
        affectation.refresh_from_db()
        self.accord.refresh_from_db()
        self.assertEqual(affectation.fin, date(2026,3,5))
        self.assertEqual(self.accord.fin, date(2026,3,1))
        self.client.force_login(self.u)
        self.assertContains(self.client.get(reverse('suivi:accord_hebergement', args=[self.accord.pk])),
                            'Les faits enregistrés ne prolongent pas')
        with self.assertRaises(ValidationError):
            h.admettre(self.u, self.accord, [self.p], date(2026,3,2))

    def test_correction_sortie_et_accord_avec_journal_et_jeton(self):
        h.sortir(self.u, self.s, date(2026,2,28))
        self.s.refresh_from_db()
        attendu = corrections.jeton(self.s)
        corrections.periode(self.u, self.s, self.s.debut, date(2026,3,5), 'Date réelle', attendu)
        with self.assertRaises(ValidationError):
            corrections.periode(self.u, self.s, self.s.debut, date(2026,3,6), 'Périmé', attendu)
        corrections.periode(self.u, self.accord, self.accord.debut, date(2026,2,15),
                            'Fin convenue rectifiée', corrections.jeton(self.accord))
        self.assertEqual(CorrectionPeriode.objects.count(), 2)
        self.assertEqual(OperationHebergement.objects.filter(action='Sortie effective').count(), 1)
        self.s.refresh_from_db()
        self.assertEqual(self.s.fin, date(2026,3,5))

    def test_suivi_clos_et_droits_restent_controles(self):
        self.a.fin = date(2026,3,2)
        self.a.save(update_fields=['fin'])
        with self.assertRaises(ValidationError):
            h.sortir(self.u, self.s, date(2026,3,3))
        self.s.refresh_from_db()
        self.assertIsNone(self.s.fin)
        self.u.user_permissions.clear()
        acteur = type(self.u).objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):
            h.sortir(acteur, self.s, date(2026,3,1))

    def test_retour_au_jour_conserve_date_sans_destination_libre(self):
        self.client.force_login(self.u)
        url = reverse('suivi:absence', args=[self.s.pk])
        page = self.client.get(url, {'retour': 'jour', 'date_service': '2026-03-03'})
        self.assertContains(page, 'name="date_service" value="2026-03-03"')
        response = self.client.post(url, {'debut': '2026-03-03', 'fin': '2026-03-04',
                                         'retour': 'jour', 'date_service': '2026-03-03'})
        self.assertRedirects(response, reverse('suivi:jour')+'?date=2026-03-03', fetch_redirect_response=False)
        response = self.client.post(url, {'debut': '2026-03-05', 'fin': '2026-03-06',
                                         'retour': 'https://example.test/', 'date_service': 'invalide'})
        self.assertRedirects(response, reverse('suivi:accord_hebergement', args=[self.accord.pk]))
