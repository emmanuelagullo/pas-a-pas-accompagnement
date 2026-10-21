"""Recette Chromium des permissions métier (lancée explicitement en CI)."""
from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth.models import Permission
from django.db import connections
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from playwright.sync_api import sync_playwright

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
        page.get_by_role('link', name='Accorder et enregistrer une admission', exact=True).click()
        page.locator('input[name="debut"]').fill('2026-02-01')
        page.locator('input[name="fin"]').fill('2026-03-01')
        page.locator('input[name="admission"]').fill('2026-02-03')
        page.locator('select[name="lieu"]').select_option(str(self.lieu.pk))
        page.get_by_role('button', name='Créer l’accord et enregistrer les admissions').click()
        page.get_by_role('heading', name='Dossier — ' + self.m.libelle, exact=True).wait_for()
        self.assertEqual(page.locator('input[name="sejour"]').count(), 3)
        def nouvel_identifiant():
            return str(AccordHebergement.objects.exclude(pk=self.accord.pk).get().sejours.first().pk)
        identifiant = verifier_hors_boucle_playwright(nouvel_identifiant)
        page.locator('input[name="sejour"][value="' + identifiant + '"]').check()
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
        page.locator('input[name="motif"]').fill('Projet préparé')
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.get_by_role('link', name='Situation et parcours sociaux', exact=True).click()
        page.get_by_role('link', name='Renseigner Emploi / formation', exact=True).click()
        page.locator('select[name="beneficiaire"]').select_option(str(self.p.pk))
        page.locator('select[name="valeur"]').select_option('formation')
        page.locator('input[name="debut"]').fill('2026-01-10')
        page.locator('input[name="source"]').fill('Source fictive précisée')
        page.locator('input[name="motif"]').fill('Situation oubliée')
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
        page.locator('input[name="sejour"][value="' + str(self.s.pk) + '"]').check()
        page.get_by_role('button', name='Afficher les actions du séjour choisi', exact=True).click()
        self.assertTrue(page.locator('input[name="sejour"][value="' + str(self.s.pk) + '"]').is_checked())
        self.assertTrue(page.locator('input[name="repas"][value="' + str(accord_repas.pk) + '"]').is_checked())
        self.assertEqual(page.get_by_role('link', name='Enregistrer la sortie', exact=True).count(), 0)
        self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))
        page.get_by_role('link', name='Corriger les dates du séjour', exact=True).click()
        page.get_by_role('link', name='Annuler et revenir', exact=True).click()
        self.assertTrue(page.locator('input[name="sejour"][value="' + str(self.s.pk) + '"]').is_checked())
        self.assertTrue(page.locator('input[name="repas"][value="' + str(accord_repas.pk) + '"]').is_checked())
