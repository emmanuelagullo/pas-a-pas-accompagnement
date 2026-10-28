from html import unescape
import re
from urllib.parse import urlsplit,parse_qs
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from . import tests_meta_f

class ExportsCompositionTests(TestCase):
    setUpTestData=classmethod(tests_meta_f.ConsolidationStatistiques.setUpTestData.__func__)
    def setUp(self):self.client.force_login(self.u)
    def config(self,**kw):return tests_meta_f.ConsolidationStatistiques.config(self,**kw)
    def token(self,r):
        href=unescape(re.search(r'href="([^"]+)">Conserver ces réglages',r.content.decode())[1])
        return parse_qs(urlsplit(href).query)['definition'][0]
    def test_exports_reels_composition_synthese_detail_et_adaptation(self):
        from .vues_exploration import explorer
        for data in (self.config(),self.config(affichage='detail'),None):
            url=reverse('dossiers:explorer')
            if data is None:
                url=reverse('dossiers:personnaliser_rapport',args=['statistiques'])
                data=dict(rapport='repas',debut='2026-01-01',fin='2026-02-01')
            r=self.client.get(url,data,follow=True)
            for format in ('csv','pdf'):
                ex=self.client.post(reverse('dossiers:rapport_exporter'),dict(definition=self.token(r),format=format))
                self.assertEqual(ex.status_code,200,ex.content[:300])
                self.assertTrue(ex.content.startswith(b'%PDF-') if format=='pdf' else b'Valeur' in ex.content or b'Objet' in ex.content)
    def test_erreur_lisible_garde_options_criteres_et_page(self):
        r=self.client.get(reverse('dossiers:explorer'),{**self.config(),'page':2})
        with patch('personnes.exports_rapports.document',side_effect=ValidationError('Vérifiez la période.')):
            ex=self.client.post(reverse('dossiers:rapport_exporter'),dict(definition=self.token(r),format='csv',resume='Résumé conservé'))
        self.assertEqual(ex.status_code,422);self.assertContains(ex,'Vérifiez la période.',status_code=422)
        self.assertNotIn("['",ex.content.decode());self.assertContains(ex,'Résumé conservé',status_code=422)
        self.assertIn('population=',ex.context['retour']);self.assertIn('page=',ex.context['retour'])
    def test_pas_de_boutons_export_sur_criteres_invalides(self):
        r=self.client.get(reverse('dossiers:explorer'),self.config(debut='invalide'))
        self.assertContains(r,'Corrigez les critères signalés')
        self.assertNotContains(r,'class="carte rapport-export"')
