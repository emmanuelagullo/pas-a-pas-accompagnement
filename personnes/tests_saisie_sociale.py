"""Contexte d'opération, provenance et vues : contrats indépendants."""
from datetime import date
from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from . import models as m, bd6, coordonnees, saisie_sociale


class SaisieSocialeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u = get_user_model().objects.create_superuser('saisie-fictive')
        cls.p = m.Personne.objects.create(designation='Personne fictive', cree_par=cls.u)
        cls.m = m.Menage.objects.create(libelle='Ménage fictif', cree_par=cls.u)
        m.Appartenance.objects.create(personne=cls.p, menage=cls.m, debut=date(2026, 1, 1))
        cls.a = m.Accompagnement.objects.create(menage=cls.m, debut=date(2026, 10, 10), cree_par=cls.u)
        cls.a.beneficiaires.add(cls.p)

    def setUp(self):
        self.client.force_login(self.u)
        self.url = reverse('dossiers:coordonnees_nouvelles', args=[self.p.pk]) + '?date=2026-10-10&saisie_sociale=1'

    def donnees(self, url=None, **valeurs):
        page = self.client.get(url or self.url, HTTP_X_CONDITION_FORM='1')
        f = page.context['form']
        return {'attendu': f.initial['attendu'], 'debut': '2026-10-10', 'ville': 'Bordeaux', **valeurs}

    def test_contexte_facultatif_source_inconnue_et_autocompletion_autorisee(self):
        r = self.client.post(self.url, self.donnees(contexte_saisie='Entretien fictif'), HTTP_X_CONDITION_FORM='1')
        self.assertEqual(r.json(), {'enregistre': True})
        self.assertEqual(m.CoordonneesPersonnelles.objects.get().source, '')
        j = m.RevisionCoordonneesPersonnelles.objects.get()
        self.assertEqual((j.contexte_saisie, j.motif), ('Entretien fictif', ''))
        page = self.client.get(reverse('dossiers:detail', args=['personne', self.p.pk]))
        self.assertIn('Entretien fictif', page.context['condition_contextes'])
        historique = self.client.get(reverse('dossiers:coordonnees', args=[self.p.pk]))
        self.assertContains(historique, 'Contexte : Entretien fictif')
        flux = StringIO(); call_command('dumpdata', 'personnes.revisioncoordonneespersonnelles', all=True, stdout=flux)
        self.assertIn('Entretien fictif', flux.getvalue())

    def test_rectification_courante_sans_motif_ne_remplace_pas_la_source(self):
        self.client.post(self.url, self.donnees(source='Courrier fictif'), HTTP_X_CONDITION_FORM='1')
        x = m.CoordonneesPersonnelles.objects.get()
        url = reverse('dossiers:coordonnees_corriger', args=[self.p.pk, x.pk]) + '?date=2026-10-10&contexte_prise=' + str(self.a.pk)
        page = self.client.get(url, HTTP_X_CONDITION_FORM='1')
        f = page.context['form']
        self.assertFalse(f.fields['motif'].required)
        self.assertFalse(f.fields['condition_confirmation'].required)
        data = self.donnees(url, source='Courrier fictif', telephone='06 00 00 00 00', contexte_saisie='Rectification fictive', condition_preuve=f.fields['condition_preuve'].initial)
        self.assertEqual(self.client.post(url, data, HTTP_X_CONDITION_FORM='1').json(), {'enregistre': True})
        x.refresh_from_db(); self.assertEqual(x.source, 'Courrier fictif')
        j = m.RevisionCoordonneesPersonnelles.objects.first()
        self.assertEqual((j.action, j.motif, j.contexte_saisie), ('correction', '', 'Rectification fictive'))

    def test_erreur_necrit_rien_et_contexte_ne_fuit_pas(self):
        data = self.donnees(courriel='invalide', contexte_saisie='Ne pas conserver')
        self.assertContains(self.client.post(self.url, data, HTTP_X_CONDITION_FORM='1'), 'invalide')
        self.assertFalse(m.CoordonneesPersonnelles.objects.exists())
        self.client.post(self.url, self.donnees(), HTTP_X_CONDITION_FORM='1')
        self.assertEqual(m.RevisionCoordonneesPersonnelles.objects.get().contexte_saisie, '')
        self.assertEqual(saisie_sociale.contexte_courant(), '')
        class Form:
            cleaned_data = {'contexte_saisie': 'Contexte transitoire'}
        def echec(**d):
            raise RuntimeError('Erreur fictive')
        with self.assertRaises(RuntimeError): saisie_sociale.executer(Form(), echec)
        self.assertEqual(saisie_sociale.contexte_courant(), '')

    def test_limites_et_conflit_conservent_la_saisie_sans_nouveau_journal(self):
        data = self.donnees(contexte_saisie='x' * 241)
        self.assertContains(self.client.post(self.url, data, HTTP_X_CONDITION_FORM='1'), '240')
        self.assertFalse(m.RevisionCoordonneesPersonnelles.objects.exists())
        data = self.donnees(contexte_saisie='Premier entretien fictif')
        self.client.post(self.url, data, HTTP_X_CONDITION_FORM='1')
        r = self.client.post(self.url, {**data, 'contexte_saisie': 'Saisie périmée'}, HTTP_X_CONDITION_FORM='1')
        self.assertEqual(r.status_code, 409)
        self.assertEqual(m.RevisionCoordonneesPersonnelles.objects.count(), 1)
        self.assertContains(r, 'Saisie périmée', status_code=409)

    def test_dates_implicites_prioritaires_et_date_libre_accessible_sans_js(self):
        url = reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk])
        r = self.client.get(url, {'vue_sociale': 'entree', 'date_sociale': '1900-01-01'})
        self.assertEqual(r.context['condition_jour'], date(2026, 10, 10))
        self.assertContains(r, 'data-condition-date-repli')
        self.assertContains(r, 'data-date="2026-10-10"')
        r = self.client.get(url, {'vue_sociale': 'date', 'date_sociale': '2026-10-12'})
        self.assertEqual(r.context['condition_jour'], date(2026, 10, 12))
        self.assertContains(r, 'data-condition-date-repli disabled')
        self.assertContains(r, '<legend>Vue et saisie</legend>')
        m.Accompagnement.objects.filter(pk=self.a.pk).update(fin=date(2026, 10, 20))
        r = self.client.get(url, {'vue_sociale': 'fin', 'date_sociale': '1900-01-01'})
        self.assertEqual(r.context['condition_jour'], date(2026, 10, 19))
        self.assertContains(r, 'data-date="2026-10-19"')

    def test_synthese_selectionne_les_valeurs_renseignees_et_origines_disponibles(self):
        self.client.post(self.url, self.donnees(telephone='06 00 00 00 00', rue='Rue fictive', code_postal='33000', pays='France', courriel='fictif@example.org'), HTTP_X_CONDITION_FORM='1')
        url = reverse('dossiers:detail', args=['personne', self.p.pk])
        params = {'vue_sociale': 'date', 'date_sociale': '2026-10-12', 'presentation_sociale': 'synthese', 'origines_sociales': '1'}
        page = self.client.get(url, params)
        fiche = next(g for g in page.context['condition_personnes'][0]['groupes'] if g['code'] == 'coordonnees')['fiches'][0]
        self.assertIn('06 00 00 00 00', [c['valeur'] for c in fiche['resume']])
        self.assertTrue(all(not c['vide'] for c in fiche['resume']))
        self.assertGreater(len(fiche['resume']), 3)
        self.assertContains(page, 'fictif@example.org')
        self.assertContains(page, 'condition-origines')
        self.assertContains(page, 'Source : non précisée')
        self.assertContains(page, 'toutes les valeurs connues sont visibles en entier')

    def test_retour_schema_refuse_perte_du_contexte(self):
        from importlib import import_module
        from django.apps import apps
        from django.db import connection
        from django.db.migrations.exceptions import IrreversibleError
        verifier = import_module('personnes.migrations.0041_contexte_saisie_sociale_facultatif').verifier_retour
        class Editeur:
            pass
        editeur = Editeur(); editeur.connection = connection
        verifier(apps, editeur)
        self.client.post(self.url, self.donnees(contexte_saisie='Contexte conservé'), HTTP_X_CONDITION_FORM='1')
        with self.assertRaises(IrreversibleError): verifier(apps, editeur)

    def test_repli_sans_js_conserve_contexte_facultatif(self):
        page = self.client.get(self.url)
        self.assertFalse(page.context['form'].fields['contexte_saisie'].widget.is_hidden)
        data = self.donnees(contexte_saisie='Entretien sans JavaScript')
        reponse = self.client.post(self.url, data)
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(m.RevisionCoordonneesPersonnelles.objects.get().contexte_saisie, 'Entretien sans JavaScript')
        self.assertEqual(m.CoordonneesPersonnelles.objects.get().source, '')

    def test_rectification_inchangee_necree_pas_de_journal(self):
        from django.core.exceptions import ValidationError
        x = bd6.renseigner(self.u, self.p, 'emploi', 'sans_emploi', date(2026, 10, 10), '', bd6.jeton(self.p))
        token = bd6.jeton(self.p)
        revision = bd6.revision(self.p)
        with self.assertRaises(ValidationError):
            bd6.renseigner(self.u, self.p, 'emploi', 'sans_emploi', x.debut, '', token, correction=x.pk)
        self.assertEqual(m.RevisionSituationPersonnelle.objects.count(), 1)
        self.p.refresh_from_db()  # L’instance Python n’est pas restaurée par le rollback SQL.
        self.assertEqual(bd6.revision(self.p), revision)
