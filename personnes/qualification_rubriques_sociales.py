"""NAV3 : dépliants natifs, aperçus, mémoire locale et édition réelle."""
import os
from datetime import timedelta
from pathlib import Path
from unittest import skipIf
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from . import models as m
from . import qualification_navigateur as q

@skipIf(q.sync_playwright is None, 'Playwright non installé.')
class RubriquesSocialesNavigateur(StaticLiveServerTestCase):
    setUp = q.ConditionSocialeNavigateur.setUp
    navigateur = q.ProfilsNavigateur.navigateur

    def url(self, nature='personne', prise=False):
        pk = self.p.pk if nature == 'personne' else self.m.pk
        return self.live_server_url + reverse('dossiers:prise' if prise else 'dossiers:detail',
            args=[nature, pk, self.a.pk] if prise else [nature, pk])

    def capture(self, page, nom):
        destination = os.environ.get('RUBRIQUES_CAPTURES')
        if destination:
            Path(destination).mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(Path(destination) / (nom + '.png')))

    def test_volet_clavier_memoire_liens_et_impression(self):
        from playwright.sync_api import expect
        page = self.navigateur()
        page.goto(self.url())
        volet = page.locator('[data-condition-volet]')
        expect(volet).not_to_have_attribute('open', '')
        volet.scroll_into_view_if_needed()
        self.capture(page, 'NAV04-volet-replie')
        volet.locator(':scope > summary').focus()
        page.keyboard.press('Enter')
        expect(volet).to_have_attribute('open', '')
        expect(page.locator('[data-condition-repli][open]')).to_have_count(0)
        groupe = page.locator('#social-' + str(self.p.pk) + '-coordonnees')
        groupe.locator(':scope > summary').click()
        volet.locator(':scope > summary').click()
        page.reload()
        expect(volet).not_to_have_attribute('open', '')
        volet.locator(':scope > summary').click()
        expect(groupe).to_have_attribute('open', '')
        page.set_viewport_size({'width': 1366, 'height': 900})
        self.capture(page, 'NAV04-volet-ouvert')
        volet.locator(':scope > summary').click()
        page.goto(self.url(prise=True) + '#social-' + str(self.p.pk) + '-coordonnees')
        expect(volet).to_have_attribute('open', '')
        expect(groupe).to_have_attribute('open', '')
        expect(groupe.locator('h4')).to_be_in_viewport()
        volet.locator(':scope > summary').click()
        page.emulate_media(media='print')
        expect(groupe.locator('dd').filter(has_text='Bordeaux')).to_be_visible()
        expect(volet).not_to_have_attribute('open', '')

    def test_ouverture_memoire_ancres_et_dispositions(self):
        from playwright.sync_api import expect
        autre = m.Personne.objects.create(designation='Martin', prenom='Samira', cree_par=self.u)
        m.Appartenance.objects.create(menage=self.m, personne=autre,
            debut=timezone.localdate()-timedelta(days=30))
        self.a.beneficiaires.add(autre)
        page = self.navigateur()
        page.goto(self.url('menage'))
        tous = page.locator('[data-condition-repli]')
        expect(page.locator('[data-condition-volet]')).not_to_have_attribute('open', '')
        expect(page.locator('[data-condition-repli][open]')).to_have_count(0)
        page.locator('[data-condition-volet] > summary').click()
        self.assertGreater(tous.count(), 20)
        for largeur in [390, 1366, 640, 320]:
            page.set_viewport_size({'width': largeur, 'height': 900})
            page.get_by_role('button', name='Tout replier', exact=True).click()
            expect(page.locator('[data-condition-repli][open]')).to_have_count(0)
            if largeur == 390:
                page.locator('#social-' + str(self.p.pk) + '-identite').scroll_into_view_if_needed()
                self.capture(page, 'NAV04-menage-replie')
            groupe = page.locator('#social-' + str(self.p.pk) + '-coordonnees')
            resume = groupe.locator(':scope > summary')
            expect(resume).to_have_accessible_name('Coordonnées')
            expect(groupe.locator('.condition-apercu')).to_contain_text('Bordeaux')
            resume.focus()
            page.keyboard.press('Enter')
            expect(groupe).to_have_attribute('open', '')
            expect(groupe.locator('[data-condition-lecture]').first).to_be_visible()
            if largeur == 1366:
                self.capture(page, 'NAV04-rubrique-ouverte')
            page.keyboard.press('Space')
            expect(groupe).not_to_have_attribute('open', '')
            self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            page.get_by_role('button', name='Tout déplier', exact=True).click()
            expect(page.locator('[data-condition-repli]:not([open])')).to_have_count(0)
        page.get_by_role('button', name='Tout replier', exact=True).click()
        page.goto(self.url('menage', prise=True))
        expect(page.locator('#social-' + str(self.p.pk) + '-coordonnees')).not_to_have_attribute('open', '')
        # L'ancre vise le dépliant lui-même : elle doit aussi l'ouvrir.
        page.goto(self.url('menage', prise=True) + '#social-' + str(self.p.pk) + '-coordonnees')
        groupe = page.locator('#social-' + str(self.p.pk) + '-coordonnees')
        expect(groupe).to_have_attribute('open', '')
        expect(groupe.locator('h4')).to_be_in_viewport()
        page.get_by_role('button', name='Tout replier', exact=True).click()
        barre = page.get_by_role('navigation', name='Accès rapides dans cette page')
        barre.get_by_role('button', name='Sommaire', exact=True).click()
        menu = page.get_by_role('navigation', name='Dans cette page', exact=True)
        menu.locator('.condition-nav-details').first.locator('summary').click()
        menu.locator('a[href="#social-' + str(self.p.pk) + '-coordonnees"]').click()
        expect(groupe).to_have_attribute('open', '')
        expect(groupe.locator('h4')).to_be_in_viewport()
        self.assertTrue(page.evaluate("Object.keys(sessionStorage).filter(k=>k.startsWith('pas-a-pas-rubriques-v1')).every(k=>Object.values(JSON.parse(sessionStorage[k])).every(v=>typeof v === 'boolean'))"))
        # L'identité de dossier reste distincte entre personne et ménage.
        page.goto(self.url())
        expect(page.locator('[data-condition-repli][open]')).to_have_count(0)

    def test_saisie_erreurs_enregistrement_annulation_et_evolution(self):
        from playwright.sync_api import expect
        m.SituationPersonnelle.objects.create(personne=self.p, dimension='ressources',
            valeur='sans_ressources', debut=self.entree+timedelta(days=1), auteur=self.u)
        page = self.navigateur()
        page.goto(self.url(prise=True))
        page.locator('[data-condition-volet] > summary').click()
        page.get_by_role('button', name='Tout replier', exact=True).click()
        groupe = page.locator('#social-' + str(self.p.pk) + '-coordonnees')
        groupe.locator(':scope > summary').click()
        groupe.get_by_role('link', name='Modifier', exact=True).click()
        form = groupe.locator('[data-condition-form]')
        form.locator('[name=telephone]').fill('06 33 33 33 33')
        page.locator('[data-condition-volet] > summary').click()
        expect(page.locator('[data-condition-volet]')).to_have_attribute('open', '')
        expect(form).to_be_visible()
        page.get_by_role('button', name='Tout replier', exact=True).click()
        expect(groupe).to_have_attribute('open', '')
        expect(page.locator('[data-condition-repli][open]')).to_have_count(1)
        expect(page.locator('[data-condition-statut]')).to_contain_text('saisie laissée ouverte')
        groupe.locator(':scope > summary').click()
        expect(groupe).to_have_attribute('open', '')
        form.locator('[name=courriel]').fill('incorrect')
        form.evaluate('f=>f.noValidate=true')  # Exercer le refus serveur.
        form.get_by_role('button', name='Enregistrer', exact=True).click()
        expect(form.locator('.erreurs-formulaire')).to_be_visible()
        form.locator('.erreurs-formulaire a[href="#id_courriel"]').click()
        expect(form.locator('[name=courriel]')).to_be_focused()
        expect(form.locator('[name=courriel]')).to_be_in_viewport()
        form.locator('[name=courriel]').fill('')
        form.get_by_role('button', name='Enregistrer', exact=True).click()
        expect(form).to_have_count(0)
        expect(groupe).to_have_attribute('open', '')
        expect(page.locator('[data-condition-repli][open]')).to_have_count(1)
        groupe.get_by_role('link', name='Modifier', exact=True).click()
        form.locator('[name=telephone]').fill('06 99 99 99 99')
        page.get_by_role('button', name='Tout replier', exact=True).click()
        page.once('dialog', lambda dialogue: dialogue.accept())
        form.get_by_role('button', name='Annuler', exact=True).click()
        expect(form).to_have_count(0)
        expect(groupe).to_have_attribute('open', '')
        expect(groupe).to_contain_text('06 33 33 33 33')
        expect(page.locator('[data-condition-statut]')).to_have_text('')
        page.get_by_role('button', name='Tout replier', exact=True).click()
        page.locator('[data-condition-evolution]').check()
        panel = page.locator('[data-condition-evolution-panel]')
        expect(panel).to_be_visible()
        ligne = panel.locator('[data-condition-groupe]').filter(has=page.get_by_role('link', name='Modifier', exact=True)).first
        ligne.get_by_role('link', name='Modifier', exact=True).click()
        edition = ligne.locator('[data-condition-form]')
        edition.locator('[name=valeur]').select_option('ressources_declarees')
        edition.get_by_role('button', name='Enregistrer', exact=True).click()
        expect(edition).to_have_count(0)
        expect(page.locator('[data-condition-evolution]')).to_be_checked()
        page.locator('[data-condition-revenir]').check()
        expect(page.locator('[data-condition-repli][open]')).to_have_count(0)

    def test_repli_sans_javascript_et_impression(self):
        from playwright.sync_api import expect
        page = self.navigateur()
        contexte = page.context.browser.new_context(storage_state=page.context.storage_state(),
            java_script_enabled=False, viewport={'width': 1366, 'height': 900})
        self.addCleanup(contexte.close)
        page = contexte.new_page()
        page.goto(self.url())
        groupe = page.locator('#social-' + str(self.p.pk) + '-coordonnees')
        expect(groupe).to_have_attribute('open', '')
        groupe.locator(':scope > summary').click()
        expect(groupe).not_to_have_attribute('open', '')
        expect(groupe.locator('[data-condition-lecture]').first).to_be_hidden()
        page.locator('[data-condition-volet] > summary').click()
        page.emulate_media(media='print')
        expect(groupe.locator('[data-condition-lecture]').first).to_be_visible()
        expect(groupe.locator('dd').filter(has_text='Bordeaux')).to_be_visible()
        self.capture(page, 'NAV04-impression')
        pdf = page.pdf()
        self.assertTrue(pdf.startswith(b'%PDF'))
        if os.environ.get('RUBRIQUES_CAPTURES'):
            (Path(os.environ['RUBRIQUES_CAPTURES']) / 'NAV04-impression.pdf').write_bytes(pdf)
        expect(groupe).not_to_have_attribute('open', '')
        page.emulate_media(media='screen')
        page.locator('[data-condition-volet] > summary').click()
        groupe.locator(':scope > summary').focus()
        page.keyboard.press('Space')
        expect(groupe).to_have_attribute('open', '')
        groupe.get_by_role('link', name='Modifier', exact=True).click()
        expect(page.get_by_role('button', name='Enregistrer', exact=True)).to_be_visible()

    def test_stockage_indisponible_et_actualisation_sur_place(self):
        from playwright.sync_api import expect
        page = self.navigateur()
        contexte = page.context.browser.new_context(storage_state=page.context.storage_state(),
            viewport={'width': 390, 'height': 844})
        self.addCleanup(contexte.close)
        contexte.add_init_script("Object.defineProperty(window,'sessionStorage',{get(){throw new DOMException('refus simulé','SecurityError')}})")
        page = contexte.new_page()
        page.goto(self.url(prise=True))
        page.locator('[data-condition-volet] > summary').click()
        page.get_by_role('button', name='Tout replier', exact=True).click()
        groupe = page.locator('#social-' + str(self.p.pk) + '-coordonnees')
        groupe.locator(':scope > summary').click()
        groupe.get_by_role('link', name='Modifier', exact=True).click()
        form = groupe.locator('[data-condition-form]')
        form.locator('[name=telephone]').fill('06 22 22 22 22')
        form.get_by_role('button', name='Enregistrer', exact=True).click()
        expect(form).to_have_count(0)
        expect(groupe).to_have_attribute('open', '')
        expect(page.locator('[data-condition-repli][open]')).to_have_count(1)
        page.reload()
        expect(page.locator('[data-condition-repli][open]')).to_have_count(0)

    def test_memoire_par_utilisateur_et_actualisation_prestations(self):
        from playwright.sync_api import expect
        second = get_user_model().objects.create_superuser('autre-fictif',
            password='Recette-fictive-CHRS14!')
        page = self.navigateur()
        page.goto(self.url('menage', prise=True))
        page.locator('[data-condition-volet] > summary').click()
        page.get_by_role('button', name='Tout replier', exact=True).click()
        barre = page.get_by_role('navigation', name='Accès rapides dans cette page')
        barre.get_by_role('link', name='Prestations', exact=True).click()
        page.get_by_role('link', name='Nouveau séjour', exact=True).click()
        hebergement = page.locator('#hebergement')
        expect(hebergement.locator('form[data-prestation-dossier]')).to_be_visible()
        hebergement.get_by_role('button', name='← Revenir à la liste', exact=True).click()
        expect(page.get_by_text('Dossier actualisé.', exact=True)).to_be_visible()
        expect(page.locator('[data-condition-repli][open]')).to_have_count(0)
        page.locator('.menu-utilisateur').first.locator('summary').click()
        page.get_by_role('button', name='Se déconnecter', exact=True).click()
        page.locator('[name=username]').fill(second.username)
        page.locator('[name=password]').fill('Recette-fictive-CHRS14!')
        page.get_by_role('button', name='Se connecter', exact=True).click()
        page.goto(self.url('menage', prise=True))
        expect(page.locator('[data-condition-repli][open]')).to_have_count(0)
        page.set_viewport_size({'width': 1366, 'height': 900})
        page.add_style_tag(content='html { font-size: 200%; }')
        self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
