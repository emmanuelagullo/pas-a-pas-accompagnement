from datetime import date
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from .models import Personne, Transmission, NotePartagee, RevisionContribution
from . import transmissions


class TransmissionsTests(TestCase):
    def setUp(self):
        self.u = get_user_model().objects.create_user("transmission-fictive")
        self.p = Personne.objects.create(designation="Dossier fictif", cree_par=self.u)
        self.u.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="personnes", codename__in=[
                "add_transmission", "view_transmission", "change_transmission",
                "add_notepartagee", "view_notepartagee", "change_notepartagee", "view_personne"]))

    def test_contributions_distinctes_et_revision(self):
        t = transmissions.transmettre(self.u, "Relève fictive")
        n = transmissions.noter(self.u, "Note fictive", personne=self.p)
        self.assertEqual(Transmission.objects.count(), 1)
        self.assertEqual(NotePartagee.objects.count(), 1)
        transmissions.rectifier(self.u, n, "Note rectifiée", "Erreur de saisie")
        n.refresh_from_db()
        self.assertEqual(n.contenu, "Note rectifiée")
        self.assertEqual(RevisionContribution.objects.get(note=n).ancien_texte, "Note fictive")
        with self.assertRaises(ValidationError):
            transmissions.noter(self.u, "Sans cible")
        with self.assertRaises(ValidationError):
            transmissions.rectifier(self.u, t, "Autre", " ")

    def test_droits_et_parcours(self):
        self.client.force_login(self.u)
        url = reverse("suivi:cahier")
        self.assertEqual(self.client.post(url, {"contenu": "Relève fictive"}).status_code, 302)
        self.assertContains(self.client.get(url), "Relève fictive")
        cible = reverse("suivi:notes", args=["personne", self.p.pk])
        self.assertEqual(self.client.post(cible, {"contenu": "Note fictive"}).status_code, 302)
        self.assertContains(self.client.get(cible), "Note fictive")
        autre = get_user_model().objects.create_user("sans-droit-fictif")
        self.client.force_login(autre)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.get(cible).status_code, 403)
        with self.assertRaises(PermissionDenied):
            transmissions.transmettre(autre, "Refus")
