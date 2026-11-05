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
        self.service.sous_titre = 'Accueil et hébergement des familles'
        self.service.save(update_fields=['sous_titre'])
        from acteurs.models import OffrePrestataire
        from .models import Partenaire
        lieu = Partenaire.objects.create(libelle='Cuisine fictive', cree_par=self.u)
        OffrePrestataire.objects.create(lieu=lieu, libelle='Table d’essai', nature='restauration')
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
                page.goto(self.live_server_url+reverse('acteurs:prestataires'))
                offre = page.locator('.bd-liste-cartes a', has_text='Table d’essai')
                expect(offre.locator('span')).to_contain_text('Cuisine fictive')
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), largeur+1)
                page.goto(self.live_server_url+reverse('acteurs:etablissement', args=[self.service.etablissement_id]))
                carte = page.locator('.bd-liste-cartes a', has_text='Les Amandiers')
                expect(carte.locator('span')).to_have_text(self.service.sous_titre)
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), largeur+1)
                carte.locator('span').click()
                ariane = page.get_by_role('navigation', name='Fil d’Ariane')
                expect(ariane.get_by_role('link', name='Paramétrage')).to_be_visible()
                expect(ariane.locator('[aria-current=page]')).to_have_text('Les Amandiers')
                if js and largeur < 1280:
                    page.get_by_role('button', name='Sommaire', exact=True).click()
                    expect(page.get_by_role('navigation', name='Dans cette page', exact=True)).to_be_visible()
                    page.get_by_role('navigation', name='Dans cette page', exact=True).get_by_role('link', name='Situation sociale et projet', exact=True).click()
                bloc=page.locator('#service-'+str(self.service.pk)+'-rubriques')
                page.get_by_role('link',name='Modifier les rubriques sociales',exact=True).click()
                if js:
                    expect(bloc.locator('[data-parametrage-hote] form')).to_be_visible()
                    page.get_by_role('link', name='Modifier l’accès aux dossiers', exact=True).click()
                    expect(page.locator('#parametrage-editeur [name=politique]')).to_be_visible()
                    expect(bloc.locator('form')).to_have_count(0)
                    page.get_by_role('link', name='Modifier les rubriques sociales', exact=True).click()
                    expect(bloc.locator('form')).to_be_visible()
                form=page.locator('#parametrage form')
                form.locator('[name=profil]').select_option('menage')
                form.get_by_role('button',name='Charger ce profil',exact=True).click()
                form=page.locator('#parametrage form')
                expect(form.locator('[name=ressources_portee]')).to_have_value('menage')
                expect(form.locator('[data-profil-charge]')).to_be_visible()
                form.locator('[name=logement_portee]').select_option('deux')
                form.locator('[name=logement_population]').select_option('adultes')
                form.locator('[name=couvertures_active]').uncheck()
                if js:
                    expect(form.locator('[name=couvertures_portee]')).to_be_hidden()
                    page.get_by_role('link', name='Modifier l’accès aux dossiers', exact=True).click()
                    expect(bloc.locator('h2, h3').first).to_be_focused()
                    expect(bloc.locator('[data-etat-parametrage]')).to_contain_text('avant de changer de rubrique')
                    expect(form.locator('[name=logement_portee]')).to_have_value('deux')
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),largeur+1)
                if os.environ.get('COL6_CAPTURES'):
                    out=Path(os.environ['COL6_CAPTURES']);out.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(out/('rubriques-'+str(largeur)+'.png')),full_page=True)
                form.get_by_role('button',name='Enregistrer',exact=True).click()
                expect(page.get_by_role('link',name='Modifier les rubriques sociales',exact=True)).to_be_visible()
                if js and largeur < 1280:
                    page.get_by_role('navigation', name='Accès rapides dans cette page').get_by_role('link', name='Autorisations').click()
                page.get_by_role('link', name='Modifier l’accès aux dossiers', exact=True).click()
                acces = page.locator('#parametrage form')
                acces.locator('[name=politique]').select_option('lecture')
                acces.get_by_role('button', name='Enregistrer', exact=True).click()
                expect(page.locator('#service-'+str(self.service.pk)+'-acces')).to_contain_text('Lecture collective, écriture sur les dossiers suivis')
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
        self.assertEqual(self.service.collecte_rubriques['couvertures'], {
            'portee': 'non', 'population': 'reference', 'portee_preferee': 'personne',
        })
        self.assertEqual(self.service.politique, 'lecture')
    def test_grand_ecran_js(self):self.parcourir(True,1366)
    def test_mobile_js(self):self.parcourir(True,390)
    def test_mobile_sans_js(self):self.parcourir(False,390)
