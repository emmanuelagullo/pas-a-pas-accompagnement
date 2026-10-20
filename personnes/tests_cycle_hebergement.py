"""Recette métier du cycle d'hébergement : périodes [début, fin[ et historique."""
from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from . import hebergement as h
from .models import Absence, Affectation, OperationHebergement, Sejour
from .tests_hebergement import Donnees


class CycleHebergement(Donnees, TestCase):
    def setUp(self):
        self.preparer()

    def test_admission_changement_de_lieu_absence_et_sortie(self):
        """Les périodes adjacentes sont autorisées et la sortie ferme les périodes ouvertes."""
        premier = h.ajouter_periode(self.u, self.s, date(2026, 1, 3), None, self.lieu)
        h.terminer_periode(self.u, premier, date(2026, 1, 10))
        second_lieu = h.creer_lieu(self.u, 'Hébergement partenaire', 'Partenaire fictif')
        second = h.ajouter_periode(self.u, self.s, date(2026, 1, 10), None, second_lieu)
        absence = h.ajouter_periode(self.u, self.s, date(2026, 1, 12), None, absence=True)

        h.sortir(self.u, self.s, date(2026, 1, 20))
        self.s.refresh_from_db()
        premier.refresh_from_db()
        second.refresh_from_db()
        absence.refresh_from_db()
        self.assertEqual(self.s.fin, date(2026, 1, 20))
        self.assertEqual((premier.fin, second.fin, absence.fin),
                         (date(2026, 1, 10), date(2026, 1, 20), date(2026, 1, 20)))
        self.assertEqual(list(self.s.affectations.values_list('lieu_id', flat=True)),
                         [self.lieu.pk, second_lieu.pk])
        self.assertEqual(list(OperationHebergement.objects.filter(sejour=self.s)
                             .values_list('action', flat=True)), [
            'Admission effective', 'Affectation enregistrée', 'Affectation close',
            'Affectation enregistrée', 'Absence enregistrée',
            'Affectation close à la sortie', 'Absence close à la sortie', 'Sortie effective',
        ])

    def test_sortie_anterieure_a_une_absence_ne_change_rien(self):
        affectation = h.ajouter_periode(self.u, self.s, date(2026, 1, 3), None, self.lieu)
        absence = h.ajouter_periode(self.u, self.s, date(2026, 1, 12), date(2026, 1, 15), absence=True)
        operations_avant = list(OperationHebergement.objects.values_list('pk', flat=True))
        with self.assertRaises(ValidationError):
            h.sortir(self.u, self.s, date(2026, 1, 10))
        self.s.refresh_from_db()
        affectation.refresh_from_db()
        absence.refresh_from_db()
        self.assertIsNone(self.s.fin)
        self.assertIsNone(affectation.fin)
        self.assertEqual(absence.fin, date(2026, 1, 15))
        self.assertEqual(list(OperationHebergement.objects.values_list('pk', flat=True)), operations_avant)

    def test_formulaires_get_sans_ecriture_et_post_sortie(self):
        self.client.force_login(self.u)
        routes = ('admettre', 'affecter', 'absence', 'sortir')
        for nom in routes:
            cible = self.accord.pk if nom == 'admettre' else self.s.pk
            self.assertEqual(self.client.get(reverse('suivi:' + nom, args=[cible])).status_code, 200)
        self.assertEqual(Sejour.objects.count(), 1)
        self.assertFalse(Affectation.objects.exists())
        self.assertFalse(Absence.objects.exists())
        self.assertEqual(OperationHebergement.objects.filter(sejour=self.s).count(), 1)
        self.assertEqual(self.client.post(reverse('suivi:affecter', args=[self.s.pk]), {
            'debut': '2026-01-03', 'fin': '', 'lieu': self.lieu.pk,
        }).status_code, 302)
        self.assertEqual(self.client.post(reverse('suivi:absence', args=[self.s.pk]), {
            'debut': '2026-01-12', 'fin': '',
        }).status_code, 302)
        self.assertEqual(self.client.post(reverse('suivi:sortir', args=[self.s.pk]), {
            'fin': '2026-01-20',
        }).status_code, 302)
        self.s.refresh_from_db()
        self.assertEqual(self.s.fin, date(2026, 1, 20))
        self.assertEqual(self.s.affectations.get().fin, self.s.fin)
        self.assertEqual(self.s.absences.get().fin, self.s.fin)
