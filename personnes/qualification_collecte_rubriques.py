from pathlib import Path
import os
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import Permission
from django.urls import reverse
from .tests_hebergement import Donnees
from . import tests_collectifs as base

class CollecteNavigateur(Donnees,StaticLiveServerTestCase):
    declarer=base.CollectifsTests.declarer
    def setUp(self):
        base.CollectifsTests.setUp(self)
        self.u.user_permissions.add(Permission.objects.get(content_type__app_label='acteurs',codename='gerer_organisation'))
        self.u=type(self.u).objects.get(pk=self.u.pk)
    def parcourir(self,js,largeur):
        from playwright.sync_api import sync_playwright,expect
        self.client.force_login(self.u)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                ctx=browser.new_context(java_script_enabled=js,viewport={'width':largeur,'height':900})
                ctx.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':self.client.cookies[settings.SESSION_COOKIE_NAME].value,'url':self.live_server_url}])
                page=ctx.new_page()
                page.goto(self.live_server_url+reverse('acteurs:service',args=[self.service.pk]))
                bloc=page.locator('#service-'+str(self.service.pk)+'-rubriques')
                page.get_by_role('link',name='Choisir les rubriques et les personnes concernées',exact=True).click()
                if js:expect(bloc.locator('[data-parametrage-hote] form')).to_be_visible()
                form=page.locator('#parametrage form')
                form.locator('[name=profil]').select_option('menage')
                form.get_by_role('button',name='Préparer ces réglages',exact=True).click()
                form=page.locator('#parametrage form')
                expect(form.locator('[name=ressources_portee]')).to_have_value('menage')
                form.locator('details.collecte-reglages > summary').click()
                form.locator('[name=logement_portee]').select_option('deux')
                form.locator('[name=logement_population]').select_option('adultes')
                form.locator('[name=couvertures_portee]').select_option('non')
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),largeur+1)
                if os.environ.get('COL6_CAPTURES'):
                    out=Path(os.environ['COL6_CAPTURES']);out.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(out/('rubriques-'+str(largeur)+'.png')),full_page=True)
                form.get_by_role('button',name='Enregistrer',exact=True).click()
                expect(page.get_by_role('link',name='Choisir les rubriques et les personnes concernées',exact=True)).to_be_visible()
                page.goto(self.live_server_url+reverse('dossiers:prise',args=['menage',self.m.pk,self.a.pk]))
                if js:page.locator('[data-condition-volet] > summary').click()
                self.assertEqual(page.locator('#social-'+str(self.p.pk)+'-ressources').count(),0)
                self.assertEqual(page.locator('#social-'+str(self.p.pk)+'-couvertures').count(),0)
                self.assertEqual(page.locator('#social-'+str(self.p.pk)+'-logement').count(),1)
                self.assertEqual(page.get_by_text('Comprendre les actions d’hébergement',exact=True).count(),0)
                if os.environ.get('COL6_CAPTURES'):page.screenshot(path=str(out/('prise-'+str(largeur)+'.png')),full_page=True)
            finally:browser.close()
        self.service.refresh_from_db()
        self.assertEqual(self.service.collecte_rubriques['logement'],{'portee':'deux','population':'adultes'})
        self.assertEqual(self.service.collecte_rubriques['ressources']['portee'],'menage')
    def test_grand_ecran_js(self):self.parcourir(True,1366)
    def test_mobile_sans_js(self):self.parcourir(False,390)
