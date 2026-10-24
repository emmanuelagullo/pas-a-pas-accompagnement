from datetime import date
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from . import bd6, contacts_menage
from .models import Personne, ContactMenage, RevisionContactMenage
from .tests_hebergement import Donnees


class ContactTests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_solenne', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        self.client.force_login(self.u)
        self.autre = Personne.objects.create(designation='Contact extérieur fictif', cree_par=self.u)
        self.url = reverse('dossiers:contact_menage', args=[self.m.pk])

    def designer(self, personne=None, debut=date(2026, 1, 1), **kwargs):
        return contacts_menage.designer(self.u, self.m, personne, debut,
            'Choix exprimé en entretien fictif', bd6.jeton(self.m), **kwargs)

    def test_contact_exterieur_et_retrait_sans_appartenance_ni_beneficiaires_implicites(self):
        fait = self.designer(self.autre)
        self.assertEqual(self.m.appartenances.count(), 1)
        self.assertEqual(list(self.a.beneficiaires.all()), [self.p])
        self.assertEqual(contacts_menage.a_date([self.m], date(2026, 1, 2)).get(), fait)
        self.designer(None, date(2026, 2, 1))
        self.assertIsNone(contacts_menage.a_date([self.m], date(2026, 2, 1)).get().contact)
        self.assertEqual(contacts_menage.a_date([self.m], date(2026, 1, 31)).get().contact, self.autre)
        self.assertEqual(RevisionContactMenage.objects.first().avant[0]['contact']['id'], str(self.autre.pk))

    def test_correction_personne_date_et_insertion_motivees(self):
        premier = self.designer(self.p)
        self.designer(None, date(2026, 4, 1))
        with self.assertRaises(ValidationError):
            self.designer(self.autre, date(2026, 3, 1))
        inter = self.designer(self.autre, date(2026, 3, 1), motif='Désignation oubliée fictive')
        self.designer(self.p, date(2026, 2, 15), correction=inter.pk, motif='Personne et date erronées fictives')
        premier.refresh_from_db(); inter.refresh_from_db()
        self.assertEqual(premier.fin, date(2026, 2, 15))
        self.assertEqual(inter.fin, date(2026, 4, 1))
        self.assertEqual(inter.contact, self.p)
        self.assertEqual(RevisionContactMenage.objects.first().action, 'correction')

    def test_etat_perime_rollback_et_traversee_refuses(self):
        token = bd6.jeton(self.m)
        premier = self.designer(self.p)
        with self.assertRaises(ValidationError):
            contacts_menage.designer(self.u, self.m, self.autre, date(2026, 2, 1), 'Fictif', token)
        self.designer(None, date(2026, 3, 1))
        with self.assertRaises(ValidationError):
            self.designer(self.autre, date(2026, 4, 1), correction=premier.pk, motif='Fictif')
        with patch.object(RevisionContactMenage.objects, 'create', side_effect=RuntimeError('Échec fictif')):
            with self.assertRaises(RuntimeError):
                self.designer(self.autre, date(2026, 4, 1))
        self.assertEqual(ContactMenage.objects.count(), 2)
        self.assertEqual(RevisionContactMenage.objects.count(), 2)

    def test_recherche_confirmation_http_et_retour_dossier_conserve(self):
        url = reverse('dossiers:contact_nouveau', args=[self.m.pk])
        params = f'?q=Origine&mode=menage&page=2&sejour={self.s.pk}&date=2026-01-15'
        page = self.client.get(url + params + '&recherche_contact=extérieur&choisir=1')
        self.assertContains(page, 'Contact extérieur fictif')
        choix = page.context['page_obj'][0].url_choix
        form = self.client.get(choix).context['form']
        response = self.client.post(choix, {'contact': self.autre.pk, 'debut': '2026-01-01',
            'source': 'Choix fictif', 'attendu': form.initial['attendu']})
        self.assertEqual(response.status_code, 302)
        self.assertIn('date=2026-01-15', response.url)
        page = self.client.get(response.url)
        self.assertIn('q=Origine', page.context['retour'])
        self.assertIn('sejour=' + str(self.s.pk), page.context['retour'])
        self.assertEqual(page.context['designation'].contact, self.autre)

    def test_post_mauvais_contact_ou_retrait_non_choisi_refuse(self):
        url = reverse('dossiers:contact_nouveau', args=[self.m.pk])
        page = self.client.get(url + '?personne=' + str(self.p.pk))
        data = {'contact': self.autre.pk, 'debut': '2026-01-01', 'source': 'Fictif', 'attendu': page.context['form'].initial['attendu']}
        self.assertEqual(self.client.post(url + '?personne=' + str(self.p.pk), data).status_code, 200)
        data['contact'] = ''
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertFalse(ContactMenage.objects.exists())
        self.assertEqual(self.client.get(url + '?personne=invalide').status_code, 404)

    def test_correction_mauvais_menage_csrf_et_droits(self):
        fait = self.designer(self.autre)
        from . import suivi
        autre = suivi.creer_menage(self.u, 'Autre ménage fictif', [self.p], date(2026, 1, 1))
        self.assertEqual(self.client.get(reverse('dossiers:contact_corriger', args=[autre.pk, fait.pk])).status_code, 404)
        protege = Client(enforce_csrf_checks=True); protege.force_login(self.u)
        self.assertEqual(protege.post(self.url, {}).status_code, 403)
        self.u.user_permissions.remove(Permission.objects.get(codename='view_contactmenage'))
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertNotContains(self.client.get(reverse('dossiers:detail', args=['menage', self.m.pk])), 'Contact extérieur fictif')

    def test_restitution_bd_resume_et_export_a_date(self):
        self.designer(self.p)
        self.designer(self.autre, date(2026, 2, 1))
        page = self.client.get(reverse('dossiers:detail', args=['menage', self.m.pk]))
        self.assertContains(page, 'Contact extérieur fictif')
        page = self.client.get(reverse('suivi:resume', args=[self.a.pk]))
        self.assertContains(page, 'Contact du ménage à l’entrée : Personne fictive')
        self.assertNotContains(page, 'Contact extérieur fictif')
        response = self.client.get(self.url, {'date': '2026-01-15', 'format': 'csv'})
        self.assertIn('Personne fictive', response.content.decode())
        self.assertNotIn('Contact extérieur', response.content.decode())
        self.assertIn('no-store', response['Cache-Control'])


class ContactConcurrenceTests(Donnees, TransactionTestCase):
    def test_copie_restauree_conserve_retrait_et_identites_du_journal(self):
        import sqlite3
        import json
        from contextlib import closing
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.db import connection
        from pas_communs.paquets import creer_sauvegarde
        from pas_a_pas_accompagnement import paquets
        if connection.vendor != 'sqlite':
            self.skipTest('Copie locale SQLite uniquement.')
        self.preparer()
        call_command('autoriser_solenne', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        contacts_menage.designer(self.u, self.m, self.p, date(2026, 1, 1), 'Choix fictif', bd6.jeton(self.m))
        contacts_menage.designer(self.u, self.m, None, date(2026, 2, 1), 'Retrait fictif', bd6.jeton(self.m))
        with TemporaryDirectory() as temporaire:
            racine = Path(temporaire); source = racine/'source'; source.mkdir()
            (source/'secret-key').write_text('cle-fictive-contact')
            with closing(sqlite3.connect(source/paquets.PROFIL.base)) as copie:
                connection.connection.backup(copie)
            archive = racine/'contact.zip'
            creer_sauvegarde(source, archive, profil=paquets.PROFIL)
            preparation = paquets.verifier(archive, racine, 'preparation')
            destination = racine/'restauree'; paquets.installer_copie(preparation, destination)
            with closing(sqlite3.connect(destination/paquets.PROFIL.base)) as db:
                self.assertEqual(db.execute('SELECT contact_id FROM personnes_contactmenage ORDER BY debut').fetchall(), [(self.p.pk.hex,), (None,)])
                apres = json.loads(db.execute('SELECT apres FROM personnes_revisioncontactmenage ORDER BY id LIMIT 1').fetchone()[0])
                self.assertEqual(apres[0]['contact']['id'], str(self.p.pk))
                self.assertEqual(apres[0]['contact']['libelle'], str(self.p))

    def test_deux_contacts_concurrents_un_seul_enregistrement(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections, OperationalError
        self.preparer()
        call_command('autoriser_solenne', self.u.username, stdout=StringIO())
        token = bd6.jeton(self.m)
        depart = Barrier(2)
        def ecrire(_):
            close_old_connections()
            try:
                u = get_user_model().objects.get(pk=self.u.pk); u.get_all_permissions()
                from .models import Menage
                m = Menage.objects.get(pk=self.m.pk)
                p = Personne.objects.get(pk=self.p.pk)
                depart.wait(timeout=10)
                try:
                    contacts_menage.designer(u, m, p, date(2026, 1, 1), 'Fictif', token)
                    return True
                except (ValidationError, OperationalError):
                    return False
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultats = list(pool.map(ecrire, range(2)))
        self.assertEqual(sum(resultats), 1, resultats)
        self.assertEqual(ContactMenage.objects.count(), 1)
        self.assertEqual(RevisionContactMenage.objects.count(), 1)
