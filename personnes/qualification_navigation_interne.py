"""NAV2 : vrais déplacements locaux, dispositions et conservation des saisies."""
import os
from pathlib import Path
from unittest import skipIf
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from . import qualification_navigateur as q

@skipIf(q.sync_playwright is None, 'Playwright non installé.')
class NavigationInterneNavigateur(StaticLiveServerTestCase):
    setUp = q.ConditionSocialeNavigateur.setUp
    navigateur = q.ProfilsNavigateur.navigateur

    def url(self, nature='menage', prise=False):
        pk = self.m.pk if nature == 'menage' else self.p.pk
        return self.live_server_url + reverse('dossiers:prise' if prise else 'dossiers:detail',
            args=[nature, pk, self.a.pk] if prise else [nature, pk])

    def capture(self, page, nom):
        destination = os.environ.get('NAVIGATION_CAPTURES')
        if destination:
            chemin = Path(destination)
            chemin.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(chemin / (nom + '.png')))

    def test_dispositions_ancres_clavier_et_historique(self):
        from playwright.sync_api import expect
        from . import models as m
        from django.utils import timezone
        from datetime import timedelta
        autre = m.Personne.objects.create(designation='Nom-très-long-' + 'Martin' * 20,
            prenom='Samira', cree_par=self.u)
        m.Appartenance.objects.create(menage=self.m, personne=autre,
            debut=timezone.localdate()-timedelta(days=30))
        self.a.beneficiaires.add(autre)
        page = self.navigateur()
        requetes = []
        page.on('request', lambda r: requetes.append(r.url) if r.resource_type != 'image' else None)
        for nature, prise in [('menage', False), ('personne', False), ('menage', True), ('personne', True)]:
            page.goto(self.url(nature, prise))
            nom = 'Prestations' if prise else 'Prises en charge'
            for largeur in [320, 390, 1280, 1366, 1920, 640]:
                page.set_viewport_size({'width': largeur, 'height': 900})
                barre = page.get_by_role('navigation', name='Accès rapides dans cette page')
                menu = page.get_by_role('navigation', name='Dans cette page', exact=True)
                if largeur >= 1280:
                    expect(menu).to_be_visible()
                    expect(barre).to_be_hidden()
                    menu.get_by_role('link', name=nom, exact=True).click()
                else:
                    expect(barre).to_be_visible()
                    historique = page.evaluate('history.length')
                    avant = len(requetes)
                    barre.get_by_role('link', name=nom, exact=True).focus()
                    page.keyboard.press('Enter')
                    expect(barre.get_by_role('link', name=nom, exact=True)).to_have_attribute('aria-current', 'location')
                    self.assertEqual(page.evaluate('history.length'), historique)
                    self.assertEqual(len(requetes), avant)
                    cible = page.locator('#titre-prestations' if prise else '#prises h2')
                    self.assertGreaterEqual(cible.bounding_box()['y'], 0)
                    self.assertLess(cible.bounding_box()['y'], barre.bounding_box()['y'])
                    declencheur = barre.get_by_role('button', name='Sommaire', exact=True)
                    declencheur.focus()
                    page.keyboard.press('Enter')
                    expect(declencheur).to_have_attribute('aria-expanded', 'true')
                    expect(menu).to_be_visible()
                    page.keyboard.press('Tab')
                    expect(menu.get_by_role('button', name='Fermer', exact=True)).to_be_focused()
                    if nature == 'menage' and not prise and largeur == 390:
                        menu.locator('.condition-nav-details').first.locator('summary').click(position={'x': 5, 'y': 5})
                        self.capture(page, 'NAV02-sommaire-etroit')
                    page.keyboard.press('Escape')
                    expect(menu).to_be_hidden()
                    expect(declencheur).to_be_focused()
                    if nature == 'menage' and not prise and largeur == 390:
                        self.capture(page, 'NAV02-dossier-etroit')
                        avant = len(requetes)
                        page.mouse.move(200, 200)
                        page.mouse.wheel(0, page.locator('#condition-sociale').bounding_box()['y'] - 150)
                        expect(barre.get_by_role('link', name='Situation', exact=True)).to_have_attribute('aria-current', 'location')
                        self.assertEqual(len(requetes), avant)
                self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Débordement à ' + str(page.viewport_size))
                if nature == 'menage' and prise and largeur == 1366:
                    self.capture(page, 'NAV02-prise-portable')
            # Texte agrandi ; le seuil en rem laisse la place aux formulaires.
            page.set_viewport_size({'width': 1366, 'height': 900})
            page.add_style_tag(content='html { font-size: 200%; }')
            self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Débordement à ' + str(page.viewport_size))
            # Retirer uniquement la feuille de qualification avant la page suivante.
            page.reload()
            if page.locator('[data-condition-volet]').get_attribute('open') is None:
                page.locator('[data-condition-volet] > summary').click()
            page.locator('[data-condition-evolution]').check()
            expect(page.locator('[data-condition-evolution-panel]')).to_be_visible()
            menu = page.get_by_role('navigation', name='Dans cette page', exact=True)
            menu.get_by_role('link', name='Éléments datés', exact=True).click()
            expect(page.locator('[data-condition-evolution]')).to_be_checked()
            menu.get_by_role('link', name='Prestations' if prise else 'Prises en charge', exact=True).click()
            menu.get_by_role('link', name='Situation sociale et projet', exact=True).click()
            expect(page.locator('[data-condition-evolution]')).to_be_checked()
        # Un lien direct reste atteignable et Précédent retrouve la page d'origine.
        page.goto(self.url())
        page.goto(self.url(prise=True) + '#titre-prestations')
        expect(page.locator('#titre-prestations')).to_be_in_viewport()
        page.go_back()
        expect(page.get_by_role('heading', name='Dossier — ' + str(self.m), exact=True)).to_be_visible()
        page.goto(self.url(prise=True) + '#evolution-elements')
        expect(page.locator('[data-condition-evolution]')).to_be_checked()
        expect(page.locator('#evolution-elements')).to_be_in_viewport()

    def test_saisie_situation_evolution_et_actualisations(self):
        from playwright.sync_api import expect
        from . import models as m
        from datetime import timedelta
        m.SituationPersonnelle.objects.create(personne=self.p, dimension='ressources',
            valeur='sans_ressources', debut=self.entree+timedelta(days=1), auteur=self.u)
        page = self.navigateur()
        page.goto(self.url(prise=True))
        page.locator('[data-condition-volet] > summary').click()
        page.get_by_role('button', name='Tout déplier', exact=True).click()
        barre = page.get_by_role('navigation', name='Accès rapides dans cette page')
        groupe = page.locator('#social-' + str(self.p.pk) + '-coordonnees')
        groupe.get_by_role('link', name='Modifier', exact=True).click()
        form = groupe.locator('[data-condition-form]')
        form.locator('[name=telephone]').fill('06 44 44 44 44')
        page.set_viewport_size({'width': 1366, 'height': 900})
        self.assertGreater(form.locator('[name=telephone]').bounding_box()['width'], 200)
        self.capture(page, 'NAV02-formulaire-portable')
        page.set_viewport_size({'width': 390, 'height': 844})
        avant = page.evaluate('history.length')
        barre.get_by_role('link', name='Prestations', exact=True).click()
        barre.get_by_role('link', name='Situation', exact=True).click()
        expect(form.locator('[name=telephone]')).to_have_value('06 44 44 44 44')
        expect(form).to_be_visible()
        self.assertEqual(page.evaluate('history.length'), avant)
        self.capture(page, 'NAV02-situation-etroit')
        form.locator('[name=courriel]').fill('invalide')
        form.evaluate('element => element.noValidate = true')  # Refus serveur, comme la recette sociale existante.
        form.get_by_role('button', name='Enregistrer', exact=True).click()
        expect(form.locator('.errorlist').first).to_be_visible()
        focus = page.locator(':focus')
        self.assertLess(focus.bounding_box()['y'] + focus.bounding_box()['height'], barre.bounding_box()['y'])
        form.locator('[name=courriel]').fill('')
        form.get_by_role('button', name='Enregistrer', exact=True).click()
        expect(form).to_have_count(0)
        expect(groupe).to_contain_text('06 44 44 44 44')
        barre.get_by_role('button', name='Sommaire', exact=True).click()
        menu = page.get_by_role('navigation', name='Dans cette page', exact=True)
        menu.get_by_role('link', name='Situation sociale et projet', exact=True).click()
        expect(menu).to_be_hidden()
        page.locator('[data-condition-evolution]').check()
        expect(page.locator('[data-condition-evolution-panel]')).to_be_visible()
        barre.get_by_role('link', name='Prestations', exact=True).click()
        barre.get_by_role('link', name='Situation', exact=True).click()
        expect(page.locator('[data-condition-evolution]')).to_be_checked()
        barre.get_by_role('button', name='Sommaire', exact=True).click()
        menu.get_by_role('link', name='Éléments datés', exact=True).click()
        expect(page.locator('[data-condition-evolution]')).to_be_checked()
        # Une déclaration personnelle datée dans la période est modifiable dans Évolution.
        ligne = page.locator('[data-condition-evolution-panel] [data-condition-groupe]').filter(
            has=page.get_by_role('link', name='Modifier', exact=True)).first
        ligne.get_by_role('link', name='Modifier', exact=True).click()
        edition = ligne.locator('[data-condition-form]')
        champ = edition.locator('[name=valeur]')
        expect(champ).to_be_visible()
        champ.select_option('ressources_declarees')
        barre.get_by_role('link', name='Prestations', exact=True).click()
        barre.get_by_role('link', name='Situation', exact=True).click()
        expect(page.locator('[data-condition-evolution]')).to_be_checked()
        expect(champ).to_have_value('ressources_declarees')
        page.once('dialog', lambda dialogue: dialogue.accept())
        edition.get_by_role('button', name='Annuler', exact=True).click()
        expect(edition).to_have_count(0)
        expect(page.locator('[data-condition-evolution]')).to_be_checked()
        ligne.get_by_role('link', name='Modifier', exact=True).click()
        edition.locator('[name=valeur]').select_option('ressources_declarees')
        edition.get_by_role('button', name='Enregistrer', exact=True).click()
        expect(edition).to_have_count(0)
        expect(page.locator('[data-condition-evolution]')).to_be_checked()
        expect(barre.get_by_role('link', name='Situation', exact=True)).to_have_attribute('aria-current', 'location')

    def test_repli_sans_javascript(self):
        from playwright.sync_api import expect
        page = self.navigateur()
        contexte = page.context.browser.new_context(storage_state=page.context.storage_state(),
            java_script_enabled=False, viewport={'width': 390, 'height': 844})
        self.addCleanup(contexte.close)
        page = contexte.new_page()
        page.goto(self.url())
        barre = page.get_by_role('navigation', name='Accès rapides dans cette page')
        barre.get_by_role('link', name='Prises en charge', exact=True).click()
        expect(page.locator('#prises h2')).to_be_in_viewport()
        barre.get_by_role('link', name='Sommaire', exact=True).click()
        expect(page.get_by_role('navigation', name='Dans cette page', exact=True)).to_be_in_viewport()

    def test_commandes_tactiles_et_actualisation_des_prestations(self):
        from playwright.sync_api import expect
        page = self.navigateur()
        contexte = page.context.browser.new_context(storage_state=page.context.storage_state(),
            has_touch=True, is_mobile=True, viewport={'width': 390, 'height': 844})
        self.addCleanup(contexte.close)
        page = contexte.new_page()
        page.goto(self.url(prise=True))
        page.locator('[data-condition-volet] > summary').click()
        page.get_by_role('button', name='Tout déplier', exact=True).click()
        barre = page.get_by_role('navigation', name='Accès rapides dans cette page')
        barre.get_by_role('button', name='Sommaire', exact=True).tap()
        menu = page.get_by_role('navigation', name='Dans cette page', exact=True)
        expect(menu).to_be_visible()
        menu.locator('.condition-nav-details').first.locator('summary').tap()
        expect(menu.locator('.condition-nav-details').first).to_have_attribute('open', '')
        menu.get_by_role('link', name='Prestations', exact=True).tap()
        expect(menu).to_be_hidden()
        page.get_by_role('link', name='Nouveau séjour', exact=True).tap()
        hebergement = page.locator('#hebergement')
        expect(hebergement.locator('form[data-prestation-dossier]')).to_be_visible()
        # Le retour aux listes remplace réellement le contenu du dossier.
        hebergement.get_by_role('button', name='← Revenir à la liste', exact=True).tap()
        expect(page.get_by_text('Dossier actualisé.', exact=True)).to_be_visible()
        barre.get_by_role('button', name='Sommaire', exact=True).tap()
        expect(menu).to_be_visible()
        expect(menu.locator('.condition-nav-details').first).to_have_attribute('open', '')
        menu.get_by_role('button', name='Fermer', exact=True).tap()
        expect(menu).to_be_hidden()
        barre.get_by_role('link', name='Situation', exact=True).tap()
        expect(barre.get_by_role('link', name='Situation', exact=True)).to_have_attribute('aria-current', 'location')
