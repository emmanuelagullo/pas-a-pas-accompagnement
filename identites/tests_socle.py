from io import StringIO
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase
from django.urls import reverse


class SocleAuthentificationTests(TestCase):
    def setUp(self):
        self.compte = get_user_model().objects.create_user("essai", password="Phrase fictive-3794")

    def test_plafond_avant_hachage_et_creation(self):
        with patch.object(get_user_model(), "check_password") as verifier:
            self.assertIsNone(authenticate(username="essai",password="x"*1025))
            verifier.assert_not_called()
        with self.assertRaises(ValidationError):validate_password("Phrase fictive-3794"*100)
        reponse=self.client.post(reverse("connexion"),{"username":"essai","password":"x"*1025})
        self.assertEqual(reponse.status_code,200)
        self.assertNotIn("_auth_user_id",self.client.session)

    def test_backend_standard_et_ancienne_session_conserves(self):
        self.client.force_login(self.compte,backend="django.contrib.auth.backends.ModelBackend")
        self.assertEqual(self.client.get(reverse("accueil")).status_code,200)
        self.assertEqual(self.client.session["_auth_user_backend"],"django.contrib.auth.backends.ModelBackend")
        self.assertEqual(self.client.get(reverse("personnes:liste")).status_code,403)

    def test_commande_ferme_toutes_les_sessions_du_seul_compte(self):
        autre=get_user_model().objects.create_user("autre-fictif",password="Phrase fictive-3794")
        clients=[Client(),Client(),Client()]
        for client,user in zip(clients,[self.compte,self.compte,autre]):client.force_login(user)
        out=StringIO();call_command("fermer_sessions_compte","essai",stdout=out)
        self.assertIn("2 session(s) fermée(s)",out.getvalue())
        for client in clients[:2]:self.assertEqual(client.get(reverse("accueil")).status_code,302)
        self.assertEqual(clients[2].get(reverse("accueil")).status_code,200)
        self.assertFalse(self.compte.user_permissions.exists())
        with self.assertRaises(CommandError):call_command("fermer_sessions_compte","inconnu")

    def test_deconnexion_exige_post_et_protection_csrf(self):
        self.client.force_login(self.compte)
        self.assertEqual(self.client.get(reverse("deconnexion")).status_code,405)
        client=Client(enforce_csrf_checks=True);client.force_login(self.compte)
        self.assertEqual(client.post(reverse("deconnexion")).status_code,403)
        self.assertEqual(self.client.post(reverse("deconnexion")).status_code,302)
        self.assertNotIn("_auth_user_id",self.client.session)

    def test_cookies_du_produit_distincts_des_noms_django(self):
        self.assertEqual(settings.SESSION_COOKIE_NAME,"pas_accompagnement_sessionid")
        self.assertEqual(settings.CSRF_COOKIE_NAME,"pas_accompagnement_csrftoken")

    def test_mot_de_passe_change_invalide_la_session(self):
        self.client.force_login(self.compte)
        self.compte.set_password("Autre phrase fictive-3794");self.compte.save()
        self.assertEqual(self.client.get(reverse("accueil")).status_code,302)
