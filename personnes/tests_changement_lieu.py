from datetime import date
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from . import corrections as c, hebergement as h
from .models import Affectation, OperationHebergement
from .tests_hebergement import Donnees


class ChangementLieuTests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        self.premiere = h.ajouter_periode(self.u, self.s, self.s.debut, None, self.lieu)
        self.autre = h.creer_lieu(self.u, 'Autre chambre fictive')

    def changer(self, debut=date(2026,1,10)):
        return h.changer_lieu(self.u, self.premiere, debut, self.autre, c.jeton(self.premiere))

    def test_changement_adjacent_et_rejeu_refuse(self):
        attendu = c.jeton(self.premiere)
        suivante = self.changer()
        self.premiere.refresh_from_db()
        self.assertEqual(self.premiere.fin, suivante.debut)
        self.assertIsNone(suivante.fin)
        self.assertEqual(suivante.lieu, self.autre)
        with self.assertRaises(ValidationError):
            h.changer_lieu(self.u, self.premiere, date(2026,1,11), self.lieu, attendu)
        self.assertEqual(Affectation.objects.count(), 2)

    def test_echec_seconde_ecriture_annule_cloture_et_journal(self):
        # Une période ancienne erronée peut exister dans une base importée.
        Affectation.objects.create(sejour=self.s, lieu=self.autre, debut=date(2026,1,12))
        avant = OperationHebergement.objects.count()
        with self.assertRaises(ValidationError): self.changer()
        self.premiere.refresh_from_db()
        self.assertIsNone(self.premiere.fin)
        self.assertEqual(OperationHebergement.objects.count(), avant)

    def test_date_et_droits(self):
        with self.assertRaises(ValidationError): self.changer(self.s.debut)
        self.u.user_permissions.clear()
        acteur = type(self.u).objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):
            h.changer_lieu(acteur, self.premiere, date(2026,1,10), self.autre, c.jeton(self.premiere))
        self.premiere.refresh_from_db()
        self.assertIsNone(self.premiere.fin)

    def test_parcours_http_et_jeton(self):
        self.client.force_login(self.u)
        url = reverse('suivi:changer_lieu', args=[self.premiere.pk])
        self.assertContains(self.client.get(url), 'name="attendu"')
        response = self.client.post(url, {'debut': '2026-01-10', 'lieu': str(self.autre.pk),
                                         'attendu': c.jeton(self.premiere)})
        self.assertRedirects(response, reverse('suivi:accord_hebergement', args=[self.accord.pk]))
        self.assertEqual(Affectation.objects.count(), 2)
