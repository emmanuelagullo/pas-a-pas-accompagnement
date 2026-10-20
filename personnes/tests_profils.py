"""CHRS14 : qualification des parcours par profils fictifs, sans rôles imposés."""
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from .tests_navigation import NavigationTests


class ParcoursProfilsTests(TestCase):
    def setUp(self):
        NavigationTests.setUp(self)

    def profil(self, *droits):
        """Chaque profil repart de zéro ; aucun droit ne doit être hérité."""
        self.u.user_permissions.clear()
        self.u.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="personnes", codename__in=droits))
        self.u = type(self.u).objects.get(pk=self.u.pk)
        self.client.force_login(self.u)

    def test_veilleur_releve_et_transmission_sans_dossier_social(self):
        self.profil("view_personne", "view_menage", "view_accompagnement",
                    "view_transmission", "add_transmission", "view_actionrelais",
                    "add_actionrelais")
        self.assertEqual(self.client.get(reverse("suivi:jour")).status_code, 200)
        self.assertEqual(self.client.get(reverse("suivi:cahier")).status_code, 200)
        self.assertEqual(self.client.get(reverse("suivi:actions_relais")).status_code, 200)
        self.assertEqual(self.client.post(reverse("suivi:cahier"),
                                          {"contenu": "Relève fictive"}).status_code, 302)
        self.assertEqual(self.client.post(reverse("suivi:actions_relais"),
                                          {"libelle": "Action fictive", "echeance": ""}).status_code, 302)
        self.assertEqual(self.client.get(reverse("suivi:trajectoire", args=[self.a.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("statistiques")).status_code, 403)

    def test_journee_consulte_et_cloture_sans_modifier_le_social(self):
        from .models import ActionRelais
        action = ActionRelais.objects.create(auteur=self.u, libelle="À reprendre")
        self.profil("view_personne", "view_menage", "view_accompagnement",
                    "view_transmission", "view_actionrelais", "change_actionrelais")
        self.assertEqual(self.client.get(reverse("suivi:jour")).status_code, 200)
        self.assertEqual(self.client.post(reverse("suivi:cahier"),
                                          {"contenu": "Non autorisé"}).status_code, 403)
        self.assertEqual(self.client.post(reverse("suivi:actions_relais"),
                                          {"libelle": "Non autorisé"}).status_code, 403)
        self.assertEqual(self.client.post(reverse("suivi:terminer_action_relais", args=[action.pk])).status_code, 302)
        action.refresh_from_db()
        self.assertIsNotNone(action.terminee_le)
        self.assertEqual(self.client.get(reverse("suivi:trajectoire", args=[self.a.pk])).status_code, 403)

    def test_referent_social_ne_recoit_pas_automatiquement_la_releve(self):
        self.profil("view_personne", "view_menage", "view_accompagnement",
                    "view_situationsociale")
        self.assertEqual(self.client.get(reverse("suivi:trajectoire", args=[self.a.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("suivi:cahier")).status_code, 403)
        self.assertEqual(self.client.get(reverse("suivi:actions_relais")).status_code, 403)
        self.assertEqual(self.client.get(reverse("statistiques")).status_code, 403)
