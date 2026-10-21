"""BD1–BD2 : listes, droits et retours des vraies écritures métier."""
from datetime import date
from io import StringIO
from urllib.parse import urlencode
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from .tests_hebergement import Donnees
from .models import NotePartagee, CorrectionPeriode, RepasDistribue, OperationHebergement
from . import repas, suivi, hebergement as h, corrections


class DossierTests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        self.u.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes',
            codename__in=['view_notepartagee', 'add_notepartagee', 'change_notepartagee']))
        self.u = type(self.u).objects.get(pk=self.u.pk)
        self.client.force_login(self.u)
        self.r = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), date(2026, 3, 1), 'dejeuner')
        self.url = reverse('suivi:accompagnement', args=[self.a.pk])

    def selection(self, **choix):
        page = self.client.get(self.url, choix)
        self.assertEqual(page.status_code, 200)
        return {'contexte_dossier': page.context['contexte_dossier']}, page.context['retour_dossier']

    def test_tous_sejours_et_repas_termines_avec_accord_seul(self):
        h.sortir(self.u, self.s, date(2026, 1, 10))
        ouvert = h.admettre(self.u, self.accord, [self.p], date(2026, 1, 12))
        seul = h.accorder(self.u, self.a, [self.p], date(2026, 4, 1), None)
        autre = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), date(2026, 1, 5), 'diner')
        page = self.client.get(self.url)
        self.assertEqual([s.pk for s in page.context['sejours_dossier']], [ouvert.pk, self.s.pk])
        self.assertEqual({r.pk for r in page.context['accords_repas']}, {self.r.pk, autre.pk})
        self.assertEqual([a.pk for a in page.context['accords_sans_sejour']], [seul.pk])
        page = self.client.get(self.url, {'sejour': self.s.pk})
        self.assertNotContains(page, reverse('suivi:sortir', args=[self.s.pk]))
        self.assertNotContains(page, 'Supprimer')
        self.assertNotContains(page, 'Prolonger')

    def test_annulation_et_selection_double_conservee(self):
        h.sortir(self.u, self.s, date(2026, 1, 10))
        h.admettre(self.u, self.accord, [self.p], date(2026, 1, 12))
        token, retour = self.selection(sejour=self.s.pk, repas=self.r.pk)
        form = self.client.get(reverse('suivi:corriger_saisie', args=['sejour', self.s.pk]), token)
        self.assertContains(form, retour.replace('&', '&amp;'))
        self.assertContains(form, 'Annuler et revenir')
        page = self.client.get(retour)
        self.assertEqual(page.context['selection_sejour'].pk, self.s.pk)
        self.assertEqual(page.context['selection_repas'].pk, self.r.pk)

    def test_correction_et_jeton_perime_conservent_retour(self):
        token, retour = self.selection()
        url = reverse('suivi:corriger_saisie', args=['sejour', self.s.pk])
        valeurs = {**token, 'debut': '2026-01-04', 'fin': '', 'motif': 'Date fictive rectifiée', 'attendu': corrections.jeton(self.s)}
        self.assertRedirects(self.client.post(url, valeurs), retour)
        self.assertEqual(CorrectionPeriode.objects.filter(nature='sejour').count(), 1)
        page = self.client.post(url, valeurs)
        self.assertContains(page, 'Annuler et revenir')
        self.assertContains(page, retour.replace('&', '&amp;'))
        self.assertEqual(CorrectionPeriode.objects.filter(nature='sejour').count(), 1)

    def test_sortie_retrouve_ligne_close_preserve_accord_et_suivi(self):
        token, retour = self.selection()
        self.assertRedirects(self.client.post(reverse('suivi:sortir', args=[self.s.pk]), {**token, 'fin': '2026-01-20'}), retour)
        self.assertEqual(self.client.get(retour).context['selection_sejour'].pk, self.s.pk)
        self.s.refresh_from_db(); self.accord.refresh_from_db(); self.a.refresh_from_db()
        self.assertEqual(self.s.fin, date(2026, 1, 20))
        self.assertEqual(self.accord.fin, date(2026, 3, 1))
        self.assertIsNone(self.a.fin)

    def test_distribution_et_annulation_tracees(self):
        token, retour = self.selection()
        self.assertRedirects(self.client.post(reverse('suivi:distribuer_repas', args=[self.r.pk]),
            {**token, 'beneficiaire': self.p.pk, 'date': '2026-01-05', 'quantite': 1}), retour)
        distribution = RepasDistribue.objects.get()
        self.assertRedirects(self.client.post(reverse('suivi:annuler_repas', args=[distribution.pk]),
            {**token, 'motif': 'Distribution fictive saisie par erreur'}), retour)
        distribution.refresh_from_db()
        self.assertIsNotNone(distribution.annule_le)
        self.assertEqual(self.client.get(retour).context['selection_repas'].pk, self.r.pk)

    def test_note_et_conflit_correction(self):
        token, retour = self.selection()
        self.assertRedirects(self.client.post(reverse('suivi:notes', args=['sejour', self.s.pk]), {**token, 'contenu': 'Note fictive'}), retour)
        note = NotePartagee.objects.get()
        url = reverse('suivi:corriger_contribution', args=['note', note.pk])
        valeurs = {**token, 'contenu': 'Note corrigée', 'texte_attendu': 'Périmé', 'motif': 'Précision fictive'}
        page = self.client.post(url, valeurs)
        self.assertContains(page, retour.replace('&', '&amp;'), status_code=409)
        valeurs['texte_attendu'] = note.contenu
        self.assertRedirects(self.client.post(url, valeurs), retour)

    def test_actions_absence_et_lieu_sans_doublon(self):
        aff = h.ajouter_periode(self.u, self.s, date(2026, 1, 3), None, self.lieu)
        abs_ = h.ajouter_periode(self.u, self.s, date(2026, 1, 4), None, absence=True)
        page = self.client.get(self.url)
        self.assertContains(page, reverse('suivi:changer_lieu', args=[aff.pk]))
        self.assertContains(page, reverse('suivi:clore_absence', args=[abs_.pk]))
        self.assertNotContains(page, reverse('suivi:absence', args=[self.s.pk]))
        self.assertNotContains(page, reverse('suivi:affecter', args=[self.s.pk]))

    def test_date_de_travail_conservee(self):
        token, retour = self.selection(retour='jour', date_service='2026-01-06')
        form = self.client.get(reverse('suivi:absence', args=[self.s.pk]), token)
        self.assertEqual(form.context['form'].initial['debut'], date(2026, 1, 6))
        self.assertRedirects(self.client.post(reverse('suivi:absence', args=[self.s.pk]), {**token, 'debut': '2026-01-06', 'fin': ''}), retour)
        self.assertEqual(self.client.get(retour).context['dossier_valeurs']['date_service'], '2026-01-06')

    def test_selection_etrangere_et_contexte_falsifie_ignores(self):
        autre = suivi.ouvrir(self.u, self.m, [self.p], date(2026, 1, 1))
        r = repas.accorder(self.u, autre, [self.p], date(2026, 1, 1), None, 'diner')
        token, _ = self.selection(repas=r.pk, sejour='//exemple.test')
        page = self.client.get(self.url, {'repas': r.pk, 'sejour': 'invalide'})
        self.assertEqual(page.context['selection_repas'].pk, self.r.pk)
        for donnees in [token, {'contexte_dossier': '//exemple.test'}]:
            page = self.client.get(reverse('suivi:distribuer_repas', args=[r.pk]), donnees)
            self.assertNotContains(page, 'Retour au dossier')

    def test_droits_et_refus_direct_meme_avec_contexte_valide(self):
        token, _ = self.selection()
        self.u.user_permissions.remove(*Permission.objects.filter(content_type__app_label='personnes', codename__in=[
            'view_accordhebergement', 'view_repasdistribue', 'view_informationsaccompagnement', 'view_situationsociale', 'change_sejour']))
        page = self.client.get(self.url, token)
        for texte in ['id="hebergement"', 'id="repas"', 'Situation et parcours sociaux', 'Informations pratiques et projet']:
            self.assertNotContains(page, texte)
        url = reverse('suivi:sortir', args=[self.s.pk])
        self.assertEqual(self.client.get(url, token).status_code, 403)
        self.assertEqual(self.client.post(url, {**token, 'fin': '2026-01-20'}).status_code, 403)
        self.assertFalse(OperationHebergement.objects.filter(action='Sortie effective').exists())

    def test_lieux_masques_et_requetes_bornees(self):
        h.ajouter_periode(self.u, self.s, date(2026, 1, 3), None, self.lieu)
        self.u.user_permissions.remove(Permission.objects.get(content_type__app_label='personnes', codename='view_lieuhebergement'))
        self.assertNotContains(self.client.get(self.url), self.lieu.libelle)
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as premiere:
            self.client.get(self.url)
        for i in range(12):
            accord = h.accorder(self.u, self.a, [self.p], date(2026, 1, 1), None)
            h.admettre(self.u, accord, [self.p], date(2026, 1, 3))
            repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), None, 'diner')
        with CaptureQueriesContext(connection) as seconde:
            self.client.get(self.url)
        self.assertLessEqual(len(seconde), len(premiere) + 2)

    def test_resume_social_historique_et_creation_lieu(self):
        token, retour = self.selection()
        for nom in ['resume', 'social', 'trajectoire', 'corrections']:
            self.assertContains(self.client.get(reverse('suivi:' + nom, args=[self.a.pk]), token), retour.replace('&', '&amp;'))
        url = reverse('suivi:creer_lieu') + '?' + urlencode({**token, 'accord': self.accord.pk})
        self.assertRedirects(self.client.post(url, {**token, 'libelle': 'Nouveau lieu fictif', 'partenaire': ''}), retour)

    def test_recherche_conservee_et_selection_par_formulaire_get(self):
        token, retour = self.selection(q='Personne fictive', page='2')
        page = self.client.get(retour)
        self.assertIn('q=Personne+fictive', page.context['retour_origine'])
        self.assertIn('page=2', page.context['retour_origine'])
        nouveau = repas.accorder(self.u, self.a, [self.p], date(2026, 2, 1), None, 'diner')
        page = self.client.get(self.url, {**token, 'repas': nouveau.pk, 'sejour': self.s.pk})
        self.assertEqual(page.context['selection_repas'].pk, nouveau.pk)
        self.assertEqual(page.context['selection_sejour'].pk, self.s.pk)
        page = self.client.get(page.context['retour_dossier'])
        self.assertEqual(page.context['selection_repas'].pk, nouveau.pk)
        self.assertIn('q=Personne+fictive', page.context['retour_origine'])
