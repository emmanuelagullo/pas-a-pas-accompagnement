"""Recette réelle Chromium des modifications sur place dans Évolution.

PWA_CHROMIUM=/chemin/chromium python3 manage.py test personnes.qualification_evolution
Données et serveur isolés par Django ; aucune instance existante modifiée.
"""
import os
from datetime import date
from unittest import skipUnless
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from . import models as m, social, suivi


@skipUnless(os.environ.get('PWA_CHROMIUM'), 'Chromium non configuré : aucune observation navigateur.')
class EvolutionNavigateur(StaticLiveServerTestCase):
    def setUp(self):
        from playwright.sync_api import sync_playwright
        self.u = get_user_model().objects.create_superuser('evolution-fictive', password='Fictif-Evolution-2026!')
        self.p = m.Personne.objects.create(designation='Maïa fictive', cree_par=self.u)
        self.m = suivi.creer_menage(self.u, 'Les Passerelles — fictif', [self.p], date(2026,1,1))
        self.a = suivi.ouvrir(self.u, self.m, [self.p], date(2026,1,1))
        self.e = social.evenement(self.u, self.a, self.p, date(2026,2,1), 'Événement fictif à corriger', 'Source fictive')
        from . import repas
        self.accord_repas = repas.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,3,1),'dejeuner')
        self.distribution = repas.distribuer(self.u,self.accord_repas,self.p,date(2026,2,2),1,'Jeune fictif')
        from . import financements
        from decimal import Decimal
        self.tarif_correction = financements.definir_tarif(self.u,financements.creation_tarif(),'Définition fictive',
            debut=date(2026,1,1),fin=None,libelle='Repas fictif',unite='repas',categorie='',montant=Decimal('25'),devise='EUR',prestataire=None,actif=True,source='Convention fictive')
        self.pw = sync_playwright().start(); self.addCleanup(self.pw.stop)
        self.browser = self.pw.chromium.launch(executable_path=os.environ['PWA_CHROMIUM'], args=['--no-sandbox'])
        self.addCleanup(self.browser.close)
        self.url = reverse('dossiers:detail', args=['personne',self.p.pk])
        self.errors = []

    def page(self, **kwargs):
        page = self.browser.new_page(**kwargs)
        page.on('pageerror', lambda error: self.errors.append(str(error)))
        page.goto(self.live_server_url + self.url)
        page.locator('[name="username"]').fill('evolution-fictive')
        page.locator('[name="password"]').fill('Fictif-Evolution-2026!')
        page.get_by_role('button', name='Se connecter', exact=True).click()
        page.wait_for_url('**' + self.url + '*')
        return page

    def test_options_et_correction_sur_place_bureau_mobile_clavier(self):
        from playwright.sync_api import expect
        page = self.page(viewport={'width':1280,'height':900})
        bouton = page.locator('[data-condition-options-bouton]')
        expect(bouton).to_have_attribute('aria-expanded','false')
        bouton.focus(); page.keyboard.press('Enter')
        expect(bouton).to_have_attribute('aria-expanded','true')
        page.locator('[data-condition-evolution]').click()
        expect(page.locator('[data-condition-trajectoire]')).to_be_visible()
        expect(bouton).to_have_attribute('aria-expanded','false')
        bouton.click()
        expect(page.locator('[data-evolution-selection]')).to_be_visible()
        bouton.click()
        ligne = page.locator(f'#evolution-evenement-{self.e.pk}')
        ligne.get_by_role('link', name='Modifier', exact=True).click()
        expect(ligne.locator('[data-condition-form]')).to_be_visible()
        ligne.locator('[data-condition-annuler]').click()
        expect(ligne.locator('[data-condition-form]')).to_have_count(0)
        ligne.locator('details').evaluate('(d) => d.open = true')
        ligne.get_by_role('link', name='Modifier', exact=True).click()
        ligne.locator('[name="date_effet"]').fill('2026-02-03')
        ligne.locator('[name="texte"]').fill('Événement fictif corrigé sur place')
        expect(ligne.locator('[name="motif"]')).not_to_be_visible()
        original = page.url
        ligne.get_by_role('button', name='Enregistrer', exact=True).click()
        expect(page.locator('[data-condition-statut]')).to_have_text('Modification enregistrée.')
        self.assertEqual(page.url, original)
        expect(page.locator('[data-condition-evolution]')).to_be_checked()
        expect(ligne.locator('details')).to_have_attribute('open','')
        expect(ligne).to_contain_text('03/02/2026')
        expect(ligne).to_contain_text('Événement fictif corrigé sur place')
        page.locator('[data-condition-revenir]').click()
        expect(bouton).to_have_attribute('aria-expanded','true')
        page.reload()
        expect(bouton).to_have_attribute('aria-expanded','true')
        page.set_viewport_size({'width':390,'height':844})
        page.locator('[data-condition-evolution]').click()
        expect(page.locator('[data-condition-trajectoire]')).to_be_visible()
        bouton.click()
        radios = page.locator('.condition-modes').bounding_box()
        commande = bouton.bounding_box()
        self.assertLess(commande['y'], radios['y'] + radios['height'])
        labels = page.locator('.condition-modes label')
        self.assertLess(abs(labels.nth(0).bounding_box()['y'] - labels.nth(1).bounding_box()['y']), 1)
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), 391)
        self.assertEqual(self.errors, [])
        page.screenshot(path='/tmp/evolution-options-mobile.png', full_page=True)

    def test_options_sans_javascript(self):
        from playwright.sync_api import expect
        page = self.page(java_script_enabled=False, viewport={'width':390,'height':844})
        options = page.locator('#options-situation')
        expect(options).not_to_have_attribute('open','')
        options.locator('summary').first.click()
        expect(page.locator('[data-condition-selection]')).to_be_visible()
        page.get_by_role('link', name='Consulter l’évolution', exact=True).click()
        options = page.locator('#options-evolution')
        options.locator('summary').first.click()
        expect(page.locator('[data-evolution-selection]')).to_be_visible()
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), 391)

    def test_repas_categorie_visible_et_correction_sans_motif(self):
        from playwright.sync_api import expect
        accord, distribution = self.accord_repas, self.distribution
        page = self.page(viewport={'width':1280,'height':900})
        options = page.locator('[data-condition-options-bouton]')
        indicateur = options.locator('[aria-hidden=true]')
        self.assertIn('▸',indicateur.evaluate("e => getComputedStyle(e,'::before').content"))
        options.click()
        self.assertIn('▾',indicateur.evaluate("e => getComputedStyle(e,'::before').content"))
        page.locator('[data-condition-evolution]').click()
        ligne = page.locator(f'#evolution-repas-{distribution.pk}')
        ligne.get_by_role('link',name='Modifier',exact=True).click()
        expect(ligne.locator('[name=categorie_declaree]')).to_be_visible()
        expect(ligne.locator('[name=categorie_declaree]')).to_have_value('Jeune fictif')
        expect(ligne.locator('[name=motif]')).not_to_be_visible()
        ligne.locator('[name=quantite]').fill('2')
        ligne.get_by_role('button',name='Enregistrer',exact=True).click()
        expect(page.locator('[data-condition-statut]')).to_have_text('Modification enregistrée.')
        expect(ligne).to_contain_text('2 ×')
        page.goto(self.live_server_url + reverse('dossiers:corriger_distribution',args=[distribution.pk]))
        expect(page.locator('[name=categorie_declaree]')).to_have_value('Jeune fictif')
        expect(page.locator('[name=quantite]')).to_have_value('2')
        expect(page.locator('[name=motif]')).not_to_be_visible()
        page.goto(self.live_server_url + reverse('suivi:distribuer_repas',args=[accord.pk]))
        expect(page.locator('[name=categorie_declaree]')).to_be_visible()
        expect(page.locator('[name=categorie_declaree]')).to_have_value('')
        self.assertIn('Jeune fictif',page.locator('datalist').first.inner_html())
        self.assertEqual(self.errors,[])
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path='/tmp/repas-categories-mobile.png',full_page=True)

    def test_aide_frise_sans_deplacement_et_fermeture_echap(self):
        from playwright.sync_api import expect
        page=self.page(viewport={'width':1280,'height':900})
        label=page.locator('[data-frise-explication]:visible').first
        label.scroll_into_view_if_needed()
        bulle=label.locator('.frise-explication')
        avant=label.bounding_box()
        label.hover()
        expect(bulle).to_be_visible()
        apres=label.bounding_box()
        self.assertEqual(avant,apres)
        bulle.hover()
        expect(bulle).to_be_visible()
        page.keyboard.press('Escape')
        expect(bulle).not_to_be_visible()
        page.mouse.move(0,0)
        label.locator('input').focus()
        expect(bulle).to_be_visible()
        page.keyboard.press('Escape')
        expect(bulle).not_to_be_visible()
        page.goto(self.live_server_url + '/')
        page.set_viewport_size({'width':390,'height':844})
        label.locator('input').blur()
        label.hover()
        expect(bulle).to_be_visible()
        box=bulle.bounding_box()
        self.assertGreaterEqual(box['x'],0)
        self.assertLessEqual(box['x']+box['width'],390)
        page.screenshot(path='/tmp/frise-aide-mobile.png',full_page=True)
        mobile=self.page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        mobile.goto(self.live_server_url + '/')
        choix=mobile.locator('[data-frise-explication]:visible').first
        choix.locator('input').tap()
        expect(choix.locator('input')).to_be_checked()
        expect(choix.locator('.frise-explication')).not_to_be_visible()
        self.assertEqual(self.errors,[])

    def test_correction_tarif_motif_conditionnel_et_repli_sans_javascript(self):
        from playwright.sync_api import expect
        url=self.live_server_url + reverse('dossiers:tarif',args=[self.tarif_correction.pk])
        page=self.page(viewport={'width':1280,'height':900})
        page.goto(url)
        choix=page.locator('[name=action]')
        motif=page.locator('[name=motif]')
        expect(motif).to_be_visible()
        self.assertTrue(motif.evaluate('(e) => e.required'))
        choix.select_option('correction')
        expect(motif).not_to_be_visible()
        self.assertFalse(motif.evaluate('(e) => e.required'))
        page.locator('[name=montant]').fill('28')
        page.get_by_role('button',name='Enregistrer',exact=True).click()
        page.wait_for_url('**' + reverse('dossiers:tarifs'))
        page.goto(url)
        expect(page.locator('[name=montant]')).to_have_value('28,0000')
        choix.select_option('correction')
        expect(motif).not_to_be_visible()
        choix.select_option('changement')
        expect(motif).to_be_visible()
        self.assertTrue(motif.evaluate('(e) => e.required'))
        page.set_viewport_size({'width':390,'height':844})
        choix.select_option('correction')
        expect(motif).not_to_be_visible()
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),391)
        page.screenshot(path='/tmp/correction-tarif-mobile.png',full_page=True)
        sansjs=self.page(java_script_enabled=False,viewport={'width':390,'height':844})
        sansjs.goto(url)
        sansjs.locator('[name=action]').select_option('correction')
        sansjs.locator('[name=montant]').fill('29')
        sansjs.get_by_role('button',name='Enregistrer',exact=True).click()
        sansjs.wait_for_url('**' + reverse('dossiers:tarifs'))
        sansjs.goto(url)
        expect(sansjs.locator('[name=montant]')).to_have_value('29,0000')
        self.assertEqual(self.errors,[])
