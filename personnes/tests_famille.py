"""Déclarations familiales : dates, inconnus, droits, concurrence et exploitation."""
from datetime import date
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse

from . import famille, bd6
from .models import Personne, DeclarationFamiliale, RevisionDeclarationFamiliale
from .tests_hebergement import Donnees


def valeurs(**changements):
    resultat = dict(situation_familiale='Célibataire', rapports_parentaux='Perdus de vue',
        fratrie='Deux sœurs', enfants_a_charge=0, enfants_non_a_charge=None, grossesse=None)
    resultat.update(changements)
    return resultat


class FamilleTests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_solenne', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        self.client.force_login(self.u)
        self.url = reverse('dossiers:famille', args=[self.p.pk])

    def creer(self, debut=date(2026, 1, 1), **kwargs):
        return famille.renseigner(self.u, self.p, debut, 'Entretien fictif', bd6.jeton(self.p),
            **valeurs(**kwargs))

    def test_declaration_independante_du_menage_et_inconnus_distincts_de_zero(self):
        fait = self.creer()
        self.assertEqual(fait.enfants_a_charge, 0)
        self.assertIsNone(fait.enfants_non_a_charge)
        self.assertIsNone(fait.grossesse)
        self.assertEqual(self.m.appartenances.count(), 1)
        self.assertEqual(list(self.a.beneficiaires.all()), [self.p])
        self.assertEqual(famille.a_date([self.p], date(2026, 1, 10)).get(), fait)
        self.assertFalse(famille.a_date([self.p], date(2025, 12, 31)).exists())
        page = self.client.get(self.url, {'date': '2026-01-10'})
        self.assertContains(page, 'Deux sœurs')
        self.assertContains(page, 'Perdus de vue')
        self.assertContains(page, 'Non renseigné')

    def test_changement_insertion_et_correction_date_preservent_voisins_et_journaux(self):
        premier = self.creer()
        dernier = self.creer(date(2026, 4, 1), situation_familiale='En couple', enfants_a_charge=2)
        token = bd6.jeton(self.p)
        with self.assertRaises(ValidationError):
            famille.renseigner(self.u, self.p, date(2026, 3, 1), 'Fictif', token, **valeurs())
        inter = famille.renseigner(self.u, self.p, date(2026, 3, 1), 'Fictif', token,
            motif='Fait oublié fictif', **valeurs(situation_familiale='Séparée'))
        premier.refresh_from_db(); dernier.refresh_from_db()
        self.assertEqual(premier.fin, date(2026, 3, 1))
        self.assertEqual(inter.fin, dernier.debut)
        revision = RevisionDeclarationFamiliale.objects.first()
        self.assertEqual(revision.action, 'insertion')
        self.assertEqual(len(revision.avant), 2)
        self.assertEqual(len(revision.apres), 3)
        famille.renseigner(self.u, self.p, date(2026, 2, 15), 'Document corrigé fictif', bd6.jeton(self.p),
            motif='Jour incorrect fictif', correction=inter.pk, **valeurs(situation_familiale='Séparée', grossesse=False))
        premier.refresh_from_db(); inter.refresh_from_db(); dernier.refresh_from_db()
        self.assertEqual(premier.fin, inter.debut)
        self.assertEqual(inter.fin, dernier.debut)
        self.assertIsNone(dernier.fin)
        self.assertFalse(inter.grossesse)
        self.assertEqual(famille.a_date([self.p], date(2026, 2, 20)).get(), inter)
        self.assertEqual(RevisionDeclarationFamiliale.objects.first().avant[1]['debut'], '2026-03-01')

    def test_refus_sans_ecriture_sur_mauvaise_cible_doublon_traversee_et_future(self):
        premier = self.creer()
        self.creer(date(2026, 4, 1))
        autre = Personne.objects.create(designation='Autre fictive', cree_par=self.u)
        for cible, debut, correction in [(self.p, date(2026, 4, 1), premier.pk),
            (self.p, date(2026, 5, 1), premier.pk), (autre, date(2026, 2, 1), premier.pk),
            (self.p, date(9999, 1, 1), None)]:
            with self.assertRaises(ValidationError):
                famille.renseigner(self.u, cible, debut, 'Fictif', bd6.jeton(cible),
                    motif='Erreur fictive', correction=correction, **valeurs(situation_familiale='Autre'))
        self.assertEqual(DeclarationFamiliale.objects.count(), 2)
        self.assertEqual(RevisionDeclarationFamiliale.objects.count(), 2)
        premier.refresh_from_db()
        self.assertEqual(premier.debut, date(2026, 1, 1))
        self.assertEqual(premier.fin, date(2026, 4, 1))

    def test_formulaire_perime_et_echec_journal_annulent_tout(self):
        token = bd6.jeton(self.p)
        self.creer()
        with self.assertRaises(ValidationError):
            famille.renseigner(self.u, self.p, date(2026, 2, 1), 'Fictif', token, **valeurs())
        avant = famille.photographie(self.p)
        with patch.object(RevisionDeclarationFamiliale.objects, 'create', side_effect=RuntimeError('Échec fictif')):
            with self.assertRaises(RuntimeError):
                self.creer(date(2026, 2, 1))
        self.assertEqual(famille.photographie(self.p), avant)

    def test_valeurs_negatives_source_vide_et_aucune_modification_refusees(self):
        fait = self.creer()
        for donnees in [valeurs(enfants_a_charge=-1), valeurs(enfants_non_a_charge=-1)]:
            with self.assertRaises(ValidationError):
                famille.renseigner(self.u, self.p, date(2026, 2, 1), 'Fictif', bd6.jeton(self.p), **donnees)
        with self.assertRaises(ValidationError):
            famille.renseigner(self.u, self.p, date(2026, 2, 1), ' ', bd6.jeton(self.p), **valeurs())
        with self.assertRaises(ValidationError):
            famille.renseigner(self.u, self.p, fait.debut, fait.source, bd6.jeton(self.p),
                correction=fait.pk, motif='Aucune différence fictive', **valeurs())
        self.assertEqual(DeclarationFamiliale.objects.count(), 1)

    def test_formulaire_http_erreurs_nommees_et_retour_prise_et_selections(self):
        url = reverse('dossiers:famille_nouvelle', args=[self.p.pk])
        query = f'?depuis_nature=menage&depuis_pk={self.m.pk}&depuis_prise={self.a.pk}&sejour={self.s.pk}&q=Fictif&date_service=2026-01-10'
        page = self.client.get(url + query)
        data = {'debut': '2026-01-02', 'situation_familiale': 'En couple', 'rapports_parentaux': '',
            'fratrie': '', 'enfants_a_charge': '0', 'enfants_non_a_charge': '', 'grossesse': 'unknown',
            'source': 'Entretien fictif', 'attendu': page.context['form'].initial['attendu']}
        self.assertEqual(self.client.post(url + query, data).status_code, 302)
        retour = self.client.get(self.url + query).context['retour']
        self.assertIn('/prises/' + str(self.a.pk), retour)
        self.assertIn('sejour=' + str(self.s.pk), retour)
        self.assertIn('date_service=2026-01-10', retour)
        self.assertIn('q=Fictif', retour)
        # Sans JavaScript, les champs conservent valeurs et erreurs nommées.
        data.update(debut='9999-01-01', attendu=bd6.jeton(self.p))
        page = self.client.post(url + query, data)
        self.assertEqual(page.status_code, 409)
        self.assertIn('debut', page.context['form'].errors)
        self.assertContains(page, 'href="#id_debut"', status_code=409)
        self.assertContains(page, 'En couple', status_code=409)

    def test_lecture_et_editions_bd_bornees_par_personne_date_et_droit(self):
        self.creer(situation_familiale='Situation A fictive')
        self.creer(date(2026, 2, 1), situation_familiale='Situation B fictive')
        page = self.client.get(reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk]))
        self.assertContains(page, 'Situation A fictive')  # à l'entrée
        self.assertNotContains(page, 'Situation B fictive')
        self.assertContains(page, 'Situation familiale déclarée')
        self.assertContains(page, 'date=2026-01-01&amp;depuis_nature=menage')
        actuelle = self.client.get(reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk]), {'vue_sociale': 'today'})
        self.assertContains(actuelle, 'Situation B fictive')
        self.assertNotContains(actuelle, 'Situation A fictive')
        page = self.client.get(reverse('suivi:resume', args=[self.a.pk]))
        self.assertContains(page, 'Situation A fictive')
        self.assertNotContains(page, 'Situation B fictive')
        self.u.user_permissions.remove(Permission.objects.get(codename='view_declarationfamiliale'))
        page = self.client.get(reverse('dossiers:detail', args=['personne', self.p.pk]))
        self.assertNotContains(page, 'Situation B fictive')
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_rapport_population_filtres_bornes_csv_et_non_additivite(self):
        self.creer(enfants_a_charge=2, grossesse=True)
        self.creer(date(2026, 2, 1), situation_familiale='En couple', enfants_a_charge=2)
        autre = Personne.objects.create(designation='Autre fictive', cree_par=self.u)
        url = reverse('dossiers:rapport_familles')
        page = self.client.get(url, {'date': '2026-01-31'})
        self.assertEqual(page.context['nombre'], 2)
        self.assertEqual(dict(page.context['bilan']), {'Aucune déclaration applicable': 1, 'Célibataire': 1})
        self.assertContains(page, 'ne sont pas additionnés')
        page = self.client.get(url, {'date': '2026-02-01', 'situation': 'en COUPLE'})
        self.assertEqual(page.context['nombre'], 1)
        csv = self.client.get(url, {'date': '2026-01-31', 'format': 'csv'}).content.decode()
        self.assertIn('Célibataire', csv)
        self.assertIn(';Oui;', csv)
        self.assertNotIn('En couple', csv)
        page = self.client.get(url, {'date': '2026-01-31', 'renseignement': 'inconnue'})
        self.assertEqual([l['personne'].pk for l in page.context['page_obj']], [autre.pk])

    def test_csv_ne_convertit_pas_texte_en_formule_et_histoire_est_echappee(self):
        self.p.designation = '=1+1'; self.p.save()
        self.creer(situation_familiale='<script>Fictif</script>', fratrie='@fonction()')
        self.assertContains(self.client.get(self.url), '&lt;script&gt;Fictif&lt;/script&gt;')
        response = self.client.get(reverse('dossiers:rapport_familles'), {'date': '2026-01-10', 'format': 'csv'})
        csv = response.content.decode()
        self.assertIn("'=1+1", csv)
        self.assertIn("'@fonction()", csv)
        self.assertIn('no-store', response['Cache-Control'])

    def test_aucun_droit_implicite_csrf_et_cible_etrangere(self):
        protege = Client(enforce_csrf_checks=True); protege.force_login(self.u)
        self.assertEqual(protege.post(reverse('dossiers:famille_nouvelle', args=[self.p.pk]), {}).status_code, 403)
        u = get_user_model().objects.create_user('Sans-famille-fictif')
        call_command('autoriser_chrs7', u.username, stdout=StringIO())
        u = get_user_model().objects.get(pk=u.pk)
        self.assertFalse(u.has_perm('personnes.view_declarationfamiliale'))
        with self.assertRaises(PermissionDenied):
            famille.renseigner(u, self.p, date(2026, 1, 1), 'Fictif', bd6.jeton(self.p), **valeurs())
        self.client.force_login(u)
        for url in [self.url, reverse('dossiers:rapport_familles')]:
            self.assertEqual(self.client.get(url).status_code, 403)


class FamilleConcurrenceTests(Donnees, TransactionTestCase):
    def test_migration_ne_reinterprete_pas_anciens_champs_et_ne_donne_pas_de_droits(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        courant = executor.loader.graph.leaf_nodes()
        ancien = [('personnes', '0014_textes_enrichis')]
        try:
            executor.migrate(ancien)
            apps = executor.loader.project_state(ancien).apps
            u = apps.get_model('identites', 'Utilisateur').objects.create(username='Ancien-solenne-fictif', password='!')
            p = apps.get_model('personnes', 'Personne').objects.create(designation='Ancienne fictive', cree_par_id=u.pk)
            m = apps.get_model('personnes', 'Menage').objects.create(libelle='Ancien ménage fictif', cree_par_id=u.pk)
            a = apps.get_model('personnes', 'Accompagnement').objects.create(menage_id=m.pk,
                debut=date(2026, 1, 1), fin_prevue=date(2026, 6, 1), cree_par_id=u.pk)
            apps.get_model('personnes', 'EvolutionPriseEnCharge').objects.create(accompagnement_id=a.pk,
                ancienne_fin=None, nouvelle_fin=date(2026, 6, 1), motif='Fictif', auteur_id=u.pk)
            MigrationExecutor(connection).migrate(courant)
            from .models import EvolutionPriseEnCharge, Accompagnement
            self.assertEqual(EvolutionPriseEnCharge.objects.get().action, 'prolongation')
            self.assertEqual(Accompagnement.objects.get(pk=a.pk).fin_prevue, date(2026, 6, 1))
            self.assertFalse(DeclarationFamiliale.objects.exists())
            from .models import ContactMenage, Partenaire
            self.assertFalse(ContactMenage.objects.exists())
            self.assertFalse(Partenaire.objects.exists())
            self.assertFalse(get_user_model().objects.get(pk=u.pk).user_permissions.exists())
            self.assertEqual(Personne.objects.get(pk=p.pk).designation, 'Ancienne fictive')
        finally:
            MigrationExecutor(connection).migrate(courant)

    def test_copie_zip_conserve_serie_et_corrections_familiales(self):
        import sqlite3
        from contextlib import closing
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.db import connection
        from pas_communs.paquets import creer_sauvegarde
        from pas_a_pas_accompagnement import paquets
        if connection.vendor != 'sqlite':
            self.skipTest('Les copies locales utilisent SQLite.')
        self.preparer()
        call_command('autoriser_solenne', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        fait = famille.renseigner(self.u, self.p, date(2026, 1, 1), 'Entretien fictif',
            bd6.jeton(self.p), **valeurs(enfants_a_charge=2))
        famille.renseigner(self.u, self.p, date(2026, 1, 2), 'Date corrigée fictive',
            bd6.jeton(self.p), correction=fait.pk, motif='Erreur fictive', **valeurs(enfants_a_charge=1))
        with TemporaryDirectory() as temporaire:
            racine = Path(temporaire)
            source = racine / 'source'; source.mkdir()
            (source / 'secret-key').write_text('cle-fictive-famille')
            with closing(sqlite3.connect(source / paquets.PROFIL.base)) as copie:
                connection.connection.backup(copie)
            archive = racine / 'famille.zip'
            creer_sauvegarde(source, archive, profil=paquets.PROFIL)
            preparation = paquets.verifier(archive, racine, 'preparation')
            destination = racine / 'restauree'
            paquets.installer_copie(preparation, destination)
            with closing(sqlite3.connect(destination / paquets.PROFIL.base)) as db:
                self.assertEqual(db.execute('SELECT debut, enfants_a_charge, enfants_non_a_charge, grossesse FROM personnes_declarationfamiliale').fetchone(),
                    ('2026-01-02', 1, None, None))
                self.assertEqual(db.execute('SELECT action FROM personnes_revisiondeclarationfamiliale ORDER BY id').fetchall(),
                    [('changement',), ('correction',)])

    def test_deux_declarations_ne_secrasent_pas(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections, OperationalError
        self.preparer()
        call_command('autoriser_solenne', self.u.username, stdout=StringIO())
        token = bd6.jeton(self.p)
        depart = Barrier(2)
        def ecrire(situation):
            close_old_connections()
            try:
                u = get_user_model().objects.get(pk=self.u.pk); u.get_all_permissions()
                p = Personne.objects.get(pk=self.p.pk)
                depart.wait(timeout=10)
                try:
                    famille.renseigner(u, p, date(2026, 1, 1), 'Fictif', token,
                        **valeurs(situation_familiale=situation))
                    return True
                except (ValidationError, OperationalError):
                    return False
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultats = list(pool.map(ecrire, ['A fictive', 'B fictive']))
        self.assertEqual(sum(resultats), 1, resultats)
        self.assertEqual(DeclarationFamiliale.objects.count(), 1)
        self.assertEqual(RevisionDeclarationFamiliale.objects.count(), 1)
