from io import StringIO
from unittest.mock import patch
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.test import Client, TestCase
from django.urls import reverse

from .models import Personne


class ParcoursTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.compte = get_user_model().objects.create_user(username="essai", password="mot-de-passe-fictif-47")
        cls.personne = Personne.objects.create(designation="Personne fictive A", cree_par=cls.compte)

    def droits(self, *codes):
        self.compte.user_permissions.set(Permission.objects.filter(
            content_type__app_label="personnes", codename__in=codes))
        self.client.force_login(self.compte)

    def test_connexion_necessaire_sur_tous_les_ecrans(self):
        for url in [reverse("accueil"), reverse("personnes:liste"),
                    reverse("personnes:creer"), reverse("personnes:detail", args=[self.personne.pk])]:
            with self.subTest(url=url):
                reponse = self.client.get(url)
                self.assertEqual(reponse.status_code, 302)
                self.assertTrue(reponse.url.startswith(reverse("connexion") + "?next="))
        self.assertEqual(self.client.post(reverse("personnes:creer"), {"designation": "Fictive"}).status_code, 302)
        self.assertEqual(Personne.objects.count(), 1)

    def test_connexion_sans_permission_ne_donne_aucun_droit_metier(self):
        self.client.force_login(self.compte)
        self.assertContains(self.client.get(reverse("accueil")), "pas encore de droit")
        for nom, args in [("liste", []), ("creer", []), ("detail", [self.personne.pk])]:
            self.assertEqual(self.client.get(reverse("personnes:" + nom, args=args)).status_code, 403)
        self.assertEqual(self.client.post(reverse("personnes:creer"), {"designation": "Fictive"}).status_code, 403)
        self.assertEqual(Personne.objects.count(), 1)

    def test_lecture_seule_et_creation_seule(self):
        self.droits("view_personne")
        self.assertContains(self.client.get(reverse("personnes:liste")), "Personne fictive A")
        self.assertEqual(self.client.get(reverse("personnes:detail", args=[self.personne.pk])).status_code, 200)
        self.assertEqual(self.client.post(reverse("personnes:creer"), {"designation": "Fictive"}).status_code, 403)
        self.droits("add_personne")
        self.assertEqual(self.client.post(reverse("personnes:creer"), {"designation": "Fictive"}).status_code, 403)

    def test_identite_incomplete_auteur_fixe_et_identifiants_distincts(self):
        self.droits("view_personne", "add_personne")
        for _ in range(2):
            reponse = self.client.post(reverse("personnes:creer"), {
                "designation": "  Identité fictive provisoire  ", "prenom": "", "cree_par": "999999",
            })
            self.assertEqual(reponse.status_code, 302)
            personne = Personne.objects.get(pk=reponse.url.rstrip("/").split("/")[-1])
            self.assertEqual(personne.designation, "Identité fictive provisoire")
            self.assertEqual(personne.prenom, "")
            self.assertEqual(personne.cree_par_id, self.compte.pk)
            self.assertIsNotNone(personne.cree_le)
            self.assertContains(self.client.get(reponse.url), "Non renseigné")
        self.assertEqual(Personne.objects.filter(designation="Identité fictive provisoire").count(), 2)

    def test_identite_vide_refusee_et_contenu_echappe(self):
        self.droits("view_personne", "add_personne")
        reponse = self.client.post(reverse("personnes:creer"), {"designation": "   "})
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["form"].errors)
        self.assertEqual(Personne.objects.count(), 1)
        reponse = self.client.post(reverse("personnes:creer"), {"designation": "<script>fictif</script>"})
        fiche = self.client.get(reponse.url)
        self.assertContains(fiche, "&lt;script&gt;fictif&lt;/script&gt;")
        self.assertNotContains(fiche, "<script>fictif</script>")

    def test_csrf_obligatoire_puis_creation_autorisee(self):
        self.droits("view_personne", "add_personne")
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.compte)
        url = reverse("personnes:creer")
        self.assertEqual(client.post(url, {"designation": "Fictive"}).status_code, 403)
        client.get(url)
        jeton = client.cookies[settings.CSRF_COOKIE_NAME].value
        self.assertEqual(client.post(url, {"designation": "Fictive", "csrfmiddlewaretoken": jeton}).status_code, 302)

    def test_pagination_et_fiche_absente(self):
        self.droits("view_personne")
        Personne.objects.bulk_create([Personne(designation=f"Fictive {i:02}", cree_par=self.compte) for i in range(26)])
        page = self.client.get(reverse("personnes:liste"))
        self.assertEqual(len(page.context["page_obj"]), 25)
        suite = self.client.get(reverse("personnes:liste"), {"page": 2})
        self.assertEqual(len(suite.context["page_obj"]), 2)
        self.assertEqual(self.client.get(reverse("personnes:detail", args=[uuid4()])).status_code, 404)

    def test_connexion_redirection_externe_refusee_et_deconnexion_post(self):
        reponse = self.client.post(reverse("connexion"), {
            "username": "essai", "password": "mot-de-passe-fictif-47", "next": "https://example.invalid/",
        })
        self.assertRedirects(reponse, reverse("accueil"))
        self.assertEqual(self.client.get(reverse("deconnexion")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("deconnexion")), reverse("connexion"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_controle_demarrage_et_independance_scolaire(self):
        self.assertJSONEqual(self.client.get(reverse("health")).content, {"status": "ok"})
        with patch("pas_a_pas_accompagnement.views.connection.cursor", side_effect=DatabaseError("fictif")):
            reponse = self.client.get(reverse("health"))
        self.assertEqual(reponse.status_code, 503)
        self.assertJSONEqual(reponse.content, {"status": "indisponible"})
        for nom in ["suivi", "referentiel", "comptes"]:
            self.assertFalse(apps.is_installed(nom))
        self.assertNotEqual(Personne, get_user_model())

    def test_compte_inactif_ne_peut_pas_se_connecter(self):
        self.compte.is_active = False
        self.compte.save(update_fields=["is_active"])
        reponse = self.client.post(reverse("connexion"), {"username": "essai", "password": "mot-de-passe-fictif-47"})
        self.assertEqual(reponse.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


class CompteEssaiTests(TestCase):
    def test_compte_ordinaire_permissions_et_mot_de_passe(self):
        sortie = StringIO()
        with patch("personnes.management.commands.creer_compte_essai.getpass", return_value="essai-fictif-long-2026!"):
            call_command("creer_compte_essai", "essai-fictif", stdout=sortie)
        compte = get_user_model().objects.get(username="essai-fictif")
        self.assertFalse(compte.is_staff)
        self.assertFalse(compte.is_superuser)
        self.assertTrue(compte.check_password("essai-fictif-long-2026!"))
        self.assertEqual(compte.get_all_permissions(), {"personnes.view_personne", "personnes.add_personne"})
        self.assertNotIn("essai-fictif-long-2026!", sortie.getvalue())
        self.assertTrue(self.client.login(username="essai-fictif", password="essai-fictif-long-2026!"))
        self.assertEqual(self.client.get(reverse("personnes:liste")).status_code, 200)

    def test_mot_de_passe_faible_refuse_et_compte_existant_preserve(self):
        with patch("personnes.management.commands.creer_compte_essai.getpass", return_value="123"):
            with self.assertRaises(CommandError):
                call_command("creer_compte_essai", "fictif")
        self.assertFalse(get_user_model().objects.exists())
        compte = get_user_model().objects.create_user(username="fictif", password="mot-de-passe-fictif-47")
        with self.assertRaises(CommandError):
            call_command("creer_compte_essai", "fictif")
        compte.refresh_from_db()
        self.assertTrue(compte.check_password("mot-de-passe-fictif-47"))
        self.assertEqual(compte.user_permissions.count(), 0)
