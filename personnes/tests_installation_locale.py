from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from .models import Personne


class InstallationTests(TestCase):
    def test_absente_du_profil_developpement(self):
        self.assertEqual(self.client.get(reverse("installation_locale")).status_code, 404)

    @override_settings(MODE_LOCAL=True)
    def test_premier_compte_ouvre_les_fiches_sans_superpouvoir(self):
        self.assertRedirects(self.client.get(reverse("accueil")), reverse("installation_locale"))
        reponse = self.client.post(reverse("installation_locale"), {
            "username": "compte-fictif", "password1": "mot-de-passe-fictif-2026!", "password2": "mot-de-passe-fictif-2026!"})
        self.assertRedirects(reponse, reverse("personnes:liste"))
        compte = get_user_model().objects.get(username="compte-fictif")
        self.assertFalse(compte.is_superuser)
        self.assertFalse(compte.is_staff)
        self.assertEqual(compte.get_all_permissions(), {"personnes.add_personne", "personnes.view_personne"})
        self.assertEqual(self.client.get(reverse("installation_locale")).status_code, 404)
        self.assertEqual(self.client.post(reverse("installation_locale"), {}).status_code, 404)
        self.assertEqual(get_user_model().objects.count(), 1)

    @override_settings(MODE_LOCAL=True)
    def test_csrf_et_mot_de_passe_restent_obligatoires(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("installation_locale"), {}).status_code, 403)
        self.client.post(reverse("installation_locale"), {"username": "fictif", "password1": "123", "password2": "123"})
        self.assertFalse(get_user_model().objects.exists())

    @override_settings(MODE_LOCAL=True)
    def test_espace_deja_initialise_ne_peut_pas_recreer_un_compte(self):
        get_user_model().objects.create_user(username="deja-fictif")
        self.assertEqual(self.client.get(reverse("installation_locale")).status_code, 404)
