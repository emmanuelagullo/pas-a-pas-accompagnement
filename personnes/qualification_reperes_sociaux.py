"""NAV10 : aperçu replié, vraie saisie et changement de vue dans Chromium."""
import os
from pathlib import Path
from unittest import skipIf
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from . import qualification_navigateur as q

@skipIf(q.sync_playwright is None,'Playwright non installé.')
class ReperesSociauxNavigateur(StaticLiveServerTestCase):
    setUp=q.ConditionSocialeNavigateur.setUp
    navigateur=q.ProfilsNavigateur.navigateur

    def capture(self,page,nom):
        if os.environ.get('REPERES_CAPTURES'):
            dossier=Path(os.environ['REPERES_CAPTURES']);dossier.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(dossier/nom))

    def ouvrir(self,page):
        volet=page.locator('[data-condition-volet]')
        if volet.get_attribute('open') is None:volet.locator(':scope > summary').click()
        return volet

    def test_dispositions_date_et_menage(self):
        from playwright.sync_api import expect
        from . import models as m
        autre=m.Personne.objects.create(designation='Samira fictive',cree_par=self.u)
        m.Appartenance.objects.create(menage=self.m,personne=autre,debut=self.entree)
        page=self.navigateur()
        for nature in ['personne','menage']:
            page.goto(self.live_server_url+reverse('dossiers:detail',args=[nature,self.p.pk if nature=='personne' else self.m.pk]))
            volet=page.locator('[data-condition-volet]')
            if volet.get_attribute('open') is not None:volet.locator(':scope > summary').click()
            apercu=page.locator('#condition-volet-apercu')
            expect(apercu).to_be_visible();expect(apercu).to_contain_text('avec des informations')
            for largeur in [390,1366]:
                page.set_viewport_size({'width':largeur,'height':900})
                volet.scroll_into_view_if_needed()
                self.assertTrue(page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                self.capture(page,'NAV10-'+nature+'-'+str(largeur)+'.png')
            page.set_viewport_size({'width':640,'height':900})
            page.evaluate("document.documentElement.style.fontSize='200%'")
            self.assertTrue(page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            volet.locator(':scope > summary').focus();page.keyboard.press('Enter')
            expect(apercu).to_be_hidden()
            volet.locator(':scope > summary').focus();page.keyboard.press('Enter')
            expect(apercu).to_be_visible()

    def test_annulation_enregistrement_et_retrait_actualisent_le_compteur(self):
        from playwright.sync_api import expect
        page=self.navigateur();page.goto(self.live_server_url+reverse('dossiers:detail',args=['personne',self.p.pk]))
        self.ouvrir(page)
        compteur=page.locator('[data-condition-reperes-personne]');avant=compteur.inner_text()
        groupe=page.locator('#social-'+str(self.p.pk)+'-logement')
        groupe.locator(':scope > summary').click()
        groupe.get_by_role('link',name='Renseigner',exact=True).click()
        groupe.get_by_role('button',name='Annuler',exact=True).click()
        expect(compteur).to_have_text(avant)
        groupe.get_by_role('link',name='Renseigner',exact=True).click()
        form=groupe.locator('form[data-condition-form]')
        form.locator('[name=valeur]').select_option('logement_autonome')
        form.get_by_role('button',name='Enregistrer',exact=True).click()
        expect(form).to_have_count(0)
        self.assertEqual(int(compteur.inner_text().split()[0]),int(avant.split()[0])+1)
        groupe.locator('.condition-actions summary').click()
        groupe.get_by_role('link',name='Retirer ce changement',exact=True).click()
        form=groupe.locator('form[data-condition-form]');form.locator('[name=confirmer]').check()
        form.get_by_role('button',name='Enregistrer',exact=True).click()
        expect(form).to_have_count(0);expect(compteur).to_have_text(avant)

    def test_evolution_et_retour_situation(self):
        from playwright.sync_api import expect
        page=self.navigateur();page.goto(self.live_server_url+reverse('dossiers:prise',args=['menage',self.m.pk,self.a.pk]))
        volet=self.ouvrir(page)
        page.locator('[data-condition-evolution]').click()
        expect(page.locator('[data-condition-reperes-evolution]')).to_contain_text('Évolution du')
        volet.locator(':scope > summary').click()
        expect(page.locator('[data-condition-reperes-evolution]')).to_be_visible()
        expect(page.locator('[data-condition-reperes-situation]')).to_be_hidden()
        self.capture(page,'NAV10-evolution.png')
        self.ouvrir(page);page.locator('[data-condition-revenir]').click()
        volet.locator(':scope > summary').click()
        expect(page.locator('[data-condition-reperes-situation]')).to_be_visible()

    def test_repli_sans_javascript(self):
        from playwright.sync_api import expect
        premiere=self.navigateur()
        contexte=premiere.context.browser.new_context(java_script_enabled=False)
        self.addCleanup(contexte.close);contexte.add_cookies(premiere.context.cookies())
        page=contexte.new_page();page.goto(self.live_server_url+reverse('dossiers:detail',args=['personne',self.p.pk]))
        volet=page.locator('[data-condition-volet]')
        expect(page.locator('[data-condition-reperes-personne]')).to_be_visible()
        volet.locator(':scope > summary').click()
        expect(page.locator('#condition-volet-apercu')).to_be_visible()
        expect(page.locator('#condition-volet-apercu')).to_contain_text('avec des informations')
