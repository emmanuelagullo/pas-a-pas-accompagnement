"""NAV7 : une prestation ouverte dans Form3, sans remplacement de sa catégorie."""
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
        self.autres_aides=[]
        for code,libelle in m.TypeAide.NATURES[1:]:
            type_aide=m.TypeAide.objects.create(nature=code,libelle=libelle+' fictif',unite='unité',cree_par=self.u)
            aide=m.AccordAide.objects.create(accompagnement=self.a,type_aide=type_aide,nature=code,libelle=type_aide.libelle,unite='unité',debut=self.entree,source='Recette fictive',cree_par=self.u)
            aide.beneficiaires.add(self.p);self.autres_aides.append(aide)
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
                hbox.scroll_into_view_if_needed(); self.capture(page, 'NAV07-prestations-' + str(largeur))
        cadre=page.locator('#hebergement').element_handle()
        for code, valeur in [('hebergement',str(self.s.pk)), ('repas',str(self.r.pk)), ('aides-transport',str(self.aides[1].pk))]+[('aides-'+a.nature,str(a.pk)) for a in self.autres_aides]:
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
            self.assertTrue(cadre.evaluate('e=>e.isConnected'))
            expect(page.get_by_role('navigation', name='Fil d’Ariane')).to_be_visible()
            if code == 'hebergement':
                for largeur in [390,1366]:
                    page.set_viewport_size({'width':largeur,'height':900})
                    page.locator('[data-prestation-panneau]').scroll_into_view_if_needed()
                    self.capture(page,'NAV07-sejour-ouvert-'+str(largeur))
                panneau=page.locator('[data-prestation-panneau]')
                with page.expect_popup() as impression:
                    panneau.get_by_role('link',name='Imprimer / PDF',exact=True).click()
                imprime=impression.value;imprime.wait_for_load_state()
                imprime.emulate_media(media='print')
                expect(imprime.locator('.prestation-impression')).to_be_visible()
                expect(imprime.locator('#repas')).to_be_hidden()
                self.capture(imprime,'NAV07-impression-prestation')
                if os.environ.get('PRESTATIONS_CAPTURES'): imprime.pdf(path=str(Path(os.environ['PRESTATIONS_CAPTURES'])/'NAV07-impression-prestation.pdf'))
                imprime.close()
            expect(page.locator('#hebergement')).to_be_visible()
            retour = page.get_by_role('link', name='Refermer', exact=True)
            retour.click()
            expect(page.locator('[data-prestation-panneau]')).to_have_count(0)
            expect(page.locator('#' + code + ' [data-prestation-url][value="' + valeur + '"]')).to_be_checked()
        self.assertIn('page=2', page.get_by_role('link', name='Dossiers', exact=True).first.get_attribute('href'))

    def test_saisie_sur_place_erreurs_annulation_et_enregistrement(self):
        from playwright.sync_api import expect
        page = self.navigateur(); page.set_viewport_size({'width':1366,'height':900}); page.goto(self.url + '#repas')
        boite = page.locator('#repas')
        boite.get_by_role('link', name='Enregistrer une distribution', exact=True).first.click()
        panneau = boite.locator('.operation-en-place')
        expect(panneau).to_be_visible()
        expect(page.get_by_role('navigation', name='Dans cette page', exact=True).get_by_role('link', name='Prestations', exact=True)).to_have_attribute('aria-current', 'location')
        self.assertGreater(panneau.bounding_box()['width'], 700)
        boite.get_by_role('link', name='Annuler et revenir à la prestation', exact=True).click()
        expect(panneau).to_have_count(0)
        boite.get_by_role('link', name='Enregistrer une distribution', exact=True).first.click()
        form = boite.locator('.operation-en-place form').last
        expect(form).to_be_visible()
        expect(page.get_by_role('navigation', name='Dans cette page', exact=True).get_by_role('link', name='Prestations', exact=True)).to_have_attribute('aria-current', 'location')
        # Contrôler le formulaire réel sans forcer un champ masqué.
        self.capture(page, 'NAV07-edition-sur-place')
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
        expect(page.get_by_text('Modification enregistrée.', exact=True)).to_be_visible()

    def test_sans_javascript_selection_et_consultation(self):
        from playwright.sync_api import expect
        original=self.navigateur()
        contexte=original.context.browser.new_context(storage_state=original.context.storage_state(), java_script_enabled=False,
            viewport={'width':390,'height':844})
        self.addCleanup(contexte.close); page=contexte.new_page(); page.goto(self.url)
        for code, valeur in [('hebergement',str(self.s.pk)),('repas',str(self.r.pk)),('aides-transport',str(self.aides[1].pk))]+[('aides-'+a.nature,str(a.pk)) for a in self.autres_aides]:
            boite=page.locator('#'+code)
            radio=boite.locator('[data-prestation-url][value="'+valeur+'"]')
            radio.check(); boite.locator('[data-prestation-selection-valider]').click()
            expect(radio).to_be_checked()
            self.assertEqual(page.locator('#hebergement input:checked').input_value(), str(self.s.pk))
        page.locator('#aides-transport .selectionnee a.prestation-consulter').click()
        expect(page.get_by_role('heading', name='Transport — Transport fictif 1', exact=True)).to_be_visible()
        expect(page.get_by_role('navigation', name='Fil d’Ariane')).to_be_visible()

    def test_notes_de_prestation_publication_sur_place(self):
        from playwright.sync_api import expect
        page=self.navigateur()
        page.goto(self.url+'?prestation=repas:'+str(self.r.pk))
        panneau=page.locator('[data-prestation-panneau]')
        panneau.get_by_role('link',name='Notes de la prestation').click()
        panneau.get_by_role('button',name='Écrire un message',exact=True).click()
        editeur=panneau.locator('.ProseMirror')
        expect(editeur).to_be_visible()
        editeur.fill('Message fictif de recette NAV7')
        panneau.get_by_role('button',name='Publier le message').click()
        expect(panneau.locator('.liaisons-fil').get_by_text('Message fictif de recette NAV7',exact=True)).to_be_visible()
        expect(page.get_by_role('navigation',name='Fil d’Ariane')).to_be_visible()
        self.assertIn('/prises/',page.url)


    def test_creation_prevision_et_arrivee_dans_nav(self):
        from playwright.sync_api import expect
        page=self.navigateur();page.set_viewport_size({'width':390,'height':900})
        page.goto(self.url+'?q=Martin&page=2')
        boite=page.locator('#hebergement')
        cadre=boite.element_handle()
        boite.locator(':scope > .boite-entete').get_by_role('link',name='Nouveau séjour',exact=True).click()
        form=boite.locator('[data-prestation-form]')
        expect(form).to_be_visible()
        form.get_by_label('Arrivée déjà effectuée',exact=False).uncheck()
        form.get_by_role('button',name='Enregistrer le séjour',exact=True).click()
        expect(boite.locator('[data-prestation-form]')).to_have_count(0)
        expect(boite).to_contain_text('Prévu — arrivée à confirmer')
        page.get_by_role('link',name='Refermer',exact=True).click()
        boite.get_by_role('link',name='Enregistrer l’arrivée',exact=True).click()
        form=boite.locator('[data-prestation-form]')
        expect(form).to_be_visible()
        form.get_by_role('button',name='Enregistrer l’arrivée',exact=True).click()
        expect(boite.locator('[data-prestation-form]')).to_have_count(0)
        expect(boite.get_by_text('Prévu — arrivée à confirmer',exact=True)).to_have_count(0)
        self.assertTrue(cadre.evaluate('(e)=>e.isConnected'))
        self.assertIn('page=2',page.url)
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),390)
