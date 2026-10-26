"""Recette Chromium des permissions métier (lancée explicitement en CI)."""
from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth.models import Permission
from django.db import connections
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from unittest import skipIf

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError as erreur:
    if erreur.name != 'playwright':
        raise
    sync_playwright = None

from .tests_navigation import NavigationTests


def verifier_hors_boucle_playwright(verification):
    """Vérifier la base hors de la boucle événementielle Playwright."""
    def executer():
        try:
            return verification()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(executer).result()


@skipIf(sync_playwright is None, 'Module Python Playwright non installé : qualification navigateur ignorée.')
class ProfilsNavigateur(StaticLiveServerTestCase):
    """Profils fictifs : le navigateur ne doit proposer aucun accès interdit."""

    def setUp(self):
        NavigationTests.setUp(self)
        self.u.set_password('Recette-fictive-CHRS14!')
        self.u.save(update_fields=['password'])

    def profil(self, *droits):
        def appliquer():
            self.u.user_permissions.clear()
            self.u.user_permissions.add(*Permission.objects.filter(
                content_type__app_label='personnes', codename__in=droits))

        verifier_hors_boucle_playwright(appliquer)

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


@skipIf(sync_playwright is None, 'Module Python Playwright non installé : qualification navigateur ignorée.')
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
        self.assertTrue(verifier_hors_boucle_playwright(
            lambda: Appartenance.objects.filter(menage_id=self.m.pk, personne_id=autre.pk).exists()))
        page.get_by_role('link', name=autre.designation).click()
        self.assertEqual(page.url, fiche)
        page.get_by_role('link', name=self.m.libelle).first.click()
        page.get_by_role('link', name='Ouvrir la fiche d’accompagnement').click()
        page.get_by_role('heading', name='Dossier — ' + self.m.libelle).wait_for()
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


@skipIf(sync_playwright is None, 'Module Python Playwright non installé : qualification navigateur ignorée.')
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
        def etat_final():
            sejour = Sejour.objects.get(pk=self.s.pk)
            affectations = list(Affectation.objects.filter(sejour=sejour).order_by('debut')
                                .values_list('debut', 'fin'))
            absence_fin = Absence.objects.get(sejour=sejour).fin
            sortie = OperationHebergement.objects.filter(
                sejour=sejour, action='Sortie effective').exists()
            return sejour.fin, affectations, absence_fin, sortie

        fin, affectations, absence_fin, sortie = verifier_hors_boucle_playwright(etat_final)
        self.assertEqual(fin, date(2026, 1, 20))
        self.assertEqual(affectations,
                         [(date(2026, 1, 3), date(2026, 1, 10)),
                          (date(2026, 1, 10), date(2026, 1, 20))])
        self.assertEqual(absence_fin, date(2026, 1, 20))
        self.assertTrue(sortie)


@skipIf(sync_playwright is None, 'Module Python Playwright non installé : qualification navigateur ignorée.')
class NouveauxParcoursNavigateur(StaticLiveServerTestCase):
    """Recette des jalons CHRS25–26 sans ORM dans la boucle Playwright."""

    profil = ProfilsNavigateur.profil
    navigateur = ProfilsNavigateur.navigateur

    def setUp(self):
        from io import StringIO
        from django.core.management import call_command
        from .tests_admission_guidee import AdmissionGuideeTests
        AdmissionGuideeTests.setUp(self)
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        self.u = type(self.u).objects.get(pk=self.u.pk)
        self.u.set_password('Recette-fictive-CHRS14!')
        self.u.save(update_fields=['password'])

    def test_responsable_admission_familiale_et_actions_collectives(self):
        from datetime import date
        from .models import AccordHebergement, RepasDistribue
        page = self.navigateur()
        page.goto(self.live_server_url + reverse('suivi:accompagnement', args=[self.a.pk]))
        page.get_by_role('link', name='Nouveau séjour', exact=True).click()
        page.locator('input[name="debut"]').fill('2026-02-01')
        page.locator('input[name="fin"]').fill('2026-03-01')
        page.locator('input[name="admission"]').fill('2026-02-03')
        page.locator('select[name="lieu"]').select_option(str(self.lieu.pk))
        page.get_by_role('button', name='Enregistrer le séjour').click()
        page.get_by_role('heading', name='Dossier — ' + self.m.libelle, exact=True).wait_for()
        self.assertEqual(page.locator('input[name="sejour"]').count(), 3)
        def nouvel_identifiant():
            return str(AccordHebergement.objects.exclude(pk=self.accord.pk).get().sejours.first().pk)
        identifiant = verifier_hors_boucle_playwright(nouvel_identifiant)
        page.locator('input[type="radio"][name="sejour"][value="' + identifiant + '"]').check()
        page.get_by_role('button', name='Afficher les actions du séjour choisi', exact=True).click()
        page.get_by_role('link', name='Ouvrir le séjour et son accord', exact=True).click()
        page.get_by_role('heading', name='Hébergement accordé et séjours effectifs').wait_for()
        self.assertEqual(page.get_by_role('heading', name='Séjour du', exact=False).count(), 2)
        page.get_by_role('link', name='Agir sur plusieurs séjours', exact=False).click()
        for case in page.locator('input[name="sejours"]').all():
            case.check()
        page.locator('select[name="action"]').select_option('absence')
        page.locator('input[name="date"]').fill('2026-02-05')
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_role('heading', name='Dossier — ' + self.m.libelle, exact=True).wait_for()
        def verifier():
            accord = AccordHebergement.objects.exclude(pk=self.accord.pk).get()
            return (accord.sejours.count(), sum(s.absences.filter(debut=date(2026,2,5)).count() for s in accord.sejours.all()),
                    RepasDistribue.objects.count())
        self.assertEqual(verifier_hors_boucle_playwright(verifier), (2, 2, 0))

    def test_veilleur_date_conservee_et_refus_social(self):
        self.profil('view_personne', 'view_menage', 'view_accompagnement',
            'view_accordhebergement', 'view_sejour', 'add_absence', 'view_absence', 'change_absence')
        page = self.navigateur()
        cible = self.live_server_url + reverse('suivi:jour') + '?date=2026-01-10'
        page.goto(cible)
        page.get_by_role('link', name='Signaler une absence', exact=True).click()
        self.assertEqual(page.locator('input[name="debut"]').input_value(), '2026-01-10')
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_role('heading', name='Travail du jour', exact=True).wait_for()
        self.assertEqual(page.url, cible)
        page.goto(self.live_server_url + reverse('suivi:accord_hebergement', args=[self.accord.pk]))
        page.get_by_role('link', name='Enregistrer le retour d’absence', exact=True).click()
        page.locator('input[name="fin"]').fill('2026-01-12')
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_role('heading', name='Hébergement accordé et séjours effectifs').wait_for()
        self.assertEqual(page.get_by_role('link', name='Enregistrer le retour d’absence', exact=True).count(), 0)
        self.assertEqual(page.goto(self.live_server_url + reverse('suivi:social', args=[self.a.pk])).status, 403)
        self.assertEqual(page.goto(self.live_server_url + reverse('suivi:informations', args=[self.a.pk])).status, 403)

    def test_travailleur_social_insertion_et_resume_imprimable(self):
        from datetime import date
        from . import social
        from .models import SituationSociale, NotePartagee
        for jour in [5, 20]:
            social.renseigner(self.u, self.a, self.p, 'emploi', 'emploi', date(2026,1,jour), 'Source fictive')
        NotePartagee.objects.create(accompagnement=self.a, contenu='Note réservée hors résumé', auteur=self.u)
        page = self.navigateur()
        cible = self.live_server_url + reverse('suivi:accompagnement', args=[self.a.pk])
        page.goto(cible)
        page.get_by_role('link', name='Compléter ou mettre à jour', exact=True).click()
        page.locator('input[name="referent"]').fill('Référente extérieure fictive')
        page.locator('textarea[name="objectifs_courts"]').fill('Projet fictif à court terme')
        page.locator('[name="motif"]').fill('Projet préparé')
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_role('link', name='Situation et parcours sociaux', exact=True).click()
        page.get_by_role('link', name='Renseigner Emploi / formation', exact=True).click()
        page.locator('select[name="beneficiaire"]').select_option(str(self.p.pk))
        page.locator('select[name="valeur"]').select_option('formation')
        page.locator('input[name="debut"]').fill('2026-01-10')
        page.locator('[name="source"]').fill('Source fictive précisée')
        page.locator('[name="motif"]').fill('Situation oubliée')
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_role('heading', name='Dossier — ' + self.m.libelle, exact=True).wait_for()
        page.get_by_role('link', name='Situation et parcours sociaux', exact=True).click()
        page.get_by_role('heading', name='Historique par date d’effet', exact=True).wait_for()
        def verifier():
            return list(SituationSociale.objects.filter(accompagnement=self.a, beneficiaire=self.p)
                .order_by('debut').values_list('debut', 'fin'))
        self.assertEqual(verifier_hors_boucle_playwright(verifier), [
            (date(2026,1,5), date(2026,1,10)), (date(2026,1,10), date(2026,1,20)), (date(2026,1,20), None)])
        page.goto(cible)
        page.get_by_role('link', name='Ouvrir le résumé imprimable', exact=True).click()
        page.get_by_role('heading', name='Résumé d’accompagnement', exact=False).wait_for()
        self.assertIn('Référente extérieure fictive', page.locator('body').inner_text())
        self.assertNotIn('Note réservée hors résumé', page.locator('body').inner_text())
        self.assertEqual(page.locator('main').count(), 1)
        page.emulate_media(media='print')
        self.assertFalse(page.locator('nav').is_visible())
        self.assertTrue(page.get_by_role('heading', name='Résumé d’accompagnement', exact=False).is_visible())

    def test_repas_plusieurs_services_sans_distribution(self):
        from .models import AccordRepas, RepasDistribue
        page = self.navigateur()
        page.goto(self.live_server_url + reverse('suivi:accompagnement', args=[self.a.pk]))
        page.get_by_role('link', name='Accorder plusieurs services en une saisie', exact=True).click()
        page.locator('input[name="services"][value="dejeuner"]').check()
        page.locator('input[name="services"][value="diner"]').check()
        page.locator('input[name="debut"]').fill('2026-01-01')
        page.locator('input[name="fin"]').fill('2026-02-01')
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_role('heading', name='Dossier — ' + self.m.libelle, exact=True).wait_for()
        def verifier():
            return (sorted(AccordRepas.objects.values_list('service', flat=True)), RepasDistribue.objects.count())
        self.assertEqual(verifier_hors_boucle_playwright(verifier), (['dejeuner', 'diner'], 0))

    def test_rapports_mouvements_et_naissances_incompletes(self):
        page = self.navigateur()
        page.goto(self.live_server_url + reverse('statistiques'))
        page.locator('select[name="rapport"]').select_option('mouvements')
        page.locator('input[type="date"][name="debut"]').fill('2026-01-01')
        page.locator('input[type="date"][name="fin"]').fill('2026-02-01')
        page.get_by_role('button', name='Calculer', exact=True).click()
        page.get_by_role('heading', name='Mouvements et durées', exact=True).wait_for()
        self.assertIn('Non calculable', page.locator('main').inner_text())
        page.locator('select[name="rapport"]').select_option('ages')
        page.get_by_role('button', name='Calculer', exact=True).click()
        page.get_by_role('heading', name='Âges calculables au 31/01/2026', exact=True).wait_for()
        self.assertIn('Aucun âge calculable', page.locator('main').inner_text())
        self.assertIn('Naissance non renseignée', page.locator('main').inner_text())


    def test_dossier_selection_sejour_termine_et_retour_correction(self):
        from datetime import date
        from . import hebergement as h, repas
        h.sortir(self.u, self.s, date(2026, 1, 10))
        h.admettre(self.u, self.accord, [self.p], date(2026, 1, 12))
        accord_repas = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), date(2026, 2, 1), 'dejeuner')
        page = self.navigateur()
        page.goto(self.live_server_url + reverse('suivi:accompagnement', args=[self.a.pk]))
        page.locator('input[type="radio"][name="sejour"][value="' + str(self.s.pk) + '"]').check()
        page.get_by_role('button', name='Afficher les actions du séjour choisi', exact=True).click()
        self.assertTrue(page.locator('input[type="radio"][name="sejour"][value="' + str(self.s.pk) + '"]').is_checked())
        self.assertTrue(page.locator('input[type="radio"][name="repas"][value="' + str(accord_repas.pk) + '"]').is_checked())
        self.assertEqual(page.get_by_role('link', name='Enregistrer la sortie', exact=True).count(), 0)
        self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))
        page.get_by_role('link', name='Corriger les dates du séjour', exact=True).click()
        page.get_by_role('link', name='Annuler et revenir', exact=True).click()
        self.assertTrue(page.locator('input[type="radio"][name="sejour"][value="' + str(self.s.pk) + '"]').is_checked())
        self.assertTrue(page.locator('input[type="radio"][name="repas"][value="' + str(accord_repas.pk) + '"]').is_checked())

    def test_bd3_prolongation_annulation_et_selection_conservee(self):
        from datetime import date
        from io import StringIO
        from django.core.management import call_command
        from . import repas
        from .models import EvolutionAccord
        call_command('autoriser_bd3', self.u.username, stdout=StringIO())
        self.u = type(self.u).objects.get(pk=self.u.pk)
        accord = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), date(2026, 2, 1), 'dejeuner')
        page = self.navigateur()
        page.goto(self.live_server_url + reverse('suivi:accompagnement', args=[self.a.pk]))
        page.get_by_role('link', name='Prolonger l’accord de repas', exact=True).click()
        page.locator('input[name="fin"]').fill('2026-03-01')
        page.locator('textarea[name="motif"]').fill('Décision fictive de prolongation')
        page.locator('input[name="confirmer"]').check()
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_role('heading', name='Dossier — ' + self.m.libelle, exact=True).wait_for()
        self.assertTrue(page.locator('input[type="radio"][name="repas"][value="' + str(accord.pk) + '"]').is_checked())
        page.get_by_role('link', name='Ouvrir l’accord et les distributions', exact=True).click()
        page.get_by_role('heading', name='Décisions sur l’accord', exact=True).wait_for()
        page.get_by_text('Décision fictive de prolongation', exact=False).wait_for()
        page.get_by_role('link', name='Annuler l’accord saisi par erreur', exact=True).click()
        page.locator('textarea[name="motif"]').fill('Accord fictif créé par erreur')
        page.locator('input[name="confirmer"]').check()
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_role('heading', name='Dossier — ' + self.m.libelle, exact=True).wait_for()
        self.assertTrue(page.locator('input[type="radio"][name="repas"][value="' + str(accord.pk) + '"]').is_checked())
        self.assertEqual(page.get_by_role('link', name='Enregistrer une distribution', exact=True).count(), 0)
        self.assertEqual(verifier_hors_boucle_playwright(lambda: EvolutionAccord.objects.count()), 2)


@skipIf(sync_playwright is None, 'Module Python Playwright non installé : qualification navigateur ignorée.')
class EntreeBDNavigateur(StaticLiveServerTestCase):
    """Entrée réelle BD4, recherche dynamique et sans JavaScript."""
    navigateur = ProfilsNavigateur.navigateur

    def setUp(self):
        from io import StringIO
        from django.core.management import call_command
        from .tests_hebergement import Donnees
        Donnees.preparer(self)
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        self.u.set_password('Recette-fictive-CHRS14!')
        self.u.save(update_fields=['password'])

    def test_recherche_bascule_et_sortie_retour(self):
        page = self.navigateur()
        page.get_by_role('heading', name='Quel dossier souhaitez-vous ouvrir ?').wait_for()
        page.get_by_label('Nom, prénom ou libellé du dossier', exact=True).fill(self.p.designation)
        page.get_by_text('Résultats actualisés.', exact=True).wait_for()
        page.locator('#resultats-dossiers ul.resultats-dossiers a[href*="/dossiers/menage/"]').click()
        page.get_by_role('heading', name='Dossier — ' + self.m.libelle, exact=True).wait_for()
        page.locator('.condition-personne').first.get_by_role('link', name='Dossier individuel', exact=True).click()
        page.get_by_role('heading', name='Dossier — ' + str(self.p), exact=True).wait_for()
        page.get_by_role('button', name='Ouvrir', exact=True).click()
        page.get_by_role('link', name='Enregistrer la sortie', exact=True).click()
        page.locator('input[name="fin"]').fill('2026-01-20')
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_role('heading', name='Prise en charge du 01/01/2026', exact=True).wait_for()
        page.get_by_role('heading', name='Situation sociale et projet', exact=True).wait_for()
        self.assertTrue(page.locator('#projet').is_visible())
        self.assertTrue(page.get_by_role('link', name='Modifier les informations et le projet', exact=True).is_visible())
        page.get_by_text("Dossier actualisé.", exact=True).wait_for()
        self.assertEqual(page.locator('#hebergement a[aria-current="true"]').count(), 1)
        self.assertEqual(page.locator('[data-dossier-boite="repas"]').count(), 1)
        page.get_by_role('link', name='← Dossier ' + str(self.p), exact=True).click()
        page.get_by_role('link', name='← Revenir au ménage ' + self.m.libelle, exact=True).click()
        page.get_by_role('link', name='← Rechercher un dossier', exact=True).click()
        self.assertEqual(page.locator('#recherche-nom').input_value(), self.p.designation)
        page.get_by_label('Personnes', exact=True).check()
        page.get_by_text('Résultats actualisés.', exact=True).wait_for()
        page.locator('#resultats-dossiers ul.resultats-dossiers a[href*="/dossiers/personne/"]').click()
        page.get_by_role('heading', name='Dossier — ' + str(self.p), exact=True).wait_for()
        page.set_viewport_size({'width': 360, 'height': 800})
        self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))

    def test_formulaire_dans_boite_erreur_et_annulation(self):
        page = self.navigateur()
        page.goto(self.live_server_url + reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk]))
        page.get_by_role('link', name='Nouveau séjour', exact=True).click()
        boite = page.locator('#hebergement')
        boite.locator('form[data-prestation-dossier]').wait_for()
        self.assertTrue(page.get_by_role('heading', name='Prise en charge du 01/01/2026', exact=True).is_visible())
        self.assertTrue(page.locator('#repas').is_visible())
        boite.locator('input[name="attendu"]').evaluate("e => e.value = 'perime'")
        boite.locator('input[name="debut"]').fill('2026-04-01')
        boite.locator('input[name="admission"]').fill('2026-04-01')
        boite.get_by_role('button', name='Enregistrer le séjour', exact=True).click()
        boite.get_by_text('Le formulaire a expiré. Rechargez l’accompagnement.', exact=True).wait_for()
        self.assertEqual(boite.locator('input[name="debut"]').input_value(), '2026-04-01')
        page.once('dialog', lambda dialog: dialog.accept())
        boite.get_by_role('button', name='← Revenir à la liste', exact=True).click()
        page.get_by_text('Dossier actualisé.', exact=True).wait_for()
        self.assertEqual(page.locator('#hebergement a[aria-current="true"]').count(), 1)

    def test_recherche_sans_javascript(self):
        playwright = sync_playwright().start()
        self.addCleanup(playwright.stop)
        browser = playwright.chromium.launch()
        self.addCleanup(browser.close)
        page = browser.new_page(java_script_enabled=False)
        page.goto(self.live_server_url + '/connexion/')
        page.locator('input[name="username"]').fill(self.u.username)
        page.locator('input[name="password"]').fill('Recette-fictive-CHRS14!')
        page.get_by_role('button', name='Se connecter').click()
        page.get_by_label('Nom, prénom ou libellé du dossier', exact=True).fill(self.p.designation)
        page.get_by_role('button', name='Rechercher', exact=True).click()
        page.locator('#resultats-dossiers ul.resultats-dossiers a[href*="/dossiers/menage/"]').click()
        page.get_by_role('heading', name='Dossier — ' + self.m.libelle, exact=True).wait_for()


@skipIf(sync_playwright is None, 'Module Python Playwright non installé : qualification navigateur ignorée.')
class BD6Navigateur(EntreeBDNavigateur):
    """Nouveaux formulaires métier, testés sans s’appuyer sur les maquettes."""
    def setUp(self):
        super().setUp()
        from io import StringIO
        from django.core.management import call_command
        call_command('autoriser_bd6', self.u.username, stdout=StringIO())
        self.u.user_permissions.add(Permission.objects.get(content_type__app_label='personnes', codename='add_personne'))

    def test_histoire_commentaire_membre_et_retours(self):
        page = self.navigateur()
        page.goto(self.live_server_url + reverse('dossiers:detail', args=['menage', self.m.pk]) + '?q=Fictif')
        page.locator('.bd-commentaire').get_by_role('link', name='Modifier', exact=True).click()
        page.get_by_label('Commentaire libre', exact=False).fill('Accueil fictif à préparer.')
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_text('Accueil fictif à préparer.', exact=True).wait_for()
        emploi = page.locator('#social-' + str(self.p.pk) + '-emploi')
        emploi.get_by_text('Autres actions de la rubrique', exact=True).click()
        emploi.get_by_role('link', name='Historique', exact=True).click()
        page.locator('.social-valeurs > div').filter(has=page.get_by_text('Emploi / formation', exact=True)).get_by_role('link', name='Renseigner', exact=True).click()
        page.locator('[name=debut]').fill('2026-01-01')
        page.locator('[name=valeur]').select_option('formation')
        page.locator('[name=source]').fill('Entretien fictif navigateur')
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_role('heading', name='Histoire sociale — ' + str(self.p), exact=True).wait_for()
        rubrique = page.locator('.social-valeurs > div').filter(has=page.get_by_text('Emploi / formation', exact=True))
        page.set_viewport_size({'width': 390, 'height': 844})
        rubrique.get_by_role('link', name='Corriger une erreur', exact=True).click()
        self.assertTrue(page.locator('[name=debut]').is_disabled())
        self.assertIsNone(page.locator('[name=motif]').get_attribute('required'))
        page.get_by_label('Comment le savez-vous ?', exact=True).fill('Entretien fictif corrigé')
        page.locator('[name=motif]').fill('Erreur de transcription fictive')
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_text('Entretien fictif corrigé', exact=False).first.wait_for()
        page.get_by_role('link', name='← Revenir au dossier', exact=True).click()
        page.get_by_role('heading', name='Dossier — ' + str(self.m), exact=True).wait_for()
        page.get_by_role('link', name='Ajouter une personne', exact=True).click()
        page.wait_for_load_state('domcontentloaded')
        page.get_by_label('Nom ou prénom', exact=True).fill('Nouvelle fictive navigateur')
        page.get_by_text('Résultats actualisés.', exact=True).wait_for()
        page.get_by_role('link', name='Créer une personne et l’ajouter', exact=True).click()
        self.assertEqual(page.get_by_label('Nom ou désignation', exact=False).input_value(), 'Nouvelle fictive navigateur')
        page.locator('[name=debut]').fill('2026-02-01')
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_role('heading', name='Dossier — ' + str(self.m), exact=True).wait_for()
        page.locator('.bd-lien-projet').first.click()
        self.assertTrue(page.url.endswith('#projet'))
        self.assertTrue(page.locator('#projet').is_visible())
        page.get_by_role('heading', name='Prise en charge du 01/01/2026', exact=True).wait_for()
        self.assertNotIn('Nouvelle fictive navigateur', page.locator('.bd-titre').inner_text())
        page.get_by_role('link', name='Prolonger', exact=True).click()
        page.locator('[name=fin_prevue]').fill('2026-12-01')
        page.locator('[name=motif]').fill('Prévision fictive navigateur')
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_text('01/12/2026 (exclue)', exact=False).wait_for()
        page.set_viewport_size({'width': 360, 'height': 800})
        self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))


@skipIf(sync_playwright is None, 'Module Python Playwright non installé : qualification navigateur ignorée.')
class SejourUnifieNavigateur(BD6Navigateur):
    def test_prevoir_puis_confirmer_dans_la_meme_boite(self):
        from .models import AccordHebergement, Sejour
        page = self.navigateur()
        page.goto(self.live_server_url + reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk]))
        page.get_by_role('link', name='Nouveau séjour', exact=True).click()
        boite = page.locator('#hebergement')
        choix = boite.get_by_label('Arrivée déjà effectuée', exact=False)
        self.assertTrue(choix.is_checked())
        boite.locator('[name=debut]').fill('2026-01-01')
        choix.uncheck()
        self.assertFalse(boite.locator('[name=admission]').is_visible())
        boite.get_by_role('button', name='Enregistrer le séjour', exact=True).click()
        page.get_by_text('Dossier actualisé.', exact=True).wait_for()
        page.get_by_text('Prévu — arrivée à confirmer', exact=True).wait_for()
        avant = verifier_hors_boucle_playwright(lambda: (AccordHebergement.objects.count(), Sejour.objects.count()))
        self.assertEqual(avant, (2, 1))
        page.get_by_role('link', name='Enregistrer l’arrivée', exact=True).click()
        boite.get_by_label('Date d’arrivée', exact=False).fill('2026-01-05')
        boite.get_by_role('button', name='Enregistrer l’arrivée', exact=True).click()
        page.get_by_text('Dossier actualisé.', exact=True).wait_for()
        self.assertEqual(page.get_by_text('Prévu — arrivée à confirmer', exact=True).count(), 0)
        self.assertEqual(verifier_hors_boucle_playwright(lambda: (AccordHebergement.objects.count(), Sejour.objects.count())), (2, 2))
        self.assertEqual(boite.locator('a[aria-current=true]').count(), 1)

    def test_prevoir_sans_javascript(self):
        playwright = sync_playwright().start()
        self.addCleanup(playwright.stop)
        browser = playwright.chromium.launch()
        self.addCleanup(browser.close)
        page = browser.new_page(java_script_enabled=False)
        page.goto(self.live_server_url + '/connexion/')
        page.locator('[name=username]').fill(self.u.username)
        page.locator('[name=password]').fill('Recette-fictive-CHRS14!')
        page.get_by_role('button', name='Se connecter', exact=True).click()
        page.goto(self.live_server_url + reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk]))
        page.get_by_role('link', name='Nouveau séjour', exact=True).click()
        page.get_by_label('Arrivée déjà effectuée', exact=False).uncheck()
        page.get_by_role('button', name='Enregistrer le séjour', exact=True).click()
        page.get_by_role('heading', name='Prise en charge du 01/01/2026', exact=True).wait_for()
        page.get_by_text('Prévu — arrivée à confirmer', exact=True).wait_for()


@skipIf(sync_playwright is None, 'Module Python Playwright non installé : qualification navigateur ignorée.')
class ConditionSocialeNavigateur(StaticLiveServerTestCase):
    """Bloc commun réel : hiérarchie, saisie, retrait et identité répercutée."""
    navigateur = ProfilsNavigateur.navigateur

    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        from . import models as m
        self.u = get_user_model().objects.create_superuser('condition-fictive', password='Recette-fictive-CHRS14!')
        self.p = m.Personne.objects.create(designation='Thomas fictif', cree_par=self.u)
        self.m = m.Menage.objects.create(libelle='Ménage fictif', cree_par=self.u)
        ancien = timezone.localdate() - timedelta(days=30)
        self.entree = timezone.localdate() - timedelta(days=15)
        m.Appartenance.objects.create(menage=self.m, personne=self.p, debut=ancien)
        self.a = m.Accompagnement.objects.create(menage=self.m, debut=self.entree, cree_par=self.u)
        self.a.beneficiaires.add(self.p)
        m.CoordonneesPersonnelles.objects.create(personne=self.p, debut=ancien, ville='Bordeaux',
            telephone='06 11 11 11 11', source='Déclaration fictive', auteur=self.u)

    def test_menu_champs_repris_enregistrement_et_retrait(self):
        from . import models as m
        page = self.navigateur()
        page.set_viewport_size({'width': 1600, 'height': 1000})
        page.goto(self.live_server_url + reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk]))
        menu = page.locator('nav.condition-sommaire')
        social = menu.locator('.condition-menu > li').filter(has=page.locator('a[href="#condition-sociale"]'))
        self.assertEqual(social.locator('a[href="#condition-composition"]').count(), 1)
        self.assertEqual(social.locator('a[href="#social-' + str(self.p.pk) + '"]').count(), 1)
        self.assertEqual(social.locator('a[href="#projet"]').count(), 1)
        groupe = page.locator('#social-' + str(self.p.pk) + '-coordonnees')
        page.locator('[data-condition-contexte]').fill('Entretien fictif de qualification')
        # Un rafraîchissement depuis les prestations ne doit pas désactiver
        # l'édition sociale ni perdre le contexte de l'entretien.
        page.get_by_role('link', name='Nouveau séjour', exact=True).click()
        hebergement = page.locator('#hebergement')
        hebergement.locator('form[data-prestation-dossier]').wait_for()
        hebergement.get_by_role('button', name='← Revenir à la liste', exact=True).click()
        page.get_by_text('Dossier actualisé.', exact=True).wait_for()
        self.assertEqual(page.locator('[data-condition-contexte]').input_value(), 'Entretien fictif de qualification')
        groupe.get_by_role('link', name='Modifier', exact=True).click()
        form = groupe.locator('form[data-condition-form]')
        form.locator('[name=telephone]').fill('06 22 22 22 22')
        self.assertTrue(groupe.locator('[data-condition-lecture]').is_hidden())
        form.locator('[name=courriel]').fill('invalide')
        form.evaluate('form => form.noValidate = true')  # Exercer aussi le refus serveur.
        form.get_by_role('button', name='Enregistrer', exact=True).click()
        form.locator('.errorlist').first.wait_for()
        self.assertEqual(form.locator('[name=telephone]').input_value(), '06 22 22 22 22')
        form.locator('[name=courriel]').fill('')
        form.get_by_role('button', name='Enregistrer', exact=True).click()
        groupe.locator('dd').filter(has_text='06 22 22 22 22').wait_for()
        self.assertEqual(groupe.locator('dd.condition-valeur-heritee').filter(has_text='Bordeaux').count(), 1)
        self.assertEqual(groupe.locator('dd.condition-valeur-heritee').filter(has_text='06 22 22 22 22').count(), 0)
        groupe.locator('.condition-actions summary').click()
        groupe.get_by_role('link', name='Retirer ce changement', exact=True).click()
        form = groupe.locator('form[data-condition-form]')
        form.locator('[name=confirmer]').check()
        form.get_by_role('button', name='Enregistrer', exact=True).click()
        # La valeur héritée figure aussi dans l’aperçu avant validation :
        # attendre la disparition du formulaire après le vrai POST et refresh.
        form.wait_for(state='detached')
        groupe.locator('dd').filter(has_text='06 11 11 11 11').wait_for()
        self.assertEqual(verifier_hors_boucle_playwright(lambda: (
            m.CoordonneesPersonnelles.objects.count(), m.CoordonneesPersonnelles.tous.count(),
            m.RevisionCoordonneesPersonnelles.objects.filter(action='retrait').count())), (1, 2, 1))

    def test_identite_actualise_entete_et_sommaire_mobile(self):
        page = self.navigateur()
        page.goto(self.live_server_url + reverse('dossiers:detail', args=['personne', self.p.pk]))
        groupe = page.locator('#social-' + str(self.p.pk) + '-identite')
        groupe.get_by_role('link', name='Modifier', exact=True).click()
        form = groupe.locator('form[data-condition-form]')
        form.locator('[name=designation]').fill('Thomas corrigé fictif')
        form.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_role('heading', name='Dossier — Thomas corrigé fictif', exact=True).wait_for()
        self.assertEqual(page.locator('.condition-menu-mobile').get_by_role('link', name='Thomas corrigé fictif', exact=True, include_hidden=True).count(), 1)
        page.set_viewport_size({'width': 390, 'height': 844})
        mobile = page.locator('.condition-menu-mobile')
        mobile.locator(':scope > summary').click()
        mobile.get_by_role('link', name='Situation sociale et projet', exact=True).click()
        self.assertFalse(mobile.evaluate('element => element.open'))
        self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))


    def test_vue_dates_implicites_synthese_origines_et_annulation_sur_place(self):
        from playwright.sync_api import expect
        from django.utils import timezone
        from . import models as m
        page = self.navigateur()
        page.goto(self.live_server_url + reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk]))
        date_vue = page.locator('[data-condition-selection] input[type=date]')
        expect(date_vue).to_be_disabled()
        expect(date_vue).to_have_value(self.entree.isoformat())
        with page.expect_navigation():
            page.locator('[name=vue_sociale]').select_option('today')
        expect(date_vue).to_have_value(timezone.localdate().isoformat())
        expect(date_vue).to_be_disabled()
        page.locator('[name=vue_sociale]').select_option('date')
        expect(date_vue).to_be_enabled()
        with page.expect_navigation():
            date_vue.fill(self.entree.isoformat())
        with page.expect_navigation():
            page.locator('[name=presentation_sociale]').select_option('synthese')
        expect(page.locator('.condition-renseignee').first).to_be_visible()
        with page.expect_navigation():
            page.locator('[name=origines_sociales]').check()
        expect(page.locator('.condition-origine').first).to_be_visible()
        groupe = page.locator('#social-' + str(self.p.pk) + '-coordonnees')
        groupe.get_by_role('link', name='Modifier', exact=True).click()
        form = groupe.locator('form[data-condition-form]')
        expect(form).to_be_visible()
        expect(form.get_by_role('button', name='Enregistrer', exact=True)).to_be_disabled()
        expect(groupe.locator('[data-condition-lecture]')).to_be_hidden()
        form.locator('[name=telephone]').fill('06 99 99 99 99')
        page.once('dialog', lambda dialogue: dialogue.accept())
        form.get_by_role('button', name='Annuler', exact=True).click()
        expect(form).to_have_count(0)
        expect(groupe.locator('[data-condition-lecture]')).to_be_visible()
        self.assertEqual(verifier_hors_boucle_playwright(lambda: m.RevisionCoordonneesPersonnelles.objects.count()), 0)
        page.set_viewport_size({'width': 1600, 'height': 1000})
        menu = page.locator('.condition-menu').first
        depliants = menu.locator('.condition-nav-details')
        expect(depliants).to_have_count(2)
        depliants.nth(0).locator('summary').click(position={'x': 5, 'y': 5})
        expect(depliants.nth(0)).to_have_attribute('open', '')
        expect(depliants.nth(1)).not_to_have_attribute('open', '')
        page.locator('[data-condition-evolution]').click()
        evolution = page.locator('[data-evolution-selection]')
        expect(evolution).to_be_visible()
        expect(evolution.locator('[name=vue_debut]')).to_have_value('entree')
        expect(evolution.locator('input[type=date][name=debut]')).to_be_disabled()
        expect(evolution.locator('input[type=date][name=debut]')).to_have_value(self.entree.isoformat())
        evolution.locator('[name=vue_fin]').select_option('date')
        expect(evolution.locator('input[type=date][name=fin]')).to_be_enabled()
        evolution.locator('[name=vue_fin]').select_option('today')
        expect(page.locator('[data-evolution-selection] [name=vue_fin]')).to_have_value('today')
        expect(page.locator('[data-evolution-selection] input[type=date][name=fin]')).to_be_disabled()
