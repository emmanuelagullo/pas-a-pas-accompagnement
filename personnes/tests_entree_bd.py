"""BD4 : entrée, synthèse multi-période et vrais retours d'opération."""
from datetime import date
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import signing
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .tests_hebergement import Donnees
from .models import Personne, Menage, Accompagnement, AccordRepas, Appartenance, EvenementSuivi
from . import suivi, hebergement, repas, corrections, dossier


class EntreeBDTests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        call_command('autoriser_bd3', self.u.username, stdout=StringIO())
        self.u.user_permissions.add(Permission.objects.get(codename='add_personne', content_type__app_label='personnes'))
        self.u = get_user_model().objects.get(pk=self.u.pk)
        self.client.force_login(self.u)
        self.url = reverse('dossiers:detail', args=['menage', self.m.pk])
        self.purl = reverse('dossiers:detail', args=['personne', self.p.pk])

    def test_accueil_recherche_menages_par_tous_membres_et_anciennes_appartenances(self):
        enfant = Personne.objects.create(designation='Benali', prenom='Inès', cree_par=self.u)
        suivi.ajouter_appartenance(self.u, self.m, enfant, date(2025, 1, 1), date(2025, 2, 1))
        autre = suivi.creer_menage(self.u, 'Sans correspondance', [self.p], date(2026, 1, 1))
        for fragment in ('', '1'):
            page = self.client.get(reverse('accueil'), {'q': 'Inès Benali', 'fragment': fragment})
            self.assertContains(page, self.m.libelle)
            self.assertNotContains(page, autre.libelle)
            self.assertContains(page, '1 février 2025')
            self.assertIn('no-store', page['Cache-Control'])
        page = self.client.get(reverse('accueil'), {'mode': 'personne', 'q': 'Inès'})
        self.assertContains(page, reverse('dossiers:detail', args=['personne', enfant.pk]))
        self.assertContains(self.client.get(reverse('accueil')), 'Quel dossier souhaitez-vous ouvrir')

    def test_recherche_plusieurs_membres_aucun_doublon_et_pagination(self):
        p2 = Personne.objects.create(designation='Deuxième', prenom='Camille', cree_par=self.u)
        suivi.ajouter_appartenance(self.u, self.m, p2, date(2026, 1, 1))
        page = self.client.get(reverse('accueil'), {'q': 'Personne Camille'})
        self.assertEqual(page.context['page_obj'].paginator.count, 1)
        for n in range(27):
            Menage.objects.create(libelle=f'Page fictive {n:02}', cree_par=self.u)
        page = self.client.get(reverse('accueil'), {'q': 'Page fictive', 'page': '2'})
        self.assertEqual(len(page.context['page_obj']), 2)
        self.assertContains(page, 'page=2')

    def test_personne_seule_sans_menage_et_sans_suivi(self):
        p = Personne.objects.create(designation='Sans suivi', cree_par=self.u)
        page = self.client.get(reverse('dossiers:detail', args=['personne', p.pk]))
        self.assertContains(page, 'Dossier — Sans suivi')
        self.assertContains(page, 'Aucune période consultable')
        self.assertEqual(list(page.context['sejours_dossier']), [])
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_synthese_toutes_periodes_et_filtrage_beneficiaires(self):
        p2 = Personne.objects.create(designation='Autre bénéficiaire', cree_par=self.u)
        suivi.ajouter_appartenance(self.u, self.m, p2, date(2026, 1, 1))
        a2 = suivi.ouvrir(self.u, self.m, [self.p, p2], date(2025, 1, 1))
        r1 = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), None, 'diner')
        r2 = repas.accorder(self.u, a2, [p2], date(2025, 1, 1), None, 'dejeuner')
        page = self.client.get(self.url)
        self.assertEqual({a.pk for a in page.context['periodes']}, {self.a.pk, a2.pk})
        self.assertEqual({r.pk for r in page.context['accords_repas']}, {r1.pk, r2.pk})
        self.assertEqual([r.pk for r in self.client.get(self.purl).context['accords_repas']], [r1.pk])
        m2 = suivi.creer_menage(self.u, 'Autre ménage', [self.p], date(2026, 1, 1))
        a3 = suivi.ouvrir(self.u, m2, [self.p], date(2026, 1, 1))
        r3 = repas.accorder(self.u, a3, [self.p], date(2026, 1, 1), None, 'diner')
        self.assertNotIn(r3.pk, [r.pk for r in self.client.get(self.url).context['accords_repas']])
        self.assertIn(r3.pk, [r.pk for r in self.client.get(self.purl).context['accords_repas']])

    def test_bascule_preserve_recherche_et_selection_et_retour_origine(self):
        page = self.client.get(self.url, {'q': 'Personne', 'mode': 'menage', 'page': '2'})
        lien = list(page.context['liens_uniques'])[0].url
        page = self.client.get(lien)
        self.assertEqual(page.context['origine'].pk, self.m.pk)
        retour = self.client.get(page.context['origine_url'])
        self.assertEqual(retour.context['selection_sejour'].pk, self.s.pk)
        self.assertIn('q=Personne', retour.context['retour'])
        self.assertIn('page=2', retour.context['retour'])
        page = self.client.get(self.purl, {'origine_menage': 'incorrect'})
        self.assertIsNone(page.context['origine'])

    def test_operation_retour_personne_et_collectif_explicite(self):
        page = self.client.get(self.purl, {'q': 'Personne', 'origine_menage': self.m.pk})
        nav = page.context['navigation_h']
        url = reverse('suivi:sortir', args=[self.s.pk])
        form = self.client.get(url, {'contexte_dossier': nav['contexte_dossier']})
        self.assertContains(form, self.p.designation)
        self.assertRedirects(self.client.post(url, {'contexte_dossier': nav['contexte_dossier'], 'fin': '2026-01-20'}), nav['retour_dossier'])
        retour = self.client.get(nav['retour_dossier'])
        self.assertEqual(retour.context['nature'], 'personne')
        self.assertEqual(retour.context['selection_sejour'].pk, self.s.pk)
        self.assertEqual(retour.context['origine'].pk, self.m.pk)
        self.assertIn('q=Personne', retour.context['retour'])

    def test_retour_correction_mauvais_parent_et_jeton_falsifie(self):
        page = self.client.get(self.url)
        nav = page.context['navigation_h']
        url = reverse('suivi:corriger_saisie', args=['sejour', self.s.pk])
        data = {'contexte_dossier': nav['contexte_dossier'], 'debut': '2026-01-04', 'fin': '', 'motif': 'Correction fictive', 'attendu': corrections.jeton(self.s)}
        self.assertRedirects(self.client.post(url, data), nav['retour_dossier'])
        values = signing.loads(nav['contexte_dossier'], salt=dossier.SEL)
        values['vue']['pk'] = str(Personne.objects.create(designation='Étranger', cree_par=self.u).pk)
        values['vue']['nature'] = 'personne'
        bad = signing.dumps(values, salt=dossier.SEL)
        page = self.client.get(url, {'contexte_dossier': bad})
        self.assertNotContains(page, reverse('dossiers:detail', args=['personne', values['vue']['pk']]))
        page = self.client.get(url, {'contexte_dossier': 'faux'})
        self.assertNotContains(page, 'Annuler et revenir au dossier')

    def test_boites_signent_chacune_le_vrai_parent(self):
        a2 = suivi.ouvrir(self.u, self.m, [self.p], date(2025, 1, 1))
        r = repas.accorder(self.u, a2, [self.p], date(2025, 1, 1), None, 'diner')
        page = self.client.get(self.url)
        for key, a in [('navigation_h', self.a), ('navigation_r', a2)]:
            values = signing.loads(page.context[key]['contexte_dossier'], salt=dossier.SEL)
            self.assertEqual(values['accompagnement'], str(a.pk))
        nav = page.context['navigation_r']
        url = reverse('suivi:accord_repas', args=[r.pk])
        self.assertContains(self.client.get(url, {'contexte_dossier': nav['contexte_dossier']}), nav['retour_dossier'])

    def test_passage_ancienne_fiche_conserve_retour_synthese(self):
        page = self.client.get(self.purl)
        nav = page.context['navigation_h']
        page = self.client.get(reverse('suivi:accompagnement', args=[self.a.pk]), {'contexte_dossier': nav['contexte_dossier']})
        self.assertIn(self.purl, page.context['retour_dossier'])
        values = signing.loads(page.context['contexte_dossier'], salt=dossier.SEL)
        self.assertEqual(values['vue']['nature'], 'personne')

    def test_choix_periode_pas_de_creation_implicite(self):
        url = reverse('dossiers:choisir', args=['menage', self.m.pk, 'repas'])
        page = self.client.get(url)
        self.assertContains(page, 'Choisir la période')
        self.assertEqual(Accompagnement.objects.count(), 1)
        self.assertEqual(AccordRepas.objects.count(), 0)
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(self.client.get(reverse('dossiers:choisir', args=['menage', self.m.pk, 'invalide'])).status_code, 404)

    def test_creation_personne_sans_menage_ni_suivi(self):
        url = reverse('dossiers:creer', args=['personne'])
        self.assertContains(self.client.get(url, {'q': 'Nom fictif'}), 'value="Nom fictif"')
        page = self.client.post(url+'?q=Nom&mode=personne', {'designation': 'Nom fictif', 'prenom': 'Alex'})
        p = Personne.objects.get(designation='Nom fictif')
        self.assertEqual(page.status_code, 302)
        self.assertIn(reverse('dossiers:detail', args=['personne', p.pk]), page.url)
        self.assertEqual(Menage.objects.count(), 1)
        self.assertEqual(Accompagnement.objects.count(), 1)
        self.assertEqual(self.client.get(page.url).status_code, 200)

    def test_creation_menage_personne_existante_et_nouvelle(self):
        url = reverse('dossiers:creer', args=['menage'])
        for choix in ('existante', 'nouvelle'):
            page = self.client.post(url, {'libelle': 'Nouveau '+choix, 'premiere_personne': choix,
                'personne': self.p.pk, 'designation': 'Nouvelle identité', 'prenom': 'Morgan', 'debut': '2026-01-01'})
            self.assertEqual(page.status_code, 302)
            m = Menage.objects.get(libelle='Nouveau '+choix)
            self.assertEqual(m.appartenances.count(), 1)
            self.assertEqual(m.accompagnements.count(), 0)
            self.assertEqual(EvenementSuivi.objects.filter(menage=m).count(), 2)
            self.assertEqual(self.client.get(page.url).status_code, 200)
        self.assertEqual(Personne.objects.filter(designation='Nouvelle identité').count(), 1)

    def test_creation_invalide_et_rollback(self):
        url = reverse('dossiers:creer', args=['menage'])
        data = {'libelle': 'Invalide', 'premiere_personne': 'nouvelle', 'designation': '   ', 'debut': '2026-01-01'}
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertFalse(Menage.objects.filter(libelle='Invalide').exists())
        data['designation'] = 'Rollback fictif'
        with patch('personnes.vues_dossiers.suivi.creer_menage', side_effect=RuntimeError('Échec fictif')):
            with self.assertRaises(RuntimeError):
                self.client.post(url, data)
        self.assertFalse(Personne.objects.filter(designation='Rollback fictif').exists())

    def test_droits_lecture_partielle_et_refus_ecriture(self):
        self.u.user_permissions.clear()
        self.u.user_permissions.add(Permission.objects.get(codename='view_personne', content_type__app_label='personnes'))
        page = self.client.get(reverse('accueil'), {'mode': 'menage', 'fragment': '1'})
        self.assertEqual(page.context['mode'], 'personne')
        self.assertNotContains(page, self.m.libelle)
        page = self.client.get(self.purl)
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, self.m.libelle)
        self.assertNotContains(page, 'Chambre fictive')
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.get(reverse('dossiers:creer', args=['personne'])).status_code, 403)
        self.assertEqual(self.client.post(reverse('dossiers:creer', args=['menage']), {}).status_code, 403)
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(self.purl).status_code, 403)
        self.assertNotContains(self.client.get(reverse('accueil'), {'fragment': '1'}), self.p.designation)

    def test_origine_arbitraire_ignoree_et_selection_etrangere_bornee(self):
        p = Personne.objects.create(designation='Autre', cree_par=self.u)
        m = suivi.creer_menage(self.u, 'Étranger', [p], date(2026, 1, 1))
        a = suivi.ouvrir(self.u, m, [p], date(2026, 1, 1))
        r = repas.accorder(self.u, a, [p], date(2026, 1, 1), None, 'diner')
        page = self.client.get(self.purl, {'origine_menage': m.pk, 'repas': r.pk})
        self.assertIsNone(page.context['origine'])
        self.assertIsNone(page.context['selection_repas'])
        self.assertNotContains(page, 'Étranger')

    def test_requetes_ne_croissent_pas_par_sejour_ni_periode(self):
        def nombre():
            with CaptureQueriesContext(connection) as queries:
                self.client.get(self.url)
            return len(queries)
        avant = nombre()
        for n in range(6):
            a = suivi.ouvrir(self.u, self.m, [self.p], date(2025, 1, n+1))
            accord = hebergement.accorder(self.u, a, [self.p], date(2025, 1, n+1), None)
            # Lecture multi-période, sans créer de séjours chevauchants.
        self.assertLessEqual(nombre(), avant + 2)

    def test_retour_menage_retrouve_selection_qui_ne_concerne_pas_personne(self):
        enfant = Personne.objects.create(designation='Enfant fictif', cree_par=self.u)
        suivi.ajouter_appartenance(self.u, self.m, enfant, date(2026, 1, 1))
        a = suivi.ouvrir(self.u, self.m, [enfant], date(2026, 1, 1))
        r = repas.accorder(self.u, a, [enfant], date(2026, 1, 1), None, 'diner')
        page = self.client.get(self.url, {'repas': r.pk})
        lien = next(l.url for l in page.context['liens_uniques'] if l.personne_id == self.p.pk)
        personnelle = self.client.get(lien)
        self.assertIsNone(personnelle.context['selection_repas'])
        retour = self.client.get(personnelle.context['origine_url'])
        self.assertEqual(retour.context['selection_repas'].pk, r.pk)

    def test_csrf_et_absence_de_creation_par_get(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.u)
        avant = Personne.objects.count()
        url = reverse('dossiers:creer', args=['personne'])
        client.get(url, {'q': 'Simple saisie'})
        self.assertEqual(Personne.objects.count(), avant)
        self.assertEqual(client.post(url, {'designation': 'Interdit'}).status_code, 403)
        self.assertEqual(Personne.objects.count(), avant)

    def test_notes_personne_et_correction_identite_retrouvent_dossier(self):
        from . import identite
        self.u.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes', codename__in=[
            'view_notepartagee', 'add_notepartagee', 'change_personne', 'view_revisionidentite']))
        page = self.client.get(self.purl, {'q': 'Fictive', 'origine_menage': self.m.pk})
        nav = page.context['navigation_personne']
        self.assertRedirects(self.client.post(reverse('suivi:notes', args=['personne', self.p.pk]),
            {'contexte_dossier': nav['contexte_dossier'], 'contenu': 'Note fictive BD4'}), nav['retour_dossier'])
        url = reverse('personnes:corriger_identite', args=[self.p.pk])
        self.assertRedirects(self.client.post(url, {'contexte_dossier': nav['contexte_dossier'],
            'designation': self.p.designation, 'prenom': 'Alex', 'motif': 'Précision fictive', 'attendu': identite.jeton(self.p)}), nav['retour_dossier'])
        p2 = Personne.objects.create(designation='Autre personne', cree_par=self.u)
        page = self.client.get(reverse('personnes:corriger_identite', args=[p2.pk]), {'contexte_dossier': nav['contexte_dossier']})
        self.assertNotContains(page, nav['retour_dossier'])

    def test_erreur_creation_personne_nommee_et_sans_erreur_globale(self):
        url = reverse('dossiers:creer', args=['menage'])
        data = {'libelle': 'Groupe fictif', 'premiere_personne': 'nouvelle', 'designation': '', 'debut': '2026-01-01'}
        page = self.client.post(url, data)
        self.assertFormError(page.context['form'], 'designation', 'Indiquez le nom ou la désignation de la nouvelle personne.')
        self.assertEqual(page.context['form'].non_field_errors(), [])
        self.assertContains(page, 'href="#id_designation"')
        self.assertContains(page, 'Nom ou désignation de la nouvelle personne :')
        self.assertContains(page, 'aria-invalid="true"')
        self.assertFalse(Menage.objects.filter(libelle='Groupe fictif').exists())
        data['designation'] = 'Nom fictif'
        data['personne'] = 'ancienne-selection-invalide'
        page = self.client.post(url, data)
        self.assertEqual(page.status_code, 302)
        self.assertEqual(Menage.objects.get(libelle='Groupe fictif').appartenances.get().personne.designation, 'Nom fictif')

    def test_erreur_personne_existante_et_aides_accessibles_sans_javascript(self):
        page = self.client.post(reverse('dossiers:creer', args=['menage']), {
            'libelle': 'Groupe fictif', 'premiere_personne': 'existante', 'debut': '2026-01-01'})
        self.assertFormError(page.context['form'], 'personne', 'Choisissez la personne à rattacher.')
        self.assertContains(page, 'href="#id_personne"')
        self.assertContains(page, 'Personne existante :')
        self.assertContains(page, 'aucune prestation ni période de suivi')
        page = self.client.get(reverse('accueil'))
        self.assertContains(page, 'aria-describedby="aide-recherche"')
        self.assertContains(page, 'Aide à la recherche et à la création')
        page = self.client.get(self.url)
        self.assertContains(page, 'Comprendre les actions d’hébergement')
        self.assertContains(page, 'tous concernés')
