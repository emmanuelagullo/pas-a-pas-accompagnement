from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .tests_navigation import NavigationTests
from .models import ModeleRapport


class ModelesRapportsTests(TestCase):
    def setUp(self):
        NavigationTests.setUp(self)
        self.parametres = {'nom': 'Repas janvier', 'rapport': 'exploration_repas',
                           'debut': '2026-01-01', 'fin': '2026-02-01',
                           'service': 'dejeuner', 'regroupement': 'categorie'}

    def test_enregistrer_recharger_supprimer(self):
        url = reverse('statistiques_modele_ajouter')
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, self.parametres).status_code, 302)
        modele = ModeleRapport.objects.get(auteur=self.u)
        self.assertEqual(modele.parametres['service'], 'dejeuner')
        self.assertNotIn('nom', modele.parametres)
        self.assertEqual(self.client.get(reverse('statistiques'), {'modele': modele.pk}).status_code, 200)
        self.assertContains(self.client.get(reverse('statistiques'), {'modele': modele.pk}), 'Repas janvier')
        self.assertEqual(self.client.post(reverse('statistiques_modele_supprimer', args=[modele.pk])).status_code, 302)
        self.assertFalse(ModeleRapport.objects.exists())

    def test_isolation_et_permissions(self):
        self.client.post(reverse('statistiques_modele_ajouter'), self.parametres)
        modele = ModeleRapport.objects.get()
        autre = get_user_model().objects.create_user(username='autre_stat', password='test')
        self.client.force_login(autre)
        self.assertEqual(self.client.get(reverse('statistiques'), {'modele': modele.pk}).status_code, 403)
        self.assertEqual(self.client.post(reverse('statistiques_modele_supprimer', args=[modele.pk])).status_code, 403)
        self.client.force_login(self.u)
        self.u.user_permissions.clear()
        self.assertEqual(self.client.post(reverse('statistiques_modele_ajouter'), self.parametres).status_code, 403)

    def test_configuration_invalide(self):
        url = reverse('statistiques_modele_ajouter')
        for modification in ({'fin': '2026-01-01'}, {'rapport': 'inconnu'},
                             {'regroupement': 'inconnu'}, {'service': 'secret'},
                             {'debut': '2020-01-01', 'fin': '2026-01-01'}):
            with self.subTest(modification=modification):
                self.assertEqual(self.client.post(url, {**self.parametres, **modification}).status_code, 400)
        self.assertEqual(ModeleRapport.objects.count(), 0)

    def test_periode_relative_recalculee_et_csv(self):
        from datetime import date
        from unittest.mock import patch
        from django.utils import timezone
        from .vues_statistiques import bornes_periode
        self.assertEqual(bornes_periode('mois_precedent', date(2026, 1, 10)),
                         (date(2025, 12, 1), date(2026, 1, 1)))
        self.assertEqual(bornes_periode('douze_mois', date(2026, 2, 10)),
                         (date(2025, 3, 1), date(2026, 2, 11)))
        self.assertEqual(bornes_periode('douze_mois', date(2026, 1, 10)),
                         (date(2025, 2, 1), date(2026, 1, 11)))
        with patch('personnes.vues_statistiques.timezone.localdate', return_value=date(2026, 1, 10)):
            self.assertEqual(self.client.post(reverse('statistiques_modele_ajouter'),
                                              {**self.parametres, 'periode': 'mois_precedent'}).status_code, 302)
        modele = ModeleRapport.objects.get()
        self.assertEqual(modele.parametres['periode'], 'mois_precedent')
        with patch('personnes.vues_statistiques.timezone.localdate', return_value=date(2026, 2, 10)):
            page = self.client.get(reverse('statistiques'), {'modele': modele.pk})
            self.assertEqual(page.status_code, 200)
            self.assertContains(page, '2026-01-01')
            self.assertContains(page, '2026-02-01')
            export = self.client.get(reverse('statistiques'), {'modele': modele.pk, 'format': 'csv'})
            self.assertEqual(export.status_code, 200)
            self.assertIn('quantite_distribuee', export.content.decode())

    def test_periode_relative_inconnue_refusee(self):
        self.assertEqual(self.client.post(reverse('statistiques_modele_ajouter'),
                                          {**self.parametres, 'periode': 'inventee'}).status_code, 400)
        self.assertFalse(ModeleRapport.objects.exists())

    def test_modele_autre_utilisateur_avec_permissions(self):
        from django.contrib.auth.models import Permission
        self.client.post(reverse('statistiques_modele_ajouter'), self.parametres)
        modele = ModeleRapport.objects.get()
        autre = get_user_model().objects.create_user(username='autre_stat_autorise', password='test')
        autre.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='personnes', codename__in=(
                'view_accompagnement', 'view_sejour', 'view_repasdistribue')))
        self.client.force_login(autre)
        self.assertEqual(self.client.get(reverse('statistiques'), {'modele': modele.pk}).status_code, 404)
        self.assertEqual(self.client.get(reverse('statistiques'), {'modele': modele.pk, 'format': 'csv'}).status_code, 404)
        self.assertEqual(self.client.post(reverse('statistiques_modele_supprimer', args=[modele.pk])).status_code, 404)
