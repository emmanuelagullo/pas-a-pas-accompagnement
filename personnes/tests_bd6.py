"""BD6 : parcours, historiques, droits et écritures concurrentes sur données fictives."""
from datetime import date
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import transaction, IntegrityError
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from .tests_hebergement import Donnees
from . import bd6, suivi, hebergement, repas, social, dossier
from .models import (Personne, Menage, Accompagnement, SituationPersonnelle, SituationSociale,
    RevisionSituationPersonnelle, CommentaireDossier, EvolutionPriseEnCharge, Appartenance,
    AccordRepas, Sejour, EvenementSuivi)


class BD6Tests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        call_command('autoriser_bd6', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        self.client.force_login(self.u)
        self.url = reverse('dossiers:detail', args=['menage', self.m.pk])
        self.prise = reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk])

    def fait(self, valeur='sans_emploi', debut=date(2026, 2, 1), **kwargs):
        return bd6.renseigner(self.u, self.p, 'emploi', valeur, debut, 'Entretien fictif', bd6.jeton(self.p), **kwargs)

    def test_form2_structure_et_form3_prestations_bornees(self):
        autre = suivi.ouvrir(self.u, self.m, [self.p], date(2025, 1, 1))
        r = repas.accorder(self.u, autre, [self.p], date(2025, 1, 1), None, 'diner')
        page = self.client.get(self.url)
        self.assertContains(page, 'Prises en charge')
        self.assertContains(page, 'Situation sociale')
        self.assertContains(page, 'Commentaire libre')
        self.assertNotContains(page, 'id="hebergement"')
        self.assertContains(page, self.prise)
        page = self.client.get(self.prise)
        self.assertContains(page, 'id="hebergement"')
        self.assertContains(page, 'À l’entrée')
        self.assertEqual([a.pk for a in page.context['periodes']], [self.a.pk])
        self.assertEqual(page.context['accords_repas'], [])
        self.assertNotContains(page, str(r.pk))
        page = self.client.get(self.url, {'prise': autre.pk, 'action': 'ouvrir'})
        self.assertIn(str(autre.pk), page.url)

    def test_form3_parent_etranger_et_droit_retires_refuses(self):
        m = suivi.creer_menage(self.u, 'Autre fictif', [self.p], date(2025, 1, 1))
        a = suivi.ouvrir(self.u, m, [self.p], date(2025, 1, 1))
        self.assertEqual(self.client.get(reverse('dossiers:prise', args=['menage', self.m.pk, a.pk])).status_code, 404)
        self.u.user_permissions.remove(Permission.objects.get(content_type__app_label='personnes', codename='view_accompagnement'))
        self.assertEqual(self.client.get(self.prise).status_code, 403)

    def test_vue_personne_resume_sans_prestation_autrui(self):
        autre = Personne.objects.create(designation='Autre fictive', cree_par=self.u)
        self.a.beneficiaires.add(autre)
        r = repas.accorder(self.u, self.a, [autre], date(2026, 1, 1), date(2026, 2, 1), 'diner')
        page = self.client.get(reverse('dossiers:detail', args=['personne', self.p.pk]))
        self.assertNotIn('Repas', page.context['periodes'][0].resume_prestations)
        page = self.client.get(reverse('dossiers:prise', args=['personne', self.p.pk, self.a.pk]))
        self.assertNotIn(r.pk, [x.pk for x in page.context['accords_repas']])

    def test_resume_union_calendaire_et_lieux(self):
        hebergement.sortir(self.u, self.s, date(2026, 1, 13))
        self.s.refresh_from_db()
        deuxieme = SimpleNamespace(debut=date(2026, 1, 5), fin=date(2026, 1, 15))
        self.assertEqual(bd6.nombre_jours([self.s, deuxieme], date(2026, 2, 1)), 12)
        r1 = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), date(2026, 1, 21), 'dejeuner')
        r2 = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), date(2026, 1, 21), 'diner')
        texte = bd6.resume_prestations(self.a, [self.s], [r1, r2], date(2026, 2, 1))
        self.assertIn('10 nuits', texte)
        self.assertIn('20 jours accordés', texte)
        self.assertNotIn('40 jours', texte)

    def test_prolongation_journalisee_ne_touche_pas_prestations(self):
        attendu = bd6.jeton(self.a)
        bd6.prolonger(self.u, self.a, date(2026, 6, 1), 'Prévision fictive', attendu)
        self.a.refresh_from_db(); self.accord.refresh_from_db(); self.s.refresh_from_db()
        self.assertEqual(self.a.fin_prevue, date(2026, 6, 1))
        self.assertIsNone(self.a.fin)
        self.assertEqual(self.accord.fin, date(2026, 3, 1))
        self.assertIsNone(self.s.fin)
        self.assertEqual(EvolutionPriseEnCharge.objects.count(), 1)
        for fin, token in [(date(2026, 7, 1), attendu), (date(2026, 5, 1), bd6.jeton(self.a))]:
            with self.assertRaises(ValidationError):
                bd6.prolonger(self.u, self.a, fin, 'Fictif', token)
        self.assertEqual(EvolutionPriseEnCharge.objects.count(), 1)

    def test_prolongation_close_ou_sans_droit_refusee(self):
        hebergement.sortir(self.u, self.s, date(2026, 1, 13))
        suivi.clore(self.u, self.a, date(2026, 2, 1))
        with self.assertRaises(ValidationError):
            bd6.prolonger(self.u, self.a, date(2026, 7, 1), 'Fictif', bd6.jeton(self.a))
        self.u.user_permissions.remove(Permission.objects.get(codename='prolonger_accompagnement'))
        u = get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):
            bd6.prolonger(u, self.a, date(2026, 7, 1), 'Fictif', bd6.jeton(self.a))

    def test_histoire_personnelle_change_et_corrige_sans_duplication(self):
        premier = self.fait()
        second = self.fait('formation', date(2026, 3, 1))
        premier.refresh_from_db()
        self.assertEqual(premier.fin, second.debut)
        self.assertEqual(bd6.etat(self.u, [self.p], date(2026, 2, 10))[0]['lignes'][1]['texte'], 'Sans emploi')
        self.assertEqual(bd6.etat(self.u, [self.p], date(2026, 3, 1))[0]['lignes'][1]['texte'], 'En formation')
        bd6.renseigner(self.u, self.p, 'emploi', 'emploi', premier.debut, 'Document fictif', bd6.jeton(self.p),
            motif='Erreur de valeur fictive', correction=premier.pk)
        self.assertEqual(SituationPersonnelle.objects.count(), 2)
        revision = RevisionSituationPersonnelle.objects.first()
        self.assertEqual(revision.action, 'correction')
        self.assertEqual(revision.avant[0]['valeur'], 'sans_emploi')
        self.assertEqual(revision.apres[0]['valeur'], 'emploi')
        self.assertEqual(SituationSociale.objects.count(), 0)

    def test_insertion_retroactive_motivee_et_voisins(self):
        self.fait()
        self.fait('formation', date(2026, 4, 1))
        with self.assertRaises(ValidationError):
            self.fait('emploi', date(2026, 3, 1))
        fait = self.fait('emploi', date(2026, 3, 1), motif='Fait oublié fictif')
        self.assertEqual(fait.fin, date(2026, 4, 1))
        self.assertEqual(list(SituationPersonnelle.objects.values_list('fin', flat=True)), [date(2026, 3, 1), date(2026, 4, 1), None])
        self.assertEqual(RevisionSituationPersonnelle.objects.first().action, 'insertion')

    def test_social_refus_motif_doublon_etat_perime_mauvaise_cible(self):
        token = bd6.jeton(self.p)
        fait = self.fait()
        for kwargs in [{'attendu': token}, {'attendu': bd6.jeton(self.m)}, {'attendu': bd6.jeton(self.p), 'correction': fait.pk}]:
            with self.assertRaises(ValidationError):
                bd6.renseigner(self.u, self.p, 'emploi', 'emploi', fait.debut, 'Fictif', **kwargs)
        self.assertEqual(RevisionSituationPersonnelle.objects.count(), 1)
        self.assertEqual(SituationPersonnelle.objects.get().valeur, 'sans_emploi')

    def test_anciens_faits_divergents_conserves(self):
        a2 = suivi.ouvrir(self.u, self.m, [self.p], date(2026, 1, 1))
        social.renseigner(self.u, self.a, self.p, 'emploi', 'sans_emploi', date(2026, 1, 1), 'Ancien A fictif')
        social.renseigner(self.u, a2, self.p, 'emploi', 'emploi', date(2026, 1, 1), 'Ancien B fictif')
        etat = bd6.etat(self.u, [self.p], date(2026, 1, 15))[0]['lignes'][1]
        self.assertTrue(etat['conflit'])
        self.fait('formation', date(2026, 2, 1))
        self.assertEqual(bd6.etat(self.u, [self.p], date(2026, 2, 1))[0]['lignes'][1]['texte'], 'En formation')
        self.assertEqual(SituationSociale.objects.count(), 2)
        page = self.client.get(reverse('dossiers:social', args=[self.p.pk]))
        self.assertContains(page, 'Ancien A fictif'); self.assertContains(page, 'Ancien B fictif')

    def test_commentaires_versions_effacement_et_conflit(self):
        token = bd6.jeton(self.m)
        bd6.commenter(self.u, self.m, 'Premier commentaire fictif', '', token)
        with self.assertRaises(ValidationError):
            bd6.commenter(self.u, self.m, 'Écrasement fictif', 'Fictif', token)
        with self.assertRaises(ValidationError):
            bd6.commenter(self.u, self.m, '', '', bd6.jeton(self.m))
        bd6.commenter(self.u, self.m, '', 'Retrait motivé fictif', bd6.jeton(self.m))
        self.assertEqual(CommentaireDossier.objects.count(), 2)
        self.assertEqual(CommentaireDossier.objects.last().texte, 'Premier commentaire fictif')
        self.assertContains(self.client.get(self.url), 'Commentaire effacé.')

    def test_nouveaux_droits_non_implicites_et_csrf(self):
        u = get_user_model().objects.create_user('sans-bd6-fictif')
        call_command('autoriser_chrs7', u.username, stdout=StringIO())
        u = get_user_model().objects.get(pk=u.pk)
        self.assertFalse(u.has_perm('personnes.add_commentairedossier'))
        with self.assertRaises(PermissionDenied):
            bd6.commenter(u, self.m, 'Fictif', '', bd6.jeton(self.m))
        protege = Client(enforce_csrf_checks=True); protege.force_login(self.u)
        url = reverse('dossiers:commentaire', args=['menage', self.m.pk])
        self.assertEqual(protege.post(url, {}).status_code, 403)
        self.client.force_login(u)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_ajout_membre_selection_creation_et_beneficiaires_inchanges(self):
        self.u.user_permissions.add(Permission.objects.get(codename='add_personne', content_type__app_label='personnes'))
        self.u = get_user_model().objects.get(pk=self.u.pk)
        token = bd6.jeton(self.m)
        lien = bd6.ajouter_membre(self.u, self.m, date(2026, 2, 1), token, designation='Nouvelle fictive')
        self.assertEqual(lien.personne.designation, 'Nouvelle fictive')
        self.assertEqual(list(self.a.beneficiaires.all()), [self.p])
        nombre = Personne.objects.count()
        with self.assertRaises(ValidationError):
            bd6.ajouter_membre(self.u, self.m, date(2026, 3, 1), token, designation='À ne pas créer')
        self.assertEqual(Personne.objects.count(), nombre)
        with self.assertRaises(ValidationError):
            bd6.ajouter_membre(self.u, self.m, date(2026, 3, 1), bd6.jeton(self.m), personne=lien.personne)

    def test_recherche_membre_fragment_et_repli_get(self):
        url = reverse('dossiers:membre', args=[self.m.pk])
        for fragment in ('', '1'):
            page = self.client.get(url, {'q': 'Personne', 'fragment': fragment})
            self.assertContains(page, str(self.p))
            self.assertContains(page, 'personne=' + str(self.p.pk))
        page = self.client.get(url, {'personne': str(self.p.pk)})
        self.assertContains(page, 'Confirmez l’identité')
        self.assertNotIn('designation', page.context['form'].fields)

    def test_form3_retour_signe_et_defaults_sans_realisation_implicite(self):
        self.a.fin_prevue = date(2026, 12, 1); self.a.save(update_fields=['fin_prevue'])
        page = self.client.get(self.prise, {'q': 'Fictif'})
        nav = page.context['periodes'][0].navigation
        self.assertIn('/prises/' + str(self.a.pk), nav['retour_dossier'])
        url = reverse('dossiers:nouveau', args=['menage', self.m.pk, 'hebergement'])
        with patch('personnes.vues_prestations_dossier.timezone.localdate', return_value=date(2026, 5, 1)):
            nouveau = self.client.get(url, {'contexte_dossier': nav['contexte_dossier']})
        self.assertEqual(nouveau.context['form'].initial['debut'], date(2026, 5, 1))
        self.assertEqual(nouveau.context['form'].initial['fin'], self.a.fin_prevue)
        self.assertEqual(nouveau.context['form'].initial['admission'], date(2026, 5, 1))
        self.assertIn('/prises/' + str(self.a.pk), nouveau.context['retour'])
        self.assertIsNone(Sejour.objects.get().fin)
        self.assertEqual(dossier.lire(SimpleNamespace(user=self.u, POST={}, GET={'contexte_dossier': nav['contexte_dossier']}), self.a)['retour_dossier'], nav['retour_dossier'])

    def test_creation_prise_avec_prevision_et_pdf(self):
        url = reverse('dossiers:nouvelle_prise', args=['menage', self.m.pk])
        page = self.client.post(url, {'beneficiaires': [str(self.p.pk)], 'debut': '2026-05-01', 'fin_prevue': '2026-06-01'})
        self.assertEqual(page.status_code, 302)
        nouvelle = Accompagnement.objects.get(debut=date(2026, 5, 1))
        self.assertIn(str(nouvelle.pk), page.url)
        self.assertEqual(nouvelle.fin_prevue, date(2026, 6, 1))
        self.assertIsNone(nouvelle.fin)
        self.assertEqual(Sejour.objects.count(), 1)
        self.assertContains(self.client.get(reverse('suivi:resume', args=[nouvelle.pk])), '01/06/2026')

    def test_invalid_prevision_et_commentaire_cible_contrainte(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Accompagnement.objects.filter(pk=self.a.pk).update(fin_prevue=self.a.debut)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            CommentaireDossier.objects.create(personne=self.p, menage=self.m, texte='Fictif', auteur=self.u)

    def test_composition_conserve_recherche_dossier_malgre_nouveau_filtre(self):
        from urllib.parse import urlencode
        self.u.user_permissions.add(Permission.objects.get(codename='add_personne', content_type__app_label='personnes'))
        url = reverse('dossiers:membre', args=[self.m.pk])
        page = self.client.get(url, {'q': 'Recherche originale', 'page': '2'})
        query = urlencode({'contexte_composition': page.context['contexte_composition'], 'q': 'Nom nouveau fictif', 'nouvelle': '1'})
        form = self.client.get(url + '?' + query)
        page = self.client.post(url + '?' + query, {'attendu': form.context['form'].initial['attendu'],
            'designation': 'Nom nouveau fictif', 'prenom': '', 'debut': '2026-02-01'})
        self.assertEqual(page.status_code, 302)
        self.assertIn('q=Recherche+originale', page.url)
        self.assertIn('page=2', page.url)

    def test_date_de_travail_conservee_et_aucune_admission_antidatee(self):
        self.a.fin_prevue = date(2026, 12, 1); self.a.save(update_fields=['fin_prevue'])
        request = SimpleNamespace(user=self.u, POST={}, GET={'date_service': '2026-05-01'})
        nav = dossier.pour_prise(request, self.a, 'menage', self.m.pk, {})
        url = reverse('dossiers:nouveau', args=['menage', self.m.pk, 'hebergement'])
        page = self.client.get(url, {'contexte_dossier': nav['contexte_dossier']})
        self.assertEqual(page.context['form'].initial['debut'], date(2026, 5, 1))
        hebergement.sortir(self.u, self.s, date(2026, 1, 10))
        suivi.clore(self.u, self.a, date(2026, 2, 1))
        with patch('personnes.vues_prestations_dossier.timezone.localdate', return_value=date(2026, 5, 1)):
            page = self.client.get(url, {'accompagnement': str(self.a.pk)})
        self.assertEqual(page.context['form'].initial['admission'], date(2026, 5, 1))
        self.assertIsNone(page.context['form'].initial['fin'])

    def test_jeton_lu_avant_contenu_commentaire_et_situation(self):
        bd6.commenter(self.u, self.m, 'Ancien commentaire fictif', '', bd6.jeton(self.m))
        original = bd6.jeton
        def commentaire_concurrent(objet):
            bd6.commenter(self.u, objet, 'Commentaire concurrent fictif', 'Relais fictif', original(objet))
            return original(objet)
        with patch('personnes.vues_bd6.bd6.jeton', side_effect=commentaire_concurrent):
            page = self.client.get(reverse('dossiers:commentaire', args=['menage', self.m.pk]))
        self.assertEqual(page.context['form'].initial['texte'], 'Commentaire concurrent fictif')
        fait = self.fait()
        def correction_concurrente(objet):
            bd6.renseigner(self.u, objet, 'emploi', 'emploi', fait.debut, 'Source concurrente fictive', original(objet),
                motif='Correction concurrente fictive', correction=fait.pk)
            return original(objet)
        with patch('personnes.vues_bd6.bd6.jeton', side_effect=correction_concurrente):
            page = self.client.get(reverse('dossiers:social_corriger', args=[self.p.pk, 'emploi', fait.pk]))
        self.assertEqual(page.context['form'].initial['valeur'], 'emploi')

    def test_date_travail_traverse_form2_et_form3(self):
        request = SimpleNamespace(user=self.u, POST={}, GET={'date_service': '2026-05-01'})
        nav = dossier.pour_vue(request, self.a, 'menage', self.m.pk, {})
        form2 = self.client.get(self.url, {'contexte_dossier': nav['contexte_dossier']})
        form3 = self.client.get(form2.context['periodes'][0].url_prise)
        self.assertEqual(form3.context['prise'].navigation['dossier_valeurs']['date_service'], '2026-05-01')


class BD6Concurrence(Donnees, TransactionTestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_bd6', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)

    def test_deux_ecritures_sociales_un_seul_etat_valide(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections, close_old_connections, OperationalError
        barriere = Barrier(2)
        token = bd6.jeton(self.p)
        def ecrire(valeur):
            close_old_connections()
            try:
                u = get_user_model().objects.get(pk=self.u.pk)
                p = Personne.objects.get(pk=self.p.pk)
                barriere.wait(timeout=10)
                try:
                    bd6.renseigner(u, p, 'emploi', valeur, date(2026, 1, 1), 'Fictif', token)
                    return True
                except (ValidationError, OperationalError):
                    return False
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultat = list(pool.map(ecrire, ['emploi', 'sans_emploi']))
        self.assertEqual(sum(resultat), 1)
        self.assertEqual(SituationPersonnelle.objects.count(), 1)
        self.assertEqual(RevisionSituationPersonnelle.objects.count(), 1)


class BD6Reprise(TransactionTestCase):
    def test_migration_conserve_anciens_faits_sans_fusion_ni_droits(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        courant = executor.loader.graph.leaf_nodes()
        try:
            ancien = [('personnes', '0012_evolutions_accords_bd3')]
            executor.migrate(ancien)
            apps = executor.loader.project_state(ancien).apps
            u = apps.get_model('identites', 'Utilisateur').objects.create(username='migration-bd6-fictive', password='!')
            p = apps.get_model('personnes', 'Personne').objects.create(designation='Personne fictive', cree_par_id=u.pk)
            m = apps.get_model('personnes', 'Menage').objects.create(libelle='Ménage fictif', cree_par_id=u.pk)
            ids = []
            for valeur in ['emploi', 'sans_emploi']:
                a = apps.get_model('personnes', 'Accompagnement').objects.create(menage_id=m.pk, debut=date(2026, 1, 1), cree_par_id=u.pk)
                a.beneficiaires.add(p)
                fait = apps.get_model('personnes', 'SituationSociale').objects.create(accompagnement_id=a.pk,
                    beneficiaire_id=p.pk, dimension='emploi', valeur=valeur, debut=date(2026, 1, 1), source='Fictif', cree_par_id=u.pk)
                ids.append(fait.pk)
            MigrationExecutor(connection).migrate(courant)
            self.assertEqual(set(SituationSociale.objects.values_list('pk', flat=True)), set(ids))
            self.assertFalse(SituationPersonnelle.objects.exists())
            self.assertFalse(get_user_model().objects.get(pk=u.pk).user_permissions.exists())
            self.assertTrue(all(a.fin_prevue is None and a.fin is None for a in Accompagnement.objects.all()))
        finally:
            MigrationExecutor(connection).migrate(courant)

    def test_copie_zip_conserve_nouveaux_journaux(self):
        from contextlib import closing
        from pathlib import Path
        from tempfile import TemporaryDirectory
        import sqlite3
        from django.db import connection
        from pas_communs.paquets import creer_sauvegarde
        from pas_a_pas_accompagnement import paquets
        if connection.vendor != 'sqlite':
            self.skipTest('Les copies locales utilisent SQLite.')
        Donnees.preparer(self)
        call_command('autoriser_bd6', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        bd6.prolonger(self.u, self.a, date(2026, 6, 1), 'Prévision fictive', bd6.jeton(self.a))
        fait = bd6.renseigner(self.u, self.p, 'emploi', 'emploi', date(2026, 1, 1), 'Source fictive', bd6.jeton(self.p))
        bd6.renseigner(self.u, self.p, 'emploi', 'formation', fait.debut, 'Source corrigée fictive', bd6.jeton(self.p),
            motif='Correction fictive', correction=fait.pk)
        bd6.commenter(self.u, self.m, 'Version initiale fictive', '', bd6.jeton(self.m))
        bd6.commenter(self.u, self.m, 'Version suivante fictive', 'Relais fictif', bd6.jeton(self.m))
        with TemporaryDirectory() as temporaire:
            racine = Path(temporaire)
            source = racine / 'source'; source.mkdir()
            (source / 'secret-key').write_text('cle-fictive-bd6')
            with closing(sqlite3.connect(source / paquets.PROFIL.base)) as copie:
                connection.connection.backup(copie)
            archive = racine / 'bd6.zip'
            creer_sauvegarde(source, archive, profil=paquets.PROFIL)
            preparation = paquets.verifier(archive, racine, 'preparation')
            destination = racine / 'restauree'
            paquets.installer_copie(preparation, destination)
            with closing(sqlite3.connect(destination / paquets.PROFIL.base)) as db:
                self.assertEqual(db.execute('SELECT fin_prevue FROM personnes_accompagnement').fetchone(), ('2026-06-01',))
                self.assertEqual(db.execute('SELECT count(*) FROM personnes_evolutionpriseencharge').fetchone(), (1,))
                self.assertEqual(db.execute('SELECT count(*) FROM personnes_revisionsituationpersonnelle').fetchone(), (2,))
                self.assertEqual(db.execute('SELECT texte FROM personnes_commentairedossier ORDER BY id').fetchall(),
                    [('Version initiale fictive',), ('Version suivante fictive',)])
