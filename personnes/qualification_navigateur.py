"""Recette Chromium des permissions métier (lancée explicitement en CI)."""
from django.contrib.auth.models import Permission
from django.test import LiveServerTestCase
from django.urls import reverse
from playwright.sync_api import sync_playwright

from .tests_navigation import NavigationTests


class ProfilsNavigateur(LiveServerTestCase):
    """Profils fictifs : le navigateur ne doit proposer aucun accès interdit."""

    def setUp(self):
        NavigationTests.setUp(self)
        self.u.set_password('Recette-fictive-CHRS14!')
        self.u.save(update_fields=['password'])

    def profil(self, *droits):
        self.u.user_permissions.clear()
        self.u.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='personnes', codename__in=droits))

    def navigateur(self):
        playwright = sync_playwright().start()
        self.addCleanup(playwright.stop)
        browser = playwright.chromium.launch()
        self.addCleanup(browser.close)
        page = browser.new_page(viewport={'width': 390, 'height': 844})
        page.goto(self.live_server_url + '/connexion/')
        page.locator('input[name="username"]').fill(self.u.username)
        page.locator('input[name="password"]').fill('Recette-fictive-CHRS14!')
        page.get_by_role('button', name='Se connecter').click()
        return page

    def ouvrir(self, page, route):
        return page.goto(self.live_server_url + reverse(route))

    def test_veilleur_saisie_et_refus_social(self):
        self.profil('view_personne', 'view_menage', 'view_accompagnement',
                    'view_transmission', 'add_transmission',
                    'view_actionrelais', 'add_actionrelais')
        page = self.navigateur()
        self.ouvrir(page, 'suivi:jour')
        page.get_by_role('heading', name='Travail du jour').wait_for()
        page.get_by_role('link', name='Écrire une transmission').click()
        page.get_by_role('heading', name='Cahier de liaison').wait_for()
        page.get_by_role('link', name='Retour au travail du jour').wait_for()
        self.assertEqual(page.goto(self.live_server_url + reverse(
            'suivi:trajectoire', args=[self.a.pk])).status, 403)
        self.assertEqual(self.ouvrir(page, 'statistiques').status, 403)

    def test_journee_actions_sans_saisie_transmission(self):
        self.profil('view_personne', 'view_menage', 'view_accompagnement',
                    'view_transmission', 'view_actionrelais', 'change_actionrelais')
        page = self.navigateur()
        self.ouvrir(page, 'suivi:jour')
        page.get_by_role('heading', name='Relève actuelle — actions explicitement en attente').wait_for()
        page.get_by_role('link', name='Consulter le cahier de liaison').wait_for()
        self.assertEqual(page.get_by_role('link', name='Écrire une transmission').count(), 0)
        page.get_by_role('link', name='Consulter et clôturer les actions de relève').click()
        self.assertEqual(page.get_by_role('heading', name='Actions de relève').count(), 1)
        self.assertEqual(page.goto(self.live_server_url + reverse(
            'suivi:trajectoire', args=[self.a.pk])).status, 403)

    def test_referent_social_sans_acces_automatique_releve(self):
        self.profil('view_personne', 'view_menage', 'view_accompagnement',
                    'view_situationsociale')
        page = self.navigateur()
        self.ouvrir(page, 'suivi:jour')
        self.assertEqual(page.get_by_role('link', name='Relève').count(), 0)
        self.assertEqual(page.get_by_role('link', name='Écrire une transmission').count(), 0)
        self.assertEqual(self.ouvrir(page, 'suivi:cahier').status, 403)
        self.assertEqual(self.ouvrir(page, 'suivi:actions_relais').status, 403)
        self.assertEqual(page.goto(self.live_server_url + reverse(
            'suivi:trajectoire', args=[self.a.pk])).status, 200)
