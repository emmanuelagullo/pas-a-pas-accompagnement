"""COL2–4 : vrais gestes Chromium, avec et sans JavaScript."""
from pathlib import Path
import os
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from .tests_hebergement import Donnees
from . import tests_collectifs as tests
from django.conf import settings

class CollectifsNavigateur(Donnees,StaticLiveServerTestCase):
    declarer=tests.CollectifsTests.declarer
    restaurer=tests.CollectifsTests.restaurer
    def setUp(self):tests.CollectifsTests.setUp(self)

    def parcourir(self,javascript,largeur):
        from playwright.sync_api import sync_playwright,expect
        self.client.force_login(self.u)
        session=self.client.cookies[settings.SESSION_COOKIE_NAME].value
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                ctx=browser.new_context(java_script_enabled=javascript,viewport={'width':largeur,'height':900})
                ctx.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':session,'url':self.live_server_url}])
                page=ctx.new_page()
                url=self.live_server_url+reverse('dossiers:prise',args=['menage',self.m.pk,self.a.pk])
                page.goto(url)
                page.get_by_role('link',name='Nouvelle restauration',exact=True).click()
                form=page.locator('#collectif-form form');expect(form).to_be_visible()
                form.locator('[name=debut]').fill('2026-01-10')
                form.locator('[name=fin_prevue]').fill('2026-01-13')
                form.locator('[name=premier]').select_option('diner')
                form.locator('[name=dernier]').select_option('dejeuner')
                form.locator('[name=prix_adulte]').fill('8')
                form.locator('[name=prix_enfant]').fill('5')
                if os.environ.get('COL_CAPTURES'):
                    out=Path(os.environ['COL_CAPTURES']);out.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(out/f'COL-restauration-{largeur}.png'),full_page=True)
                form.get_by_role('button',name='Enregistrer',exact=True).click()
                expect(page.locator('#prestations-collectives')).to_contain_text('Restauration')
                carte=page.locator('#prestations-collectives article').first
                carte.get_by_role('link',name='Prolonger',exact=True).click()
                form=page.locator('#collectif-form form');form.locator('[name=date]').fill('2026-01-15')
                form.get_by_role('button',name='Enregistrer',exact=True).click()
                expect(page.locator('#prestations-collectives article').first).to_contain_text('15/01/2026')
                page.get_by_role('link',name='Bilan / Imprimer',exact=True).click()
                expect(page.get_by_role('heading',name='Bilan des prestations collectives')).to_be_visible()
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),largeur+1)
                if os.environ.get('COL_CAPTURES'):
                    out=Path(os.environ['COL_CAPTURES']);out.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(out/f'COL-bilan-{largeur}.png'),full_page=True)
            finally:browser.close()

    def test_390_avec_javascript(self):self.parcourir(True,390)
    def test_1366_sans_javascript(self):self.parcourir(False,1366)
