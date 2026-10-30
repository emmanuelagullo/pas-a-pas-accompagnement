"""Observations Chromium explicites, distinctes des tests HTML et de Pyodide."""
from datetime import date
from urllib.parse import urlencode
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from . import tests_meta_f as fixtures, analyses as a, repas


class AnalysesNavigateur(StaticLiveServerTestCase):
    def setUp(self):
        fixtures.ConsolidationStatistiques.setUpTestData.__func__(type(self))
        self.u.set_password('Recette-statistiques-fictive!');self.u.save()
        repas.distribuer(self.u,self.ar,self.adulte,date(2026,1,2),2)
        repas.distribuer(self.u,self.ar,self.adulte,date(2026,1,3),3)

    def test_selection_zero_justificatifs_retour_conservation_et_exports(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch()
            page=browser.new_page(viewport={'width':390,'height':844})
            page.goto(self.live_server_url+reverse('connexion'))
            page.locator('input[name=username]').fill(self.u.username)
            page.locator('input[name=password]').fill('Recette-statistiques-fictive!')
            page.get_by_role('button',name='Se connecter').click();page.wait_for_load_state('load')
            d=a.defaut();d.update(debut='2026-01-01',fin='2026-01-05',reference='2026-01-04',affichage='detail',criteres=[dict(source='prises',mode='avec',relation='personne')],mesures=[dict(titre='Repas',source='repas',mesure='quantite'),dict(titre='Nuitées',source='sejours',mesure='quantite')])
            page.goto(self.live_server_url+reverse('dossiers:analyse')+'?'+urlencode({'definition':a.encoder(d)}))
            page.get_by_role('heading',name='Analyse composée',exact=True).wait_for()
            self.assertEqual(page.get_by_text('Sur quoi porte la recherche ?',exact=True).count(),0)
            page.get_by_role('link',name='5 repas',exact=True).click()
            page.get_by_role('heading',name='Faits justificatifs',exact=True).wait_for()
            page.get_by_role('link',name='Ouvrir l’objet').first.click()
            page.get_by_role('link',name='Ouvrir le dossier de cet objet').click()
            page.get_by_role('link',name='Revenir aux résultats du rapport').click()
            page.get_by_role('heading',name='Faits justificatifs',exact=True).wait_for()
            page.get_by_role('link',name='Revenir à l’analyse').click()
            page.get_by_text('Conserver ce modèle ou ses paramètres',exact=True).click()
            page.get_by_label('Nom à conserver').fill('Mes repas habituels')
            page.get_by_label('Conserver comme').select_option('ensemble')
            page.get_by_label('Nom du nouveau modèle (si vous conservez les deux)').fill('Repas et nuits')
            page.get_by_role('button',name='Conserver une nouvelle entrée',exact=True).click()
            page.get_by_role('heading',name='Mes repas habituels',exact=True).wait_for()
            with page.expect_download() as dl:page.get_by_role('button',name='Exporter le CSV',exact=True).click()
            self.assertIsNone(dl.value.failure())
            with page.expect_download() as dl:page.get_by_role('button',name='Exporter le PDF',exact=True).click()
            self.assertIsNone(dl.value.failure())
            page.screenshot(path=str(__import__('pathlib').Path(__import__('tempfile').gettempdir())/'st13-analyse-mobile.png'),full_page=True)
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),410)
            # L'assemblage retrouve le modèle et la personnalisation conservés.
            page.goto(self.live_server_url+reverse('dossiers:assemblage'))
            page.get_by_text('Organiser les parties et leurs paramètres · 0 parties',exact=True).click()
            page.get_by_label('Modèle personnel à réutiliser').select_option(label='Repas et nuits')
            page.get_by_role('button',name='Ajouter cette analyse',exact=True).click()
            page.get_by_role('heading',name='1. Repas et nuits',exact=True).wait_for()
            with page.expect_download() as dl:page.get_by_role('button',name='Exporter le PDF',exact=True).click()
            self.assertIsNone(dl.value.failure())

            browser.close()

    def test_compositeur_contextuel_sans_javascript_clavier_et_retour_local(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch()
            page=browser.new_page(viewport={'width':390,'height':844},java_script_enabled=False)
            page.goto(self.live_server_url+reverse('connexion'))
            page.locator('input[name=username]').fill(self.u.username)
            page.locator('input[name=password]').fill('Recette-statistiques-fictive!')
            page.get_by_role('button',name='Se connecter').click()
            d=a.defaut();d.update(debut='2026-01-01',fin='2026-01-05',reference='2026-01-04')
            page.goto(self.live_server_url+reverse('dossiers:analyse')+'?'+urlencode({'definition':a.encoder(d)}))
            page.locator('#modifier-compter > summary').focus();page.keyboard.press('Enter')
            page.locator('#bloc-mesure1_ > summary').focus();page.keyboard.press('Enter')
            choix=page.get_by_label('Calcul');choix.wait_for(state='visible')
            self.assertNotIn('nuits_distinctes',choix.locator('option').evaluate_all('(xs) => xs.map(x => x.value)'))
            self.assertEqual(page.get_by_label('Nuitées des épisodes retenus').count(),0)
            page.get_by_label('Éléments à compter').select_option('sejours')
            page.get_by_role('button',name='Actualiser les choix de ce bloc').click()
            choix=page.get_by_label('Calcul');choix.wait_for(state='visible')
            self.assertIn('nuits_distinctes',choix.locator('option').evaluate_all('(xs) => xs.map(x => x.value)'))
            self.assertEqual(page.locator('#modifier-compter[open] #bloc-mesure1_[open]').count(),1)
            choix.select_option('nuits_distinctes')
            page.locator('#modifier-compter').get_by_role('button',name='Appliquer',exact=True).click()
            page.get_by_role('button',name='Ajouter une mesure',exact=True).click()
            self.assertEqual(page.locator('#bloc-mesure2_[open]').count(),1)
            self.assertIn('Somme',page.locator('#bloc-mesure2_ > summary').inner_text())
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),410)
            page.screenshot(path='/tmp/st14-compositeur-mobile.png',full_page=True)
            page.set_viewport_size({'width':1280,'height':900})
            page.screenshot(path='/tmp/st14-compositeur-bureau.png',full_page=True)
            browser.close()
