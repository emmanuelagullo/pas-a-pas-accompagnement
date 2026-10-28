from django.test import TestCase
from django.urls import reverse
from . import tests_meta_f
from .catalogue_rapports import SOURCES

class EntetesStatistiquesTests(TestCase):
    setUpTestData=classmethod(tests_meta_f.ConsolidationStatistiques.setUpTestData.__func__)
    def setUp(self):self.client.force_login(self.u)
    def test_entetes_et_retours_des_sources_et_composition(self):
        for source in [*SOURCES,'exploration']:
            url=reverse('dossiers:explorer') if source=='exploration' else reverse('dossiers:rapport_composer',args=[source])
            r=self.client.get(url,{'filtre':'mes'})
            self.assertEqual(r.status_code,200,r.content[:400])
            h=r.content.decode();main=h[h.index('<main'):]
            self.assertIn('← Statistiques et rapports',main)
            self.assertLess(main.index('← Statistiques et rapports'),main.index('<h1>'))
            self.assertNotIn('Retour au travail du jour',main);self.assertNotIn('Rapport affiché —',main)
            self.assertIn('filtre=mes',r.content.decode())
