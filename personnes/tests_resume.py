from datetime import date
from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from . import tests_hebergement, hebergement as h, informations_suivi as informations
from .models import NotePartagee


class ResumeTests(TestCase):
    def setUp(self):
        tests_hebergement.Donnees.preparer(self)
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        self.u = type(self.u).objects.get(pk=self.u.pk)
        self.client.force_login(self.u)

    def test_resume_selon_droits_sans_notes_ni_versions_anciennes(self):
        h.ajouter_periode(self.u, self.s, date(2026,1,3), None, self.lieu)
        NotePartagee.objects.create(sejour=self.s, contenu='Note hors résumé', auteur=self.u)
        donnees = {champ: '' for champ in informations.CHAMPS}
        donnees['referent'] = 'Référent réservé fictif'
        informations.enregistrer(self.u, self.a, informations.jeton(self.a, None), 'Accueil', **donnees)
        url = reverse('suivi:resume', args=[self.a.pk])
        page = self.client.get(url)
        self.assertContains(page, 'Chambre fictive')
        self.assertContains(page, 'Référent réservé fictif')
        self.assertNotContains(page, 'Note hors résumé')
        self.assertIn('no-store', page['Cache-Control'])
        self.assertEqual(self.client.post(url).status_code, 405)
        self.u.user_permissions.remove(*self.u.user_permissions.filter(codename__in=['view_informationsaccompagnement', 'view_lieuhebergement']))
        page = self.client.get(url)
        self.assertNotContains(page, 'Référent réservé fictif')
        self.assertNotContains(page, 'Chambre fictive')

    def test_retour_lieu_et_notes(self):
        url = reverse('suivi:creer_lieu') + '?accord=' + str(self.accord.pk)
        self.assertRedirects(self.client.post(url, {'libelle': 'Nouveau lieu fictif', 'partenaire': ''}),
            reverse('suivi:accord_hebergement', args=[self.accord.pk]))
        self.assertRedirects(self.client.post(reverse('suivi:creer_lieu')+'?accord=https://example.test/',
            {'libelle': 'Autre lieu fictif', 'partenaire': ''}), reverse('suivi:liste'))
        from django.contrib.auth.models import Permission
        self.u.user_permissions.add(Permission.objects.get(content_type__app_label='personnes', codename='view_notepartagee'))
        url = reverse('suivi:notes', args=['sejour', self.s.pk])
        self.assertContains(self.client.get(url), reverse('suivi:accord_hebergement', args=[self.accord.pk]))

    def test_resume_interdit_sans_droits(self):
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(reverse('suivi:resume', args=[self.a.pk])).status_code, 403)


    def test_appartenance_identique_refusee_sans_effet_partiel(self):
        from . import suivi
        from django.core.exceptions import ValidationError
        avant = self.m.evenements.count()
        with self.assertRaises(ValidationError):
            suivi.ajouter_appartenance(self.u, self.m, self.p, date(2026,1,1))
        self.assertEqual(self.m.appartenances.count(), 1)
        self.assertEqual(self.m.evenements.count(), avant)
