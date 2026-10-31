"""NAV6 : sélection explicite, consultation et édition dans une colonne."""
import os
from pathlib import Path
from datetime import timedelta
from unittest import skipIf
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from . import qualification_navigateur as q
from . import models as m, hebergement as h, repas

@skipIf(q.sync_playwright is None, 'Playwright non installé.')
class PrestationsNavigationNavigateur(StaticLiveServerTestCase):
    navigateur = q.ProfilsNavigateur.navigateur

    def setUp(self):
        q.ConditionSocialeNavigateur.setUp(self)
        accord = h.accorder(self.u, self.a, [self.p], self.entree, None)
        self.s = h.admettre(self.u, accord, [self.p], self.entree)
        h.sortir(self.u, self.s, self.entree + timedelta(days=2))
        self.s2 = h.admettre(self.u, accord, [self.p], self.entree + timedelta(days=3))
        self.r = repas.accorder(self.u, self.a, [self.p], self.entree, None, 'diner')
        self.r2 = repas.accorder(self.u, self.a, [self.p], self.entree, None, 'dejeuner')
        t = m.TypeAide.objects.create(nature='transport', libelle='Ticket fictif', unite='ticket', cree_par=self.u)
        self.aides = []
        for numero in range(2):
            a = m.AccordAide.objects.create(accompagnement=self.a, type_aide=t, nature=t.nature,
                libelle=('Titre-très-long-' + 'Voyage'*20) if numero == 0 else 'Transport fictif 1', unite=t.unite, debut=self.entree,
                quantite=10, source='Recette fictive', cree_par=self.u)
            a.beneficiaires.add(self.p); self.aides.append(a)
        self.url = self.live_server_url + reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk])

    def capture(self, page, nom):
        if os.environ.get('PRESTATIONS_CAPTURES'):
            p=Path(os.environ['PRESTATIONS_CAPTURES']); p.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(p / (nom + '.png')))

    def test_selection_consultation_retour_et_dispositions(self):
        from playwright.sync_api import expect
        page = self.navigateur()
        page.goto(self.url + '?q=Martin&page=2#titre-prestations')
        for largeur in [390, 1366, 1920, 640]:
            page.set_viewport_size({'width':largeur,'height':900})
            hbox, rbox = page.locator('#hebergement'), page.locator('#repas')
            self.assertAlmostEqual(hbox.bounding_box()['x'], rbox.bounding_box()['x'], delta=2)
            self.assertGreater(rbox.bounding_box()['y'], hbox.bounding_box()['y'] + hbox.bounding_box()['height'] - 2)
            self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            if largeur in (390, 1366):
                hbox.scroll_into_view_if_needed(); self.capture(page, 'NAV06-prestations-' + str(largeur))
        for code, valeur in [('hebergement',str(self.s.pk)), ('repas',str(self.r.pk)), ('aides-transport',str(self.aides[1].pk))]:
            boite = page.locator('#' + code)
            radio = boite.locator('[data-prestation-url][value="' + valeur + '"]')
            radio.check()
            expect(radio).to_be_checked()
            expect(boite.locator('.selectionnee [data-prestation-url]')).to_have_value(valeur)
            lien = radio.locator('xpath=../..').locator('a.prestation-consulter')
            destination = lien.get_attribute('href')
            lien.click()
            expect(page.locator('.operation-en-place')).to_have_count(0)
            expect(page.locator('h1')).to_be_visible()
            self.assertIn(destination.split('?')[0], page.url)
            retour = page.locator('a').filter(has_text='Revenir à la prise en charge').first
            if not retour.count(): retour = page.get_by_role('link', name='Retour au dossier — sélection conservée', exact=True)
            retour.click()
            expect(page.locator('#' + code + ' [data-prestation-url][value="' + valeur + '"]')).to_be_checked()
        self.assertIn('page=2', page.get_by_role('link', name='Dossiers', exact=True).first.get_attribute('href'))

    def test_saisie_sur_place_erreurs_annulation_et_enregistrement(self):
        from playwright.sync_api import expect
        page = self.navigateur(); page.set_viewport_size({'width':1366,'height':900}); page.goto(self.url + '#repas')
        boite = page.locator('#repas')
        boite.get_by_role('link', name='Enregistrer une distribution', exact=True).click()
        panneau = boite.locator('.operation-en-place')
        expect(panneau).to_be_visible()
        expect(page.get_by_role('navigation', name='Dans cette page', exact=True).get_by_role('link', name='Prestations', exact=True)).to_have_attribute('aria-current', 'location')
        self.assertGreater(panneau.bounding_box()['width'], 700)
        panneau.get_by_role('button', name='← Revenir à la liste', exact=True).click()
        expect(panneau).to_have_count(0)
        boite.get_by_role('link', name='Enregistrer une distribution', exact=True).click()
        form = boite.locator('.operation-en-place form').last
        expect(form).to_be_visible()
        expect(page.get_by_role('navigation', name='Dans cette page', exact=True).get_by_role('link', name='Prestations', exact=True)).to_have_attribute('aria-current', 'location')
        # Contrôler le formulaire réel sans forcer un champ masqué.
        self.capture(page, 'NAV06-edition-sur-place')
        form.locator('[name=quantite]').fill('2')
        form.locator('[name=date]').fill(self.entree.isoformat())
        form.locator('[name=beneficiaire]').select_option(str(self.p.pk))
        autre = page.locator('#hebergement input[value="' + str(self.s.pk) + '"]')
        autre.click()
        expect(autre).not_to_be_checked()
        expect(form.locator('[name=quantite]')).to_have_value('2')
        expect(page.locator('#etat-dossier')).to_contain_text('Terminez ou annulez')
        form.locator('[name=date]').fill((self.entree - timedelta(days=1)).isoformat())
        form.get_by_role('button', name='Enregistrer', exact=True).click()
        expect(form.locator('.errorlist').first).to_be_visible()
        form.locator('[name=date]').fill(self.entree.isoformat())
        form.get_by_role('button', name='Enregistrer', exact=True).click()
        expect(boite.locator('.operation-en-place')).to_have_count(0)
        expect(page.get_by_text('Dossier actualisé.', exact=True)).to_be_visible()

    def test_sans_javascript_selection_et_consultation(self):
        from playwright.sync_api import expect
        original=self.navigateur()
        contexte=original.context.browser.new_context(storage_state=original.context.storage_state(), java_script_enabled=False,
            viewport={'width':390,'height':844})
        self.addCleanup(contexte.close); page=contexte.new_page(); page.goto(self.url)
        for code, valeur in [('hebergement',str(self.s.pk)),('repas',str(self.r.pk)),('aides-transport',str(self.aides[1].pk))]:
            boite=page.locator('#'+code)
            radio=boite.locator('[data-prestation-url][value="'+valeur+'"]')
            radio.check(); boite.locator('[data-prestation-selection-valider]').click()
            expect(radio).to_be_checked()
            self.assertEqual(page.locator('#hebergement input:checked').input_value(), str(self.s.pk))
        page.locator('#aides-transport .selectionnee a.prestation-consulter').click()
        expect(page.get_by_role('heading', name='Transport — Transport fictif 1', exact=True)).to_be_visible()
