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
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                ctx=browser.new_context(java_script_enabled=javascript,viewport={'width':largeur,'height':900})
                ctx.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':self.client.cookies[settings.SESSION_COOKIE_NAME].value,'url':self.live_server_url}])
                page=ctx.new_page();erreurs=[];documents=[]
                page.on('pageerror',lambda e:erreurs.append(str(e)))
                page.goto(self.live_server_url+reverse('dossiers:prise',args=['menage',self.m.pk,self.a.pk])+'?q=Fictif&page=3')
                page.on('request',lambda r:documents.append(r.url) if r.resource_type=='document' else None)
                boite=page.locator('#repas')
                entete=boite.locator(':scope > .boite-entete')
                entete.get_by_role('link',name='Nouvelle période de repas',exact=True).click()
                form=page.locator('#collectif-form form');expect(form).to_be_visible()
                expect(page.locator('[data-prestation-panneau]')).to_have_count(1)
                form.locator('[name=debut]').fill('2026-01-10')
                form.locator('[name=fin_prevue]').fill('2026-01-13')
                form.locator('[name=premier]').select_option('diner')
                form.locator('[name=dernier]').select_option('dejeuner')
                form.locator('[name=prix_adulte]').fill('8')
                form.locator('[name=prix_enfant]').fill('5')
                form.locator('summary',has_text='Choisir un groupe').click()
                form.locator('[name=restreindre]').check()
                form.locator('[name=selection_enfant]').fill('1')
                if javascript:expect(form.locator('[data-collectif-calcul]')).to_contain_text('30.00 EUR')
                else:
                    form.get_by_role('button',name='Calculer',exact=True).click()
                    expect(form.locator('[data-collectif-calcul]')).to_contain_text('30.00 EUR')
                form.get_by_role('button',name='Enregistrer',exact=True).click()
                expect(page.locator('#collectif-form')).to_have_count(0)
                expect(page.locator('[data-prestation-panneau]')).to_have_count(1)
                carte=boite.locator('[data-prestation-carte^="commun:"]')
                expect(carte).to_have_count(1)
                expect(carte.locator('[type=radio]')).to_be_checked()
                page.get_by_role('link',name='Refermer',exact=True).click()
                barre=boite.locator(':scope > .actions-directes')
                barre.get_by_role('link',name='Prolonger',exact=True).click()
                form=page.locator('#collectif-form form');form.locator('[name=date]').fill('2026-01-15')
                form.get_by_role('button',name='Enregistrer',exact=True).click()
                expect(page.locator('#collectif-form')).to_have_count(0)
                expect(carte).to_contain_text('15/01/2026')
                expect(page.get_by_role('navigation',name='Fil d’Ariane')).to_be_visible()
                self.assertIn('q=Fictif',page.url);self.assertIn('page=3',page.url)
                if os.environ.get('COL_CAPTURES'):
                    out=Path(os.environ['COL_CAPTURES']);out.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(out/(f'NAV-unifie-{largeur}-'+('js' if javascript else 'html')+'.png')),full_page=True)
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),largeur+1)
                self.assertEqual(erreurs,[])
                if javascript:self.assertEqual(documents,[])
            finally:browser.close()

    def test_1366_avec_javascript(self):self.parcourir(True,1366)
    def test_390_sans_javascript(self):self.parcourir(False,390)
    def test_390_avec_javascript(self):self.parcourir(True,390)
    def test_1366_sans_javascript(self):self.parcourir(False,1366)




class ParametrageCollectifNavigateur(Donnees,StaticLiveServerTestCase):
    declarer=tests.CollectifsTests.declarer
    restaurer=tests.CollectifsTests.restaurer
    def setUp(self):
        tests.CollectifsTests.setUp(self)
        from django.contrib.auth.models import Permission
        self.u.user_permissions.add(Permission.objects.get(content_type__app_label='acteurs',codename='gerer_organisation'))
        self.u=type(self.u).objects.get(pk=self.u.pk)

    def parcourir(self,largeur):
        from playwright.sync_api import sync_playwright,expect
        import re
        self.client.force_login(self.u)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                ctx=browser.new_context(viewport={'width':largeur,'height':900})
                ctx.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':self.client.cookies[settings.SESSION_COOKIE_NAME].value,'url':self.live_server_url}])
                page=ctx.new_page();erreurs=[];documents=[]
                page.on('pageerror',lambda e:erreurs.append(str(e)))
                page.goto(self.live_server_url+reverse('acteurs:service',args=[self.service.pk]))
                page.on('request',lambda r:documents.append(r.url) if r.resource_type=='document' else None)
                page.get_by_role('navigation',name='Fil d’Ariane').get_by_role('link',name='Paramétrage').click()
                page.get_by_role('link',name='Voir les prestataires',exact=True).click()
                page.get_by_role('link',name='Nouvelle offre',exact=True).click()
                f=page.locator('#parametrage form')
                f.locator('[name=libelle]').fill('Table d’essai')
                f.locator('[name=nouveau_lieu]').fill('Restaurant fictif')
                f.locator('[name=nature]').select_option('restauration')
                f.get_by_role('button',name='Enregistrer',exact=True).click()
                page.get_by_role('link',name='Renseigner un tarif',exact=True).click()
                expect(page.get_by_role('heading',name='Table d’essai',exact=True)).to_be_visible()
                f=page.locator('#parametrage-editeur form')
                f.locator('[name=categorie]').select_option('adulte')
                f.locator('[name=debut]').fill('2026-01-01')
                f.locator('[name=prix]').fill('8');f.locator('[name=prix_diner]').fill('10')
                f.get_by_role('button',name='Enregistrer',exact=True).click()
                expect(page.locator('#parametrage-editeur')).to_have_count(0)
                page.get_by_role('navigation',name='Fil d’Ariane').get_by_role('link',name='Paramétrage').click()
                page.get_by_role('link',name=re.compile('^Les Amandiers')).click()
                page.get_by_role('link', name='Modifier la composition', exact=True).click()
                composition = page.locator('#parametrage-editeur form')
                expect(composition.locator('[name=prestations]')).to_have_count(0)
                composition.locator('[name=identification]').select_option('adultes')
                composition.get_by_role('button', name='Enregistrer', exact=True).click()
                expect(page.locator('#parametrage-editeur')).to_have_count(0)
                expect(page.locator(f'#service-{self.service.pk}-composition')).to_contain_text('Adultes identifiés')
                page.get_by_role('link',name='Modifier les prestations',exact=True).click()
                expect(page.get_by_role('heading',name='Les Amandiers',exact=True)).to_be_visible()
                editeur=page.locator('#parametrage-editeur')
                expect(page.locator('[data-parametrage-bloc] #parametrage-editeur')).to_have_count(1)
                self.assertEqual(editeur.locator('..').get_attribute('id'),'service-'+str(self.service.pk)+'-prestations')
                membres=page.locator('#service-'+str(self.service.pk)+'-membres').element_handle()
                f=editeur.locator('form')
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),largeur+1)
                expect(page.get_by_role('link',name='Modifier les prestations',exact=True)).to_be_hidden()
                expect(f.locator('[name=identification]')).to_have_count(0)
                f.locator('[name=catalogue]').check()
                f.locator('[name=prestations][value=hebergement]').uncheck()
                f.get_by_label('Table d’essai',exact=True).check()
                if os.environ.get('COL_CAPTURES'):
                    out=Path(os.environ['COL_CAPTURES']);out.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(out/f'COL-parametrage-{largeur}.png'),full_page=True)
                f.get_by_role('button',name='Enregistrer',exact=True).click()
                expect(page.locator('#parametrage-editeur')).to_have_count(0)
                self.assertTrue(membres.evaluate('(e)=>e.isConnected'))
                # The access editor opens in its own section, never at page bottom.
                page.get_by_role('link',name='Modifier l’accès aux dossiers',exact=True).click()
                expect(page.locator('#service-'+str(self.service.pk)+'-acces #parametrage-editeur')).to_be_visible()
                page.locator('#parametrage-editeur').get_by_role('link',name='Annuler',exact=True).click()
                expect(page.locator('#parametrage-editeur')).to_have_count(0)
                self.assertEqual(erreurs,[])
                self.assertEqual(len(documents),4)
            finally:browser.close()
        self.service.refresh_from_db();self.assertTrue(self.service.catalogue_prestations)
        self.assertEqual(self.service.profil_collectif['prestations'],['restauration'])
        self.assertEqual(self.service.profil_collectif['identification'], 'adultes')

    def test_390(self):self.parcourir(390)
    def test_1366(self):self.parcourir(1366)
