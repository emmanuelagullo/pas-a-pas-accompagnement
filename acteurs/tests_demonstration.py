from io import StringIO
from copy import deepcopy
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import ConfigurationAcces, DossierService
from personnes.models import Personne


TEMPLATES_DEMO = deepcopy(settings.TEMPLATES)
TEMPLATES_DEMO[0]['OPTIONS']['context_processors'].append('pas_a_pas_accompagnement.demo.contexte')


@override_settings(DEMONSTRATION_PUBLIQUE=True, TEMPLATES=TEMPLATES_DEMO)
class DemonstrationActeursTests(TestCase):
    def preparer(self):
        call_command('preparer_demonstration', acteurs=True, stdout=StringIO())

    def test_filtres_et_decouverte_apres_connexion(self):
        self.preparer()
        self.assertTrue(ConfigurationAcces.objects.get(pk=1).active)
        self.assertEqual(get_user_model().objects.count(), 5)
        self.assertContains(self.client.get('/connexion/'), 'tâches distinctes')
        self.client.force_login(get_user_model().objects.get(username='essai'))
        page = self.client.get(reverse('accueil'))
        self.assertContains(page, 'class="choix-dossiers"')
        self.assertContains(page, 'Mon service')
        self.assertEqual(Personne.objects.count(),36)
        page = self.client.get(reverse('accueil'), {'filtre': 'attente'})
        self.assertContains(page, 'Noor')
        self.assertNotContains(page, 'Alex')
        self.assertContains(page, 'badge-attente')
        self.assertContains(self.client.get('/decouverte/'), 'commencez le suivi')
        self.client.force_login(get_user_model().objects.get(username='coordination'))
        self.assertEqual(self.client.get(reverse('accueil')).status_code, 302)

    def test_refus_base_existante_sans_modification(self):
        self.preparer()
        avant = (Personne.objects.count(), DossierService.objects.count())
        with self.assertRaises(CommandError):
            self.preparer()
        self.assertEqual(avant, (Personne.objects.count(), DossierService.objects.count()))

    @override_settings(DEMONSTRATION_PUBLIQUE=False)
    def test_refus_hors_demonstration(self):
        with self.assertRaises(CommandError):
            self.preparer()
        self.assertFalse(get_user_model().objects.exists())

    def test_navigation_compacte_et_raccourci_personnel(self):
        self.preparer()
        self.client.force_login(get_user_model().objects.get(username='essai'))
        page=self.client.get(reverse('accueil'))
        self.assertContains(page, '>Établissement</a>')
        self.assertContains(page, '<summary>Compte : essai</summary>')
        self.assertContains(page, '<summary>En chantier</summary>')
        self.assertNotContains(page, 'Service pour les nouvelles saisies')
        self.assertNotContains(page, 'Statistiques de mon service')
        self.assertNotContains(page, 'Découvrir les acteurs et les relais')
        self.assertNotContains(page, 'Essai —')
        self.assertNotContains(page, 'id="service-acteurs"')
        page=self.client.get(reverse('accueil'),{'filtre':'mes','en_cours':'1'})
        self.assertContains(page,'Alex')
        self.assertNotContains(page,'Yannis')
