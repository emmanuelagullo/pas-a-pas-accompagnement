"""Coordonnées personnelles datées : aucune assimilation au logement ou aux partenaires."""
from datetime import date
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from . import bd6, coordonnees, famille
from .models import Personne, CoordonneesPersonnelles, RevisionCoordonneesPersonnelles
from .tests_hebergement import Donnees


def valeurs(**changements):
    d = dict(rue='1 rue de l’Exemple fictif', code_postal='00100', ville='Ville fictive', pays='Pays fictif',
        telephone='+00 123 fictif', courriel='personne@example.invalid', fax='')
    d.update(changements)
    return d


class CoordonneesTests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_solenne', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        self.client.force_login(self.u)
        self.url = reverse('dossiers:coordonnees', args=[self.p.pk])

    def creer(self, debut=date(2026, 1, 1), **kwargs):
        return coordonnees.renseigner(self.u, self.p, debut, 'Entretien fictif', bd6.jeton(self.p), **valeurs(**kwargs))

    def test_coordonnees_sans_ecriture_hebergement_et_rendu_echappe(self):
        fait = self.creer(rue='<script>Adresse fictive</script>')
        self.assertEqual(fait.code_postal, '00100')
        self.assertEqual(self.s.affectations.count(), 0)
        self.assertEqual(self.m.appartenances.count(), 1)
        self.assertContains(self.client.get(self.url), '&lt;script&gt;Adresse fictive&lt;/script&gt;')
        self.assertFalse(coordonnees.a_date([self.p], date(2025, 12, 31)).exists())
        page = self.client.get(reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk]))
        self.assertContains(page, 'Coordonnées')
        self.assertContains(page, 'data-condition-groupe')
        self.assertNotContains(page, 'Détail et historique des coordonnées')
        self.assertContains(page, 'Ville fictive')
        self.assertNotContains(page, '<script>Adresse fictive</script>')

    def test_changement_insertion_correction_valeurs_et_date(self):
        premier = self.creer()
        dernier = self.creer(date(2026, 4, 1), ville='Ville récente fictive')
        inter = coordonnees.renseigner(self.u, self.p, date(2026, 3, 1), 'Fictif', bd6.jeton(self.p),
            motif='Fait oublié fictif', **valeurs(ville='Ville intermédiaire fictive'))
        coordonnees.renseigner(self.u, self.p, date(2026, 2, 15), 'Document fictif', bd6.jeton(self.p),
            motif='Erreur de date fictive', correction=inter.pk, **valeurs(ville='Ville corrigée fictive', courriel=''))
        premier.refresh_from_db(); inter.refresh_from_db(); dernier.refresh_from_db()
        self.assertEqual(premier.fin, date(2026, 2, 15))
        self.assertEqual(inter.fin, dernier.debut)
        self.assertEqual(inter.courriel, '')
        self.assertEqual(coordonnees.a_date([self.p], date(2026, 3, 10)).get(), inter)
        journal = RevisionCoordonneesPersonnelles.objects.first()
        self.assertEqual(journal.action, 'correction')
        self.assertEqual(journal.avant[1]['ville'], 'Ville intermédiaire fictive')
        self.assertEqual(journal.apres[1]['ville'], 'Ville corrigée fictive')

    def test_etat_partage_refuse_formulaire_ouvert_avant_modification_familiale(self):
        token = bd6.jeton(self.p)
        from .tests_famille import valeurs as valeurs_famille
        famille.renseigner(self.u, self.p, date(2026, 1, 1), 'Fictif', token, **valeurs_famille())
        with self.assertRaises(ValidationError):
            coordonnees.renseigner(self.u, self.p, date(2026, 1, 1), 'Fictif', token, **valeurs())
        self.assertFalse(CoordonneesPersonnelles.objects.exists())

    def test_erreurs_source_courriel_future_cible_et_rollback(self):
        premier = self.creer()
        self.creer(date(2026, 4, 1))
        for debut, donnees in [(date(2026, 2, 1), valeurs(courriel='invalide')),
            (date(9999, 1, 1), valeurs())]:
            with self.assertRaises(ValidationError):
                coordonnees.renseigner(self.u, self.p, debut, 'Fictif', bd6.jeton(self.p), **donnees)
        with self.assertRaises(ValidationError):
            coordonnees.renseigner(self.u, self.p, date(2026, 2, 1), 'x' * 161, bd6.jeton(self.p), **valeurs())
        with self.assertRaises(ValidationError):
            coordonnees.renseigner(self.u, self.p, date(2026, 5, 1), 'Fictif', bd6.jeton(self.p),
                correction=premier.pk, motif='Fictif', **valeurs())
        with patch.object(RevisionCoordonneesPersonnelles.objects, 'create', side_effect=RuntimeError('Fictif')):
            with self.assertRaises(RuntimeError):
                self.creer(date(2026, 5, 1))
        self.assertEqual(CoordonneesPersonnelles.objects.count(), 2)
        self.assertEqual(RevisionCoordonneesPersonnelles.objects.count(), 2)

    def test_rapports_exactement_dates_filtres_csv_et_formules_neutralisees(self):
        self.creer(rue='=FORMULE()')
        self.creer(date(2026, 2, 1), ville='Autre ville fictive', pays='Autre pays fictif')
        autre = Personne.objects.create(designation='Sans coordonnées fictives', cree_par=self.u)
        url = reverse('dossiers:rapport_coordonnees')
        page = self.client.get(url, {'date': '2026-01-31', 'ville': 'ville FICTIVE', 'code_postal': '00100'})
        self.assertEqual(page.context['nombre'], 1)
        self.assertEqual(page.context['page_obj'][0]['coordonnees'].ville, 'Ville fictive')
        response = self.client.get(url, {'date': '2026-01-31', 'format': 'csv'})
        csv = response.content.decode()
        self.assertIn("'=FORMULE()", csv)
        self.assertNotIn('Autre ville', csv)
        self.assertIn(str(autre.pk), csv)
        self.assertIn('no-store', response['Cache-Control'])
        page = self.client.get(url, {'date': '2026-02-01', 'pays': 'Autre pays fictif'})
        self.assertEqual(page.context['nombre'], 1)
        self.assertEqual(page.context['page_obj'][0]['coordonnees'].ville, 'Autre ville fictive')

    def test_http_repli_sans_js_et_conservation_date_consultee_et_origine(self):
        url = reverse('dossiers:coordonnees_nouvelles', args=[self.p.pk])
        query = f'?date=2026-01-20&depuis_nature=menage&depuis_pk={self.m.pk}&depuis_prise={self.a.pk}&sejour={self.s.pk}&q=Fictif'
        page = self.client.get(url + query)
        data = dict(valeurs(), debut='2026-01-01', source='Entretien fictif', attendu=page.context['form'].initial['attendu'])
        response = self.client.post(url + query, data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('date=2026-01-20', response.url)
        page = self.client.get(response.url)
        self.assertContains(page, '20/01/2026')
        self.assertContains(page, 'Les coordonnées ont changé')
        self.assertIn('/prises/' + str(self.a.pk), page.context['retour'])
        self.assertIn('sejour=' + str(self.s.pk), page.context['retour'])

    def test_fiche_pdf_contient_coordonnees_seulement_avec_droits(self):
        self.creer()
        url = reverse('personnes:fiche_pdf', args=[self.p.pk])
        with patch('pas_communs.pdf.rendre_html', return_value=b'%PDF-fictif') as rendu:
            self.client.get(url)
        self.assertIn('00100', rendu.call_args.args[0])
        with override_settings(MODE_PWA=True), patch('pas_communs.pdf.fiche_texte', return_value=b'%PDF-fictif') as rendu:
            self.client.get(url)
        self.assertTrue(any('00100' in ligne for ligne in rendu.call_args.args[1]))
        self.u.user_permissions.remove(Permission.objects.get(codename='view_coordonneespersonnelles'))
        with patch('pas_communs.pdf.rendre_html', return_value=b'%PDF-fictif') as rendu:
            self.client.get(url)
        self.assertNotIn('00100', rendu.call_args.args[0])
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.get(reverse('dossiers:rapport_coordonnees')).status_code, 403)

    def test_droits_independants_et_anciennes_coordonnees_conservees(self):
        u = get_user_model().objects.create_user('Sans-coordonnees-fictif')
        call_command('autoriser_chrs7', u.username, stdout=StringIO())
        u = get_user_model().objects.get(pk=u.pk)
        self.assertFalse(u.has_perm('personnes.view_coordonneespersonnelles'))
        with self.assertRaises(PermissionDenied):
            coordonnees.renseigner(u, self.p, date(2026, 1, 1), 'Fictif', bd6.jeton(self.p), **valeurs())
        self.creer()
        self.creer(date(2026, 2, 1), rue='', code_postal='', ville='', pays='', telephone='', courriel='', fax='')
        self.assertEqual(coordonnees.a_date([self.p], date(2026, 1, 31)).get().code_postal, '00100')
        self.assertEqual(coordonnees.a_date([self.p], date(2026, 2, 1)).get().adresse, '')


class CoordonneesRepriseTests(Donnees, TransactionTestCase):
    def test_copie_zip_conserve_coordonnees_et_journal(self):
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
        coordonnees.renseigner(self.u, self.p, date(2026, 1, 1), 'Fictif', bd6.jeton(self.p), **valeurs())
        with TemporaryDirectory() as temporaire:
            racine = Path(temporaire)
            source = racine / 'source'; source.mkdir()
            (source / 'secret-key').write_text('cle-fictive-coordonnees')
            with closing(sqlite3.connect(source / paquets.PROFIL.base)) as copie:
                connection.connection.backup(copie)
            archive = racine / 'coordonnees.zip'
            creer_sauvegarde(source, archive, profil=paquets.PROFIL)
            preparation = paquets.verifier(archive, racine, 'preparation')
            destination = racine / 'restauree'
            paquets.installer_copie(preparation, destination)
            with closing(sqlite3.connect(destination / paquets.PROFIL.base)) as db:
                self.assertEqual(db.execute('SELECT code_postal, courriel FROM personnes_coordonneespersonnelles').fetchone(), ('00100', 'personne@example.invalid'))
                self.assertEqual(db.execute('SELECT action FROM personnes_revisioncoordonneespersonnelles').fetchone(), ('changement',))
