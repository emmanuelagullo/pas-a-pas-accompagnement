"""Recette Chromium des permissions métier (lancée explicitement en CI)."""
from django.contrib.auth.models import Permission
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from playwright.sync_api import sync_playwright

from .tests_navigation import NavigationTests


class ProfilsNavigateur(StaticLiveServerTestCase):
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

    def test_releve_historique_conserve_date_et_droits(self):
        """Recette veilleur : consultation passée, relève, retour à la même date."""
        self.profil('view_personne', 'view_menage', 'view_accompagnement',
                    'view_transmission', 'add_transmission',
                    'view_actionrelais', 'add_actionrelais', 'change_actionrelais')
        page = self.navigateur()
        cible = self.live_server_url + reverse('suivi:jour') + '?date=2026-01-03'
        page.goto(cible)
        page.get_by_role('heading', name='Situation à la date choisie — 03/01/2026').wait_for()
        page.get_by_role('link', name='Écrire une transmission').click()
        page.get_by_role('heading', name='Cahier de liaison').wait_for()
        self.assertEqual(page.locator('input[name="date_service"]').input_value(), '2026-01-03')
        page.get_by_role('link', name='Retour au travail du jour').click()
        self.assertEqual(page.url, cible)
        page.get_by_role('link', name='Créer une action de relève').click()
        page.get_by_role('heading', name='Actions de relève').wait_for()
        self.assertEqual(page.locator('input[name="date_service"]').input_value(), '2026-01-03')
        page.get_by_role('link', name='Retour au travail du jour').click()
        self.assertEqual(page.url, cible)
        self.assertEqual(page.goto(self.live_server_url + reverse(
            'suivi:trajectoire', args=[self.a.pk])).status, 403)

    def test_parcours_accueil_et_suivi_reste_navigable(self):
        """Recette d'un accompagnement fictif, sans écriture ni mutation de données."""
        self.profil('view_personne', 'view_menage', 'view_accompagnement',
                    'view_accordhebergement', 'view_sejour',
                    'view_accordrepas', 'view_repasdistribue')
        page = self.navigateur()
        page.goto(self.live_server_url + reverse('suivi:liste'))
        self.assertEqual(page.locator('main').count(), 1)
        page.goto(self.live_server_url + reverse('suivi:detail', args=[self.m.pk]))
        self.assertEqual(page.locator('main').count(), 1)
        page.goto(self.live_server_url + reverse('suivi:accompagnement', args=[self.a.pk]))
        self.assertEqual(page.locator('main').count(), 1)
        page.goto(self.live_server_url + reverse('suivi:jour') + '?date=2026-01-03')
        page.get_by_role('heading', name='Travail du jour').wait_for()
        self.assertEqual(page.locator('main').count(), 1)


class DossierPersonneMenageNavigateur(StaticLiveServerTestCase):
    """Parcours réel de rattachement, retours et contrôle des permissions."""

    setUp = ProfilsNavigateur.setUp
    profil = ProfilsNavigateur.profil
    navigateur = ProfilsNavigateur.navigateur

    def test_fiche_choix_rattachement_et_accompagnement(self):
        from .models import Personne, Appartenance
        autre = Personne.objects.create(
            designation='Autre personne fictive', cree_par=self.u)
        self.profil('view_personne', 'view_menage', 'view_accompagnement',
                    'add_appartenance')
        page = self.navigateur()
        fiche = self.live_server_url + reverse('personnes:detail', args=[autre.pk])
        page.goto(fiche)
        page.get_by_role('heading', name=autre.designation).wait_for()
        page.get_by_role('link', name='Rattacher cette personne à un ménage existant').click()
        page.get_by_text('Rattacher', exact=False).first.wait_for()
        page.get_by_role('link', name='Retour à sa fiche').click()
        self.assertEqual(page.url, fiche)
        page.get_by_role('link', name='Rattacher cette personne à un ménage existant').click()
        lien = page.get_by_role('link', name='Rattacher à ce ménage')
        self.assertIn('personne=' + str(autre.pk), lien.get_attribute('href'))
        lien.click()
        self.assertEqual(page.locator('select[name="personne"]').input_value(), str(autre.pk))
        page.get_by_role('link', name='Retour au ménage').click()
        self.assertEqual(page.url, self.live_server_url + reverse('suivi:detail', args=[self.m.pk]))
        page.goto(self.live_server_url + reverse('suivi:liste') + '?personne=' + str(autre.pk))
        page.get_by_role('link', name='Rattacher à ce ménage').click()
        page.locator('input[name="debut"]').fill('2026-01-02')
        page.get_by_role('button', name='Enregistrer').click()
        self.assertEqual(page.url, self.live_server_url + reverse('suivi:detail', args=[self.m.pk]))
        self.assertTrue(Appartenance.objects.filter(menage=self.m, personne=autre).exists())
        page.get_by_role('link', name=autre.designation).click()
        self.assertEqual(page.url, fiche)
        page.get_by_role('link', name=self.m.libelle).first.click()
        page.get_by_role('link', name='Ouvrir la fiche d’accompagnement').click()
        page.get_by_role('heading', name='Accompagnement — ' + self.m.libelle).wait_for()
        page.get_by_role('link', name='Ménage ' + self.m.libelle).click()
        self.assertEqual(page.url, self.live_server_url + reverse('suivi:detail', args=[self.m.pk]))
        # Sans le droit d'ajouter une appartenance, ni lien ni accès direct.
        self.profil('view_personne', 'view_menage', 'view_accompagnement')
        page.goto(fiche)
        self.assertEqual(page.get_by_role('link', name='Rattacher cette personne à un ménage existant').count(), 0)
        self.assertEqual(page.goto(self.live_server_url + reverse('suivi:ajouter', args=[self.m.pk])).status, 403)
        # Sans le droit de voir les accompagnements, pas de lien ni d'accès direct.
        self.profil('view_personne', 'view_menage')
        page.goto(fiche)
        self.assertEqual(page.get_by_role('heading', name='Accompagnements').count(), 0)
        self.assertEqual(page.goto(self.live_server_url + reverse('suivi:accompagnement', args=[self.a.pk])).status, 403)


class CycleHebergementNavigateur(StaticLiveServerTestCase):
    """Recette Chromium du séjour fictif : actions réelles et historique conservé."""

    def setUp(self):
        from .tests_hebergement import Donnees
        Donnees.preparer(self)
        self.u.set_password('Recette-fictive-hebergement!')
        self.u.save(update_fields=['password'])

    def test_affectation_absence_sortie_et_actions_closes(self):
        from datetime import date
        from .models import Sejour, Affectation, Absence, OperationHebergement
        playwright = sync_playwright().start()
        self.addCleanup(playwright.stop)
        browser = playwright.chromium.launch()
        self.addCleanup(browser.close)
        page = browser.new_page()
        page.goto(self.live_server_url + '/connexion/')
        page.locator('input[name="username"]').fill(self.u.username)
        page.locator('input[name="password"]').fill('Recette-fictive-hebergement!')
        page.get_by_role('button', name='Se connecter').click()
        url = self.live_server_url + reverse('suivi:accord_hebergement', args=[self.accord.pk])
        page.goto(url)
        page.get_by_role('link', name='Enregistrer une admission').wait_for()
        # L'admission du jeu de test existe : la fiche doit exposer le séjour.
        page.get_by_role('heading', name='Séjour du', exact=False).wait_for()
        page.get_by_role('link', name='Ajouter une affectation').click()
        page.locator('input[name="debut"]').fill('2026-01-03')
        page.locator('select[name="lieu"]').select_option(str(self.lieu.pk))
        page.get_by_role('button', name='Enregistrer').click()
        page.get_by_role('link', name='Clôturer l’affectation').click()
        page.locator('input[name="fin"]').fill('2026-01-10')
        page.get_by_role('button', name='Enregistrer').click()
        page.get_by_role('link', name='Ajouter une affectation').click()
        page.locator('input[name="debut"]').fill('2026-01-10')
        page.locator('select[name="lieu"]').select_option(str(self.lieu.pk))
        page.get_by_role('button', name='Enregistrer').click()
        page.get_by_role('link', name='Enregistrer une absence').click()
        page.locator('input[name="debut"]').fill('2026-01-12')
        page.get_by_role('button', name='Enregistrer').click()
        page.get_by_role('link', name='Enregistrer la sortie').click()
        page.locator('input[name="fin"]').fill('2026-01-20')
        page.get_by_role('button', name='Enregistrer').click()
        page.get_by_role('heading', name='Séjour du', exact=False).wait_for()
        self.assertEqual(page.get_by_role('link', name='Ajouter une affectation').count(), 0)
        self.assertEqual(page.get_by_role('link', name='Enregistrer une absence').count(), 0)
        self.assertEqual(page.get_by_role('link', name='Enregistrer la sortie').count(), 0)
        self.s.refresh_from_db()
        self.assertEqual(self.s.fin, date(2026, 1, 20))
        self.assertEqual(list(Affectation.objects.filter(sejour=self.s).order_by('debut')
                              .values_list('debut', 'fin')),
                         [(date(2026, 1, 3), date(2026, 1, 10)),
                          (date(2026, 1, 10), date(2026, 1, 20))])
        self.assertEqual(Absence.objects.get(sejour=self.s).fin, date(2026, 1, 20))
        self.assertTrue(OperationHebergement.objects.filter(sejour=self.s,
                                                            action='Sortie effective').exists())
