"""CHRS9 : suggestions réversibles, sans création de prestations au GET."""
from django.test import TestCase
from django.urls import reverse
from .tests_hebergement import Donnees
from .models import Sejour, Affectation, Absence


class SuggestionsHebergement(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        self.client.force_login(self.u)

    def test_admission_preselectionne_sans_creer(self):
        avant = Sejour.objects.count()
        reponse = self.client.get(reverse("suivi:admettre", args=[self.accord.pk]))
        self.assertEqual(reponse.status_code, 200)
        form = reponse.context["form"]
        self.assertIn(self.p.pk, form.initial["beneficiaires"])
        self.assertGreaterEqual(form.initial["debut"], self.accord.debut)
        self.assertEqual(Sejour.objects.count(), avant)

    def test_affectation_et_absence_sans_ecriture(self):
        for nom in ("affecter", "absence"):
            reponse = self.client.get(reverse("suivi:" + nom, args=[self.s.pk]))
            self.assertEqual(reponse.status_code, 200)
            self.assertGreaterEqual(reponse.context["form"].initial["debut"], self.s.debut)
        self.assertFalse(Affectation.objects.exists())
        self.assertFalse(Absence.objects.exists())

    def test_post_explicitement_saisi_prime_sur_suggestion(self):
        reponse = self.client.post(reverse("suivi:admettre", args=[self.accord.pk]),
            {"beneficiaires": [self.p.pk], "debut": "2026-01-05"})
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(Sejour.objects.filter(debut="2026-01-05").exists())
