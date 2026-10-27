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
        self.assertEqual(get_user_model().objects.count(), 3)
        self.assertContains(self.client.get('/connexion/'), 'tâches distinctes')
        self.client.force_login(get_user_model().objects.get(username='essai'))
        page = self.client.get(reverse('accueil'))
        self.assertContains(page, 'id="filtre-acteurs"')
        self.assertContains(page, 'Mon service')
        self.assertNotContains(page, 'Essai — Dossier réservé à un autre service')
        page = self.client.get(reverse('accueil'), {'filtre': 'attente'})
        self.assertContains(page, 'Essai — En attente de suivi')
        self.assertNotContains(page, 'Essai — Mon dossier en cours')
        self.assertContains(self.client.get('/decouverte/'), 'Parcours acteurs')
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
