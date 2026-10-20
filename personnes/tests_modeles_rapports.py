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
