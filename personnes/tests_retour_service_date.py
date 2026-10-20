"""Recette d'un aller-retour de relève depuis une consultation historique."""
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from .models import ActionRelais


class RetourDateTests(TestCase):
    def setUp(self):
        self.u = get_user_model().objects.create_user("retour-date-fictif")
        self.u.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="personnes", codename__in=[
                "view_transmission", "add_transmission", "view_actionrelais",
                "add_actionrelais", "change_actionrelais"]))
        self.client.force_login(self.u)
        self.cible = reverse("suivi:jour") + "?date=2026-01-03"

    def test_transmission_retrouve_la_date(self):
        url = reverse("suivi:cahier")
        self.assertContains(self.client.get(url + "?retour=jour&date_service=2026-01-03"),
                            'name="date_service" value="2026-01-03"')
        self.assertRedirects(self.client.post(url, {"retour": "jour", "date_service": "2026-01-03",
                                                    "contenu": "Relève fictive"}), self.cible,
                             fetch_redirect_response=False)

    def test_action_et_cloture_retrouvent_la_date(self):
        url = reverse("suivi:actions_relais")
        self.assertContains(self.client.get(url + "?retour=jour&date_service=2026-01-03"),
                            'name="date_service" value="2026-01-03"')
        self.assertRedirects(self.client.post(url, {"retour": "jour", "date_service": "2026-01-03",
                                                    "libelle": "Vérification fictive"}), self.cible,
                             fetch_redirect_response=False)
        action = ActionRelais.objects.get()
        self.assertRedirects(self.client.post(reverse("suivi:terminer_action_relais", args=[action.pk]),
                                              {"retour": "jour", "date_service": "2026-01-03"}),
                             self.cible, fetch_redirect_response=False)

    def test_date_malveillante_ne_produit_pas_de_redirection_externe(self):
        url = reverse("suivi:cahier")
        self.assertRedirects(self.client.post(url, {"retour": "jour", "date_service": "//exemple.test",
                                                    "contenu": "Test fictif"}), reverse("suivi:jour"),
                             fetch_redirect_response=False)
