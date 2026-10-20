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


class ArriveeProgressive(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        self.client.force_login(self.u)

    def test_creer_personne_puis_proposer_menage_sans_le_creer(self):
        from .models import Personne, Menage
        reponse = self.client.post(reverse("personnes:creer"), {"designation": "Accueil provisoire", "prenom": ""})
        personne = Personne.objects.get(designation="Accueil provisoire")
        self.assertRedirects(reponse, reverse("personnes:detail", args=[personne.pk]))
        fiche = self.client.get(reponse.url)
        self.assertContains(fiche, "Créer un ménage avec cette personne")
        formulaire = self.client.get(reverse("suivi:creer") + f"?personne={personne.pk}")
        self.assertEqual(formulaire.status_code, 200)
        self.assertIn(str(personne.pk), [str(p) for p in formulaire.context["form"].initial["personnes"]])
        self.assertFalse(Menage.objects.filter(libelle="Accueil provisoire").exists())

    def test_parametre_personne_invalide_ignore(self):
        reponse = self.client.get(reverse("suivi:creer") + "?personne=non-uuid")
        self.assertEqual(reponse.status_code, 200)
        self.assertNotIn("personnes", reponse.context["form"].initial)
