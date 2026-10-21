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

    def test_correction_parcours_et_historique(self):
        self.client.force_login(self.u)
        note = transmissions.noter(self.u, "Version initiale", personne=self.p)
        url = reverse("suivi:corriger_contribution", args=["note", note.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {"contenu": "Version corrigée", "motif": "Rectification factuelle", "texte_attendu": "Version initiale"}).status_code, 302)
        note.refresh_from_db()
        self.assertEqual(note.contenu, "Version corrigée")
        revision = RevisionContribution.objects.get(note=note)
        self.assertEqual(revision.ancien_texte, "Version initiale")
        self.assertEqual(revision.nouveau_texte, "Version corrigée")
        self.assertEqual(revision.motif, "Rectification factuelle")

    def test_correction_interdite_sans_droit_sur_la_cible(self):
        note = transmissions.noter(self.u, "Texte", personne=self.p)
        compte = get_user_model().objects.create_user("correcteur-sans-cible")
        compte.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="personnes", codename__in=["view_notepartagee", "change_notepartagee"]))
        self.client.force_login(compte)
        self.assertEqual(self.client.get(reverse("suivi:corriger_contribution", args=["note", note.pk])).status_code, 403)

    def test_correction_concurrente_refuse_une_version_perimee(self):
        self.client.force_login(self.u)
        note = transmissions.noter(self.u, "Texte initial", personne=self.p)
        url = reverse("suivi:corriger_contribution", args=["note", note.pk])
        self.assertContains(self.client.get(url), 'name="texte_attendu"', html=False)
        transmissions.rectifier(self.u, note, "Modification intermédiaire", "Correction préalable")
        reponse = self.client.post(url, {"contenu": "Écrasement", "motif": "Correction tardive",
                                         "texte_attendu": "Texte initial"})
        self.assertEqual(reponse.status_code, 409)
        note.refresh_from_db()
        self.assertEqual(note.contenu, "Modification intermédiaire")
        self.assertEqual(RevisionContribution.objects.filter(note=note).count(), 1)

    def test_historique_visible_dans_la_fiche(self):
        self.client.force_login(self.u)
        note = transmissions.noter(self.u, "Avant", personne=self.p)
        transmissions.rectifier(self.u, note, "Après", "Rectification documentée")
        reponse = self.client.get(reverse("suivi:notes", args=["personne", self.p.pk]))
        self.assertContains(reponse, "Rectification documentée")
        self.assertContains(reponse, "Avant")
        self.assertContains(reponse, "Après")

class RetourServiceTests(TestCase):
    """Le retour explicite est borné à une route interne connue."""

    def setUp(self):
        self.u = get_user_model().objects.create_user("retour-service-fictif")
        self.u.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="personnes", codename__in=[
                "view_transmission", "add_transmission", "view_actionrelais", "add_actionrelais", "change_actionrelais"]))
        self.client.force_login(self.u)

    def test_transmission_retour_au_service(self):
        url = reverse("suivi:cahier")
        self.assertContains(self.client.get(url + "?retour=jour"), 'name="retour" value="jour"')
        self.assertRedirects(self.client.post(url, {"contenu": "Relève", "retour": "jour"}),
                             reverse("suivi:jour"), fetch_redirect_response=False)
        self.assertRedirects(self.client.post(url, {"contenu": "Autre", "retour": "https://exemple.test/"}),
                             url, fetch_redirect_response=False)

    def test_action_retour_au_service(self):
        from .models import ActionRelais
        url = reverse("suivi:actions_relais")
        self.assertContains(self.client.get(url + "?retour=jour"), 'name="retour" value="jour"')
        self.assertRedirects(self.client.post(url, {"libelle": "Relire le cahier", "retour": "jour"}),
                             reverse("suivi:jour"), fetch_redirect_response=False)
        action = ActionRelais.objects.get()
        self.assertRedirects(self.client.post(reverse("suivi:terminer_action_relais", args=[action.pk]),
                                              {"retour": "jour"}), reverse("suivi:jour"),
                             fetch_redirect_response=False)


class AffichageContributionsTests(TransmissionsTests):
    def test_contributions_ne_sont_pas_des_alertes_globales(self):
        from django.contrib.messages.storage.cookie import CookieStorage
        from django.contrib.messages.storage.base import Message
        from django.contrib.messages import SUCCESS
        self.client.force_login(self.u)
        transmissions.transmettre(self.u, 'Texte de liaison unique')
        transmissions.noter(self.u, 'Texte de note unique', personne=self.p)
        for route, texte in [(reverse('suivi:cahier'), 'Texte de liaison unique'),
                             (reverse('suivi:notes', args=['personne', self.p.pk]), 'Texte de note unique')]:
            self.client.cookies['messages'] = CookieStorage(None)._encode([Message(SUCCESS, 'Alerte enregistrée')])
            page = self.client.get(route)
            self.assertContains(page, 'Alerte enregistrée', count=1)
            self.assertContains(page, texte, count=1)
