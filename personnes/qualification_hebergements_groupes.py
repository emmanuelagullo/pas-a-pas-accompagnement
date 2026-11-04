"""NAV9 : carte commune et actions explicites, vrai Chromium."""
from datetime import timedelta
from unittest import skipIf
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from . import qualification_navigateur as q, qualification_prestations_navigation as precedent
from . import models as m

@skipIf(q.sync_playwright is None,'Playwright non installé.')
class HebergementsGroupesNavigateur(StaticLiveServerTestCase):
    navigateur=q.ProfilsNavigateur.navigateur
    capture=precedent.PrestationsNavigationNavigateur.capture
    def setUp(self):
        precedent.PrestationsNavigationNavigateur.setUp(self)
        self.membres=[]
        for nom in ['Samira fictive','Enfant fictif']:
            p=m.Personne.objects.create(designation=nom,cree_par=self.u)
            self.a.beneficiaires.add(p);self.s2.accord.beneficiaires.add(p)
            s=m.Sejour.objects.create(accord=self.s2.accord,debut=self.s2.debut,cree_par=self.u)
            s.beneficiaires.add(p);self.membres.append((p,s))

    def test_groupe_ouverture_individuelle_et_sortie_ciblee(self):
        from playwright.sync_api import expect
        page=self.navigateur();page.goto(self.url)
        groupe=page.locator('[data-hebergement-groupe]')
        expect(groupe).to_have_count(1)
        expect(groupe.locator('.hebergement-individuels')).not_to_have_attribute('open','')
        for largeur in [390,1366]:
            page.set_viewport_size({'width':largeur,'height':900})
            groupe.scroll_into_view_if_needed();self.capture(page,'NAV09-hebergement-commun-'+str(largeur))
            self.assertTrue(page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        page.set_viewport_size({'width':390,'height':900})
        groupe.locator(':scope > a.prestation-consulter').click()
        expect(groupe.locator('[data-prestation-panneau]')).to_be_visible()
        expect(page.get_by_role('navigation',name='Accès rapides dans cette page').get_by_role('link',name='Prestations',exact=True)).to_have_attribute('aria-current','location')
        page.set_viewport_size({'width':1366,'height':900})
        expect(page.get_by_role('navigation',name='Fil d’Ariane')).to_be_visible()
        groupe.get_by_role('link',name='Refermer',exact=True).click()
        expect(groupe.locator('[data-prestation-panneau]')).to_have_count(0)
        # Lien direct : la cible individuelle reste atteignable sans ouvrir à la main.
        enfant=self.membres[0][1]
        page.goto(self.url+'?prestation=sejour:'+str(enfant.pk))
        expect(page.locator('#prestation-sejour-'+str(enfant.pk))).to_be_visible()
        page.locator('[data-prestation-panneau]').get_by_role('link',name='Refermer',exact=True).click()
        groupe.get_by_role('link',name='Agir sur les personnes…',exact=True).click()
        form=groupe.locator('[data-prestation-form]')
        expect(form).to_be_visible()
        form.locator('[name=action]').select_option('sortie')
        form.locator('[name=sejours][value="'+str(enfant.pk)+'"]').check()
        form.locator('[name=date]').fill((self.entree+timedelta(days=5)).isoformat())
        form.get_by_role('button',name='Enregistrer',exact=True).click()
        expect(page.locator('[data-prestation-form]')).to_have_count(0)
        expect(groupe.locator(':scope > a.prestation-consulter')).to_contain_text('Fins de séjour différentes')
        self.capture(page,'NAV09-sortie-individuelle')

    def test_sans_javascript(self):
        from playwright.sync_api import expect
        page=self.navigateur();contexte=page.context
        browser=contexte.browser
        sans=browser.new_context(java_script_enabled=False)
        self.addCleanup(sans.close)
        sans.add_cookies(contexte.cookies())
        page=sans.new_page();page.goto(self.url)
        groupe=page.locator('[data-hebergement-groupe]')
        groupe.locator('.hebergement-individuels > summary').click()
        groupe.locator('.prestation-ligne a.prestation-consulter').first.click()
        expect(page.locator('[data-prestation-panneau]')).to_be_visible()
