from datetime import date
from io import StringIO
import json
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from . import models as m, bd6, coordonnees, famille, retraits_chronologiques as r


class RetraitsChronologiquesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u = get_user_model().objects.create_superuser('retrait-fictif')
        cls.p = m.Personne.objects.create(designation='Thomas fictif', cree_par=cls.u)
        cls.m = m.Menage.objects.create(libelle='Ménage fictif', cree_par=cls.u)
        m.Appartenance.objects.create(menage=cls.m, personne=cls.p, debut=date(2026, 1, 1))
        cls.a = m.Accompagnement.objects.create(menage=cls.m, debut=date(2026, 10, 12), cree_par=cls.u)
        cls.a.beneficiaires.add(cls.p)

    def social(self, jour, valeur):
        return bd6.renseigner(self.u, self.p, 'emploi', valeur, jour, 'Entretien fictif', bd6.jeton(self.p))

    def retirer(self, code, fait, **options):
        _, x, p = r.apercu(self.u, self.p, code, fait.pk)
        return r.retirer(self.u, self.p, code, x.pk, bd6.jeton(self.p),
            r.preuve(code, self.p, x, p), confirmer=True, **options)

    def test_retablir_entre_deux_bornes_sans_detruire_les_journaux(self):
        precedent = self.social(date(2026, 9, 1), 'sans_emploi')
        changement = self.social(date(2026, 10, 10), 'emploi')
        suivant = self.social(date(2026, 10, 20), 'formation')
        self.retirer('emploi', changement)
        precedent.refresh_from_db(); suivant.refresh_from_db()
        self.assertEqual(precedent.fin, date(2026, 10, 20))
        self.assertEqual(suivant.debut, date(2026, 10, 20))
        self.assertEqual(m.SituationPersonnelle.objects.count(), 2)
        self.assertEqual(m.SituationPersonnelle.tous.count(), 3)
        retrait = m.RevisionSituationPersonnelle.objects.get(action='retrait')
        self.assertIsNotNone(retrait.situation.retire_le)
        self.assertEqual(len(retrait.avant), 3); self.assertEqual(len(retrait.apres), 2)
        self.assertEqual(bd6.etat(self.u, [self.p], date(2026, 10, 12))[0]['lignes'][1]['texte'], 'Sans emploi')
        self.assertEqual(r.prises_concernees(self.u, self.p, date(2026, 10, 10), date(2026, 10, 20))['nombre'], 1)

    def test_retirer_premier_ou_dernier_et_reutiliser_la_date(self):
        premier = self.social(date(2026, 9, 1), 'sans_emploi')
        self.retirer('emploi', premier)
        self.assertFalse(m.SituationPersonnelle.objects.exists())
        self.assertEqual(bd6.etat(self.u, [self.p], date(2026, 10, 12))[0]['lignes'][1]['texte'], 'Non renseigné')
        remplace = self.social(date(2026, 9, 1), 'emploi')
        dernier = self.social(date(2026, 10, 10), 'formation')
        self.retirer('emploi', dernier)
        remplace.refresh_from_db(); self.assertIsNone(remplace.fin)
        self.assertEqual(m.SituationPersonnelle.tous.count(), 3)

    def test_ne_pas_combler_un_trou_ni_rejouer_un_retrait(self):
        ancien = self.social(date(2026, 9, 1), 'sans_emploi')
        x = self.social(date(2026, 10, 10), 'emploi')
        m.SituationPersonnelle.objects.filter(pk=ancien.pk).update(fin=date(2026, 9, 20))
        self.retirer('emploi', x)
        ancien.refresh_from_db(); self.assertEqual(ancien.fin, date(2026, 9, 20))
        self.assertEqual(bd6.etat(self.u, [self.p], date(2026, 10, 12))[0]['lignes'][1]['texte'], 'Non renseigné')
        with self.assertRaises(ValidationError):
            self.retirer('emploi', x)

    def test_serie_multichamps_conserve_adresse_et_retrait_est_groupe(self):
        valeurs = {c: '' for c in coordonnees.CHAMPS}
        valeurs.update(ville='Bordeaux', telephone='ancien')
        ancien = coordonnees.renseigner(self.u, self.p, date(2026, 9, 1), 'Entretien', bd6.jeton(self.p), **valeurs)
        nouveau = coordonnees.renseigner(self.u, self.p, date(2026, 10, 10), 'Entretien', bd6.jeton(self.p), **{**valeurs, 'telephone': 'nouveau'})
        self.retirer('coordonnees', nouveau)
        lu = coordonnees.a_date([self.p], date(2026, 10, 12)).get()
        self.assertEqual((lu.pk, lu.ville, lu.telephone), (ancien.pk, 'Bordeaux', 'ancien'))
        self.assertEqual(m.RevisionCoordonneesPersonnelles.objects.get(action='retrait').coordonnees.pk, nouveau.pk)

    def test_toutes_les_series_de_groupe_et_identite_declaree(self):
        for code in ('famille', 'complements', 'administration'):
            with self.subTest(code=code):
                serie = r.configuration(code)
                ancien = serie.modele.objects.create(personne=self.p, debut=date(2026, 9, 1), fin=date(2026, 10, 10), source='Entretien', auteur=self.u)
                nouveau = serie.modele.objects.create(personne=self.p, debut=date(2026, 10, 10), source='Entretien', auteur=self.u)
                self.retirer(code, nouveau)
                ancien.refresh_from_db(); self.assertIsNone(ancien.fin)
                self.assertEqual(serie.modele.objects.count(), 1)
                self.assertEqual(serie.modele.tous.count(), 2)

    def test_perime_preuve_falsifiee_et_droits_rollback(self):
        x = self.social(date(2026, 9, 1), 'sans_emploi')
        _, _, precedent = r.apercu(self.u, self.p, 'emploi', x.pk)
        token = bd6.jeton(self.p)
        preuve = r.preuve('emploi', self.p, x, precedent)
        self.social(date(2026, 10, 10), 'emploi')
        with self.assertRaises(ValidationError):
            r.retirer(self.u, self.p, 'emploi', x.pk, token, preuve, True)
        with self.assertRaises(ValidationError):
            r.retirer(self.u, self.p, 'emploi', x.pk, bd6.jeton(self.p), 'faux', True)
        self.assertEqual(m.SituationPersonnelle.objects.count(), 2)
        lecteur = get_user_model().objects.create_user('lecteur-retrait-fictif')
        with self.assertRaises(PermissionDenied):
            r.apercu(lecteur, self.p, 'emploi', x.pk)
        self.assertIsNone(r.prises_concernees(lecteur, self.p, date(2026, 1, 1), None))

    def test_http_confirmation_et_export_integral(self):
        x = self.social(date(2026, 9, 1), 'sans_emploi')
        self.client.force_login(self.u)
        url = reverse('dossiers:condition_retirer', args=[self.p.pk, 'emploi', x.pk])
        page = self.client.get(url, HTTP_X_CONDITION_FORM='1')
        self.assertContains(page, 'Non renseigné : aucun état antérieur continu.')
        data = page.context['form'].initial
        refus = self.client.post(url, data, HTTP_X_CONDITION_FORM='1')
        self.assertContains(refus, 'Ce champ est obligatoire.')
        data = {**data, 'confirmer': 'on', 'motif': 'Entretien du 12 octobre'}
        ok = self.client.post(url, data, HTTP_X_CONDITION_FORM='1')
        self.assertEqual(ok.json(), {'enregistre': True})
        sortie = StringIO(); call_command('dumpdata', 'personnes.SituationPersonnelle', '--all', stdout=sortie)
        self.assertEqual(len(json.loads(sortie.getvalue())), 1)
        self.assertIsNotNone(json.loads(sortie.getvalue())[0]['fields']['retire_le'])

    def test_retour_schema_refuse_la_resurrection_implicite(self):
        from importlib import import_module
        from types import SimpleNamespace
        from django.apps import apps
        from django.db import connection
        from django.db.migrations.exceptions import IrreversibleError
        migration = import_module('personnes.migrations.0040_retraits_chronologies_personnelles')
        migration.verifier_retour(apps, SimpleNamespace(connection=connection))
        x = self.social(date(2026, 9, 1), 'sans_emploi')
        self.retirer('emploi', x)
        with self.assertRaises(IrreversibleError):
            migration.verifier_retour(apps, SimpleNamespace(connection=connection))

    def test_correction_sur_place_exige_confirmation_et_recalcule_la_portee(self):
        x = m.CoordonneesPersonnelles.objects.create(personne=self.p, debut=date(2026, 9, 1), ville='Bordeaux', source='Entretien', auteur=self.u)
        self.client.force_login(self.u)
        url = reverse('dossiers:coordonnees_corriger', args=[self.p.pk, x.pk]) + '?portee=1'
        page = self.client.get(url, HTTP_X_CONDITION_FORM='1')
        self.assertContains(page, 'Portée de la correction')
        initial = page.context['form'].initial
        data = {'attendu': initial['attendu'], 'debut': '2026-09-01', 'ville': 'Ville corrigée', 'source': 'Entretien', 'motif': 'Erreur',
            'condition_preuve': page.context['form']['condition_preuve'].value()}
        self.client.post(url, data, HTTP_X_CONDITION_FORM='1')
        x.refresh_from_db(); self.assertEqual(x.ville, 'Bordeaux')
        data.update(condition_confirmation='on', debut='2026-08-20')
        rep = self.client.post(url, data, HTTP_X_CONDITION_FORM='1')
        self.assertContains(rep, 'La période concernée a changé')
        x.refresh_from_db(); self.assertEqual(x.ville, 'Bordeaux')
        data['condition_preuve'] = rep.context['form']['condition_preuve'].value()
        rep = self.client.post(url, data, HTTP_X_CONDITION_FORM='1')
        self.assertEqual(rep.json(), {'enregistre': True})
        x.refresh_from_db(); self.assertEqual((x.ville, x.debut), ('Ville corrigée', date(2026, 8, 20)))


class RetraitsCopiesEtConcurrence(TransactionTestCase):
    def preparer(self):
        u = get_user_model().objects.create_superuser('copie-retrait-fictive')
        p = m.Personne.objects.create(designation='Personne fictive', cree_par=u)
        precedent = bd6.renseigner(u, p, 'emploi', 'sans_emploi', date(2026, 9, 1), 'Entretien', bd6.jeton(p))
        x = bd6.renseigner(u, p, 'emploi', 'emploi', date(2026, 10, 10), 'Entretien', bd6.jeton(p))
        return u, p, precedent, x

    def test_copie_restauree_conserve_retrait_journaux_et_lecture_active(self):
        import os, sqlite3, subprocess, sys
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from contextlib import closing
        from django.db import connection
        from pas_communs.paquets import creer_sauvegarde
        from pas_a_pas_accompagnement import paquets
        from django.conf import settings
        if connection.vendor != 'sqlite':
            self.skipTest('Copie locale SQLite.')
        u, p, precedent, x = self.preparer()
        r.retirer(u, p, 'emploi', x.pk, bd6.jeton(p), r.preuve('emploi', p, x, precedent), True)
        m.RevisionSituationPersonnelle.objects.filter(action='retrait').update(contexte_saisie='Entretien fictif conservé')
        with TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'source'; source.mkdir()
            (source / 'secret-key').write_text('cle-fictive-copie-retrait')
            with closing(sqlite3.connect(source / paquets.PROFIL.base)) as db:
                connection.connection.backup(db)
            archive = root / 'retrait.zip'; creer_sauvegarde(source, archive, profil=paquets.PROFIL)
            prep = paquets.verifier(archive, root, 'preparation')
            destination = root / 'restauree'; paquets.installer_copie(prep, destination)
            code = '''import os,json
os.environ['DJANGO_SETTINGS_MODULE']='pas_a_pas_accompagnement.settings'
import django;django.setup()
from personnes import models as m,bd6
from django.contrib.auth import get_user_model
from datetime import date
p=m.Personne.objects.get();u=get_user_model().objects.get(username='copie-retrait-fictive')
print(json.dumps([m.SituationPersonnelle.objects.count(),m.SituationPersonnelle.tous.count(),m.RevisionSituationPersonnelle.objects.filter(action='retrait').count(),bd6.etat(u,[p],date(2026,10,12))[0]['lignes'][1]['texte'], m.RevisionSituationPersonnelle.objects.get(action='retrait').contexte_saisie]))
'''
            sortie = subprocess.run([sys.executable, '-c', code], cwd=settings.BASE_DIR,
                env={**os.environ, 'ACCOMPAGNEMENT_DONNEES': str(destination)}, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(sortie.stdout), [1, 2, 1, 'Sans emploi', 'Entretien fictif conservé'])

    def test_deux_retraits_concurrents_un_seul_journal_etat_retabli(self):
        from threading import Barrier, Thread
        from django.db import close_old_connections, OperationalError, connection
        if connection.vendor != 'sqlite':
            self.skipTest('Recette de concurrence SQLite.')
        u, p, precedent, x = self.preparer()
        token = bd6.jeton(p); preuve = r.preuve('emploi', p, x, precedent)
        u.get_all_permissions()
        barriere = Barrier(2); resultats = []; erreurs = []
        def travail():
            close_old_connections()
            try:
                personne = m.Personne.objects.get(pk=p.pk)
                barriere.wait(timeout=10)
                r.retirer(u, personne, 'emploi', x.pk, token, preuve, True)
                resultats.append(True)
            except (ValidationError, OperationalError):
                resultats.append(False)
            except Exception as erreur:
                erreurs.append(str(erreur))
            finally:
                close_old_connections()
        threads = [Thread(target=travail) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=20)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertFalse(erreurs, erreurs); self.assertEqual(sum(resultats), 1, resultats)
        self.assertEqual(m.RevisionSituationPersonnelle.objects.filter(action='retrait').count(), 1)
        self.assertEqual(m.SituationPersonnelle.objects.get().valeur, 'sans_emploi')
