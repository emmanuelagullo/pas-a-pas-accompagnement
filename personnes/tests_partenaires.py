from datetime import date
from io import StringIO
from unittest.mock import patch
from urllib.parse import urlencode
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from . import partenaires, bd6, hebergement, dossier
from .models import Partenaire, FichePartenaire, RevisionFichePartenaire, Personne
from .tests_hebergement import Donnees


def valeurs(**changements):
    d = dict(nom='Association fictive', rue='Rue fictive', code_postal='00100', ville='Ville fictive',
        pays='Pays fictif', telephone='+00 123 fictif', courriel='service@example.invalid', fax='', informations='Accueil sur rendez-vous fictif.')
    d.update(changements)
    return d


class PartenairesTests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_solenne', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        self.client.force_login(self.u)

    def creer(self, **kwargs):
        return partenaires.creer(self.u, date(2026, 1, 1), 'Source fictive', partenaires.jeton_creation(), **valeurs(**kwargs))

    def test_creation_explicitement_distincte_des_homonymes_et_des_personnes(self):
        token = partenaires.jeton_creation()
        p = partenaires.creer(self.u, date(2026, 1, 1), 'Source fictive', token, **valeurs())
        with self.assertRaises(ValidationError):
            partenaires.creer(self.u, date(2026, 1, 1), 'Source fictive', token, **valeurs())
        second = self.creer()
        self.assertNotEqual(p.pk, second.pk)
        self.assertEqual(Partenaire.objects.count(), 2)
        self.assertEqual(Personne.objects.count(), 1)
        self.assertEqual(p.fiches.get().code_postal, '00100')

    def test_changement_insertion_et_correction_preservent_le_nom_courant(self):
        p = self.creer()
        premier = p.fiches.get()
        partenaires.renseigner(self.u, p, date(2026, 4, 1), 'Source fictive', bd6.jeton(p), **valeurs(nom='Nom actuel fictif'))
        inter = partenaires.renseigner(self.u, p, date(2026, 3, 1), 'Fait oublié fictif', bd6.jeton(p),
            motif='Oubli fictif', **valeurs(nom='Nom intermédiaire fictif'))
        partenaires.renseigner(self.u, p, date(2026, 2, 1), 'Source corrigée fictive', bd6.jeton(p),
            motif='Mauvaise date fictive', correction=inter.pk, **valeurs(nom='Nom corrigé fictif'))
        p.refresh_from_db(); premier.refresh_from_db(); inter.refresh_from_db()
        self.assertEqual(p.libelle, 'Nom actuel fictif')
        self.assertEqual(premier.fin, date(2026, 2, 1))
        self.assertEqual(inter.fin, date(2026, 4, 1))
        self.assertEqual(partenaires.a_date([p], date(2026, 3, 1)).get().nom, 'Nom corrigé fictif')
        self.assertEqual(RevisionFichePartenaire.objects.first().action, 'correction')

    def test_source_courriel_date_future_et_echec_journal_ne_creent_pas_de_coquille(self):
        for debut, source, donnees in [(date(9999, 1, 1), 'Fictif', valeurs()),
            (date(2026, 1, 1), '', valeurs()), (date(2026, 1, 1), 'Fictif', valeurs(courriel='invalide')),
            (date(2026, 1, 1), 'Fictif', valeurs(nom=' '))]:
            with self.assertRaises(ValidationError):
                partenaires.creer(self.u, debut, source, partenaires.jeton_creation(), **donnees)
        with patch.object(RevisionFichePartenaire.objects, 'create', side_effect=RuntimeError('Fictif')):
            with self.assertRaises(RuntimeError):
                self.creer()
        self.assertFalse(Partenaire.objects.exists())

    def test_ancien_formulaire_et_correction_mauvaise_cible_refuses(self):
        p = self.creer(); token = bd6.jeton(p)
        partenaires.renseigner(self.u, p, date(2026, 2, 1), 'Fictif', token, **valeurs(nom='Nouveau fictif'))
        with self.assertRaises(ValidationError):
            partenaires.renseigner(self.u, p, date(2026, 3, 1), 'Fictif', token, **valeurs())
        autre = self.creer(nom='Autre fictif')
        with self.assertRaises(ValidationError):
            partenaires.renseigner(self.u, autre, date(2026, 1, 1), 'Fictif', bd6.jeton(autre),
                correction=p.fiches.first().pk, motif='Mauvaise cible fictive', **valeurs())
        self.assertEqual(FichePartenaire.objects.count(), 3)

    def test_recherche_et_csv_a_date_sans_formules_ni_html_actif(self):
        p = self.creer(nom='=FORMULE()', informations='<script>Fictif</script>')
        partenaires.renseigner(self.u, p, date(2026, 2, 1), 'Fictif', bd6.jeton(p), **valeurs(nom='Autre nom fictif'))
        url = reverse('dossiers:partenaires')
        page = self.client.get(url, {'date': '2026-01-31', 'q': 'Ville'})
        self.assertContains(page, '=FORMULE()')
        self.assertNotContains(page, 'Autre nom fictif')
        csv = self.client.get(url, {'date': '2026-01-31', 'format': 'csv'}).content.decode()
        self.assertIn("'=FORMULE()", csv)
        self.assertNotIn('Autre nom fictif', csv)
        page = self.client.get(reverse('dossiers:partenaire', args=[p.pk]), {'date': '2026-01-31'})
        self.assertContains(page, '&lt;script&gt;Fictif&lt;/script&gt;')

    def test_creation_http_et_retours_signes_vers_prise(self):
        page = self.client.get(reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk]), {'q': 'Fictif', 'sejour': self.s.pk})
        token = page.context['prise'].navigation['contexte_dossier']
        query = urlencode({'prise': self.a.pk, 'contexte_dossier': token, 'q': 'Association', 'date': '2026-01-10'})
        url = reverse('dossiers:partenaire_creer') + '?' + query
        page = self.client.get(url)
        data = dict(valeurs(), debut='2026-01-01', source='Fictif', attendu=page.context['form'].initial['attendu'])
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        page = self.client.get(response.url)
        self.assertIn('/prises/' + str(self.a.pk), page.context['retour_dossier'])
        self.assertIn('contexte_dossier=', page.context['retour_dossier'])
        self.assertIn('date=2026-01-10', response.url)
        self.assertEqual(self.client.post(url, data).status_code, 409)

    def test_droits_csrf_et_ancienne_saisie_libre_inchangee(self):
        ancien = hebergement.creer_lieu(self.u, 'Ancien lieu fictif', 'Association fictive')
        p = self.creer()
        ancien.refresh_from_db()
        self.assertIsNone(ancien.organisme_id)
        self.assertEqual(ancien.partenaire, 'Association fictive')
        protege = Client(enforce_csrf_checks=True); protege.force_login(self.u)
        self.assertEqual(protege.post(reverse('dossiers:partenaire_creer'), {}).status_code, 403)
        self.u.user_permissions.remove(Permission.objects.get(codename='view_fichepartenaire'))
        self.assertEqual(self.client.get(reverse('dossiers:partenaire', args=[p.pk])).status_code, 403)
        self.assertNotContains(self.client.get(reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk])), 'Consulter le répertoire des organismes')

    def test_lieu_reutilise_identite_sans_recopier_coordonnees(self):
        p = self.creer()
        lieu = hebergement.creer_lieu(self.u, 'Nouveau lieu fictif', organisme=p)
        self.assertEqual(lieu.organisme_id, p.pk)
        self.assertEqual(lieu.partenaire, '')
        with self.assertRaises(ValidationError):
            hebergement.creer_lieu(self.u, 'Ambigu fictif', partenaire='Autre nom fictif', organisme=p)
        self.u.user_permissions.remove(Permission.objects.get(codename='view_partenaire'))
        u = get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):
            hebergement.creer_lieu(u, 'Interdit fictif', organisme=p)


class PartenairesConcurrenceTests(Donnees, TransactionTestCase):
    def test_copie_restauree_conserve_identite_versions_et_lien_lieu(self):
        import sqlite3
        from contextlib import closing
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.db import connection
        from pas_communs.paquets import creer_sauvegarde
        from pas_a_pas_accompagnement import paquets
        if connection.vendor != 'sqlite':
            self.skipTest('Copie locale SQLite uniquement.')
        self.preparer(); call_command('autoriser_solenne', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        p = partenaires.creer(self.u, date(2026, 1, 1), 'Source fictive', partenaires.jeton_creation(), **valeurs())
        lieu = hebergement.creer_lieu(self.u, 'Lieu du répertoire fictif', organisme=p)
        partenaires.renseigner(self.u, p, date(2026, 2, 1), 'Nouvelle adresse fictive', bd6.jeton(p), **valeurs(ville='Autre ville fictive'))
        with TemporaryDirectory() as temporaire:
            racine = Path(temporaire); source = racine/'source'; source.mkdir()
            (source/'secret-key').write_text('cle-fictive-partenaires')
            with closing(sqlite3.connect(source/paquets.PROFIL.base)) as copie:
                connection.connection.backup(copie)
            archive = racine/'annuaire.zip'; creer_sauvegarde(source, archive, profil=paquets.PROFIL)
            preparation = paquets.verifier(archive, racine, 'preparation')
            destination = racine/'restauree'; paquets.installer_copie(preparation, destination)
            with closing(sqlite3.connect(destination/paquets.PROFIL.base)) as db:
                self.assertEqual(db.execute('SELECT organisme_id FROM personnes_lieuhebergement WHERE id=?', (lieu.pk,)).fetchone(), (p.pk.hex,))
                self.assertEqual(db.execute('SELECT ville FROM personnes_fichepartenaire ORDER BY debut').fetchall(), [('Ville fictive',), ('Autre ville fictive',)])
                self.assertEqual(db.execute('SELECT count(*) FROM personnes_revisionfichepartenaire').fetchone(), (2,))

    def test_creation_concurrente_meme_confirmation_une_seule_fiche(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections, OperationalError
        self.preparer()
        call_command('autoriser_solenne', self.u.username, stdout=StringIO())
        token = partenaires.jeton_creation(); depart = Barrier(2)
        def ecrire(_):
            close_old_connections()
            try:
                u = get_user_model().objects.get(pk=self.u.pk); u.get_all_permissions()
                depart.wait(timeout=10)
                try:
                    partenaires.creer(u, date(2026, 1, 1), 'Fictif', token, **valeurs())
                    return True
                except (ValidationError, OperationalError):
                    return False
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultat = list(pool.map(ecrire, range(2)))
        self.assertEqual(sum(resultat), 1, resultat)
        self.assertEqual(Partenaire.objects.count(), 1)
        self.assertEqual(FichePartenaire.objects.count(), 1)
        self.assertEqual(RevisionFichePartenaire.objects.count(), 1)
