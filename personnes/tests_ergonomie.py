"""Parcours courts : cible, état et contexte, sans nouvelle écriture implicite."""
from datetime import date
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from .tests_hebergement import Donnees
from . import hebergement as h
from .models import Transmission, NotePartagee


class ErgonomieTests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        self.u.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='personnes', codename__in=[
                'view_transmission', 'add_transmission', 'change_transmission',
                'view_notepartagee', 'add_notepartagee', 'change_notepartagee']))
        self.client.force_login(self.u)
        self.contexte = '?retour=jour&date_service=2026-01-06'
        self.jour = reverse('suivi:jour') + '?date=2026-01-06'

    def test_actions_adaptees_et_sejour_clos(self):
        affectation = h.ajouter_periode(self.u, self.s, date(2026, 1, 3), None, self.lieu)
        absence = h.ajouter_periode(self.u, self.s, date(2026, 1, 4), None, absence=True)
        page = self.client.get(self.jour)
        self.assertContains(page, reverse('suivi:changer_lieu', args=[affectation.pk]))
        self.assertContains(page, reverse('suivi:clore_absence', args=[absence.pk]))
        self.assertNotContains(page, reverse('suivi:absence', args=[self.s.pk]))
        self.assertNotContains(page, reverse('suivi:affecter', args=[self.s.pk]))
        h.sortir(self.u, self.s, date(2026, 1, 10))
        page = self.client.get(self.jour)
        self.assertContains(page, 'Séjour désormais clos')
        self.assertNotContains(page, reverse('suivi:sortir', args=[self.s.pk]))

    def test_retour_absence_date_identite_et_redirection(self):
        absence = h.ajouter_periode(self.u, self.s, date(2026, 1, 4), None, absence=True)
        url = reverse('suivi:clore_absence', args=[absence.pk]) + self.contexte
        page = self.client.get(url)
        self.assertContains(page, self.p.designation)
        self.assertContains(page, self.m.libelle)
        self.assertEqual(page.context['form'].initial['fin'], date(2026, 1, 6))
        reponse = self.client.post(url, {'fin': '2026-01-06', 'retour': 'jour', 'date_service': '2026-01-06'})
        self.assertRedirects(reponse, self.jour)
        absence.refresh_from_db()
        self.assertEqual(absence.fin, date(2026, 1, 6))

    def test_accord_conserve_date_et_destination_sure(self):
        page = self.client.get(reverse('suivi:accord_hebergement', args=[self.accord.pk]) + self.contexte)
        self.assertContains(page, 'date_service=2026-01-06')
        self.assertContains(page, self.jour)
        page = self.client.get(reverse('suivi:absence', args=[self.s.pk]) + '?retour=jour&date_service=https://exemple.invalid')
        self.assertNotContains(page, 'https://exemple.invalid')
        self.assertEqual(page.context['date_service'], '')

    def test_notes_correction_annulation_et_conflit_conservent_contexte(self):
        note = NotePartagee.objects.create(sejour=self.s, contenu='Version initiale', auteur=self.u)
        notes = reverse('suivi:notes', args=['sejour', self.s.pk])
        page = self.client.get(notes + self.contexte)
        self.assertContains(page, self.p.designation)
        self.assertContains(page, 'date_service=2026-01-06')
        url = reverse('suivi:corriger_contribution', args=['note', note.pk]) + self.contexte
        page = self.client.get(url)
        self.assertContains(page, 'Annuler et revenir')
        self.assertContains(page, self.p.designation)
        donnees = {'contenu': 'Version corrigée', 'texte_attendu': 'Ancienne version périmée',
                   'motif': 'Correction fictive', 'retour': 'jour', 'date_service': '2026-01-06'}
        page = self.client.post(url, donnees)
        self.assertEqual(page.status_code, 409)
        self.assertContains(page, 'Annuler et revenir', status_code=409)
        donnees['texte_attendu'] = note.contenu
        self.assertRedirects(self.client.post(url, donnees), notes + self.contexte)
        self.assertContains(self.client.get(notes + self.contexte), self.jour)

    def test_auteur_visible_et_droit_correction_preserve(self):
        message = Transmission.objects.create(contenu='Relève fictive', auteur=self.u)
        self.assertContains(self.client.get(self.jour), self.u.username)
        self.u.user_permissions.remove(Permission.objects.get(
            content_type__app_label='personnes', codename='change_transmission'))
        self.assertEqual(self.client.get(reverse('suivi:corriger_contribution', args=['transmission', message.pk])).status_code, 403)

    def test_filtres_rapport_et_modeles_apres_resultats(self):
        self.u.user_permissions.add(Permission.objects.get(
            content_type__app_label='personnes', codename='view_repasdistribue'))
        url = reverse('statistiques')
        dates = {'debut': '2026-01-01', 'fin': '2026-02-01'}
        for rapport, champ, autre in [('mouvements', None, None),
                ('exploration_repas', 'service', 'lieu'),
                ('exploration_hebergement', 'lieu', 'service')]:
            page = self.client.get(url, {**dates, 'rapport': rapport})
            self.assertEqual(page.status_code, 200)
            if champ:
                self.assertContains(page, 'id="' + champ + '"')
                self.assertNotContains(page, 'id="' + autre + '"')
            else:
                for nom in ('service', 'lieu', 'regroupement'):
                    self.assertNotContains(page, 'id="' + nom + '"')
            html = page.content.decode()
            self.assertLess(html.index('Exporter ce rapport'), html.index('Mes modèles de rapports'))

    def test_notes_ne_revelent_pas_identite_sans_droit_personne(self):
        self.u.user_permissions.remove(Permission.objects.get(
            content_type__app_label='personnes', codename='view_personne'))
        page = self.client.get(reverse('suivi:notes', args=['sejour', self.s.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, self.p.designation)

    def test_periode_ouverte_apres_date_consultee_ne_propose_pas_doublon(self):
        h.ajouter_periode(self.u, self.s, date(2026, 1, 8), None, absence=True)
        page = self.client.get(self.jour)
        self.assertNotContains(page, reverse('suivi:absence', args=[self.s.pk]))
        self.assertNotContains(page, 'Enregistrer le retour d’absence')
