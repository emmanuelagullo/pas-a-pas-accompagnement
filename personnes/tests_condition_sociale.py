"""Qualification des vues communes et du transport des formulaires existants."""
from datetime import date
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from . import models as m, bd6, coordonnees, condition_sociale


class ConditionSocialeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u = get_user_model().objects.create_superuser('bd-fictif')
        cls.p = m.Personne.objects.create(designation='Thomas fictif', cree_par=cls.u)
        cls.m = m.Menage.objects.create(libelle='Ménage fictif', cree_par=cls.u)
        m.Appartenance.objects.create(menage=cls.m, personne=cls.p, debut=date(2026, 1, 1))
        cls.a = m.Accompagnement.objects.create(menage=cls.m, debut=date(2026, 10, 10), cree_par=cls.u)
        cls.a.beneficiaires.add(cls.p)
        cls.old = m.SituationPersonnelle.objects.create(personne=cls.p, dimension='emploi',
            valeur='sans_emploi', debut=date(2026, 9, 1), source='Entretien fictif', auteur=cls.u)

    def setUp(self):
        self.client.force_login(self.u)
        self.url = reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk])

    def test_integrale_date_entree_et_donnees_directement_visibles(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['condition_jour'], date(2026, 10, 10))
        for titre in ('Protection juridique', 'Mesure déclarée', 'Fratrie déclarée', 'Téléphone', 'Dettes'):
            self.assertContains(r, titre if titre != 'Protection juridique' else 'Protections juridiques déclarées')
        self.assertContains(r, 'condition-heritee')
        self.assertNotContains(r, 'Détail et historique des coordonnées')
        self.assertContains(r, 'Dans cette page')
        self.assertEqual(m.SituationPersonnelle.objects.count(), 1)

    def test_vue_historique_menage_utilise_composition_datee(self):
        autre = m.Personne.objects.create(designation='Nadia fictive', cree_par=self.u)
        m.Appartenance.objects.create(menage=self.m, personne=autre, debut=date(2026, 10, 15))
        url = reverse('dossiers:detail', args=['menage', self.m.pk])
        r = self.client.get(url, {'vue_sociale': 'date', 'date_sociale': '2026-10-10'})
        self.assertEqual([x['personne'].pk for x in r.context['condition_personnes']], [self.p.pk])
        self.assertEqual(self.client.get(url, {'vue_sociale': 'date', 'date_sociale': 'invalide'}).status_code, 404)
        self.assertEqual(self.client.get(url, {'vue_sociale': 'date', 'date_sociale': '2099-01-01'}).status_code, 404)

    def test_formulaire_sur_place_date_source_et_conflit(self):
        url = reverse('dossiers:coordonnees_nouvelles', args=[self.p.pk]) + '?date=2026-10-10'
        r = self.client.get(url, HTTP_X_CONDITION_FORM='1')
        self.assertContains(r, 'data-condition-form')
        self.assertNotContains(r, '<html')
        self.assertEqual(r.context['form'].initial['debut'], date(2026, 10, 10))
        token = r.context['form'].initial['attendu']
        data = {'attendu': token, 'debut': '2026-10-10', 'ville': 'Bordeaux', 'source': ''}
        erreur = self.client.post(url, data, HTTP_X_CONDITION_FORM='1')
        self.assertContains(erreur, 'Bordeaux')
        self.assertFalse(m.CoordonneesPersonnelles.objects.exists())
        data['source'] = 'Entretien fictif'
        succes = self.client.post(url, data, HTTP_X_CONDITION_FORM='1')
        self.assertEqual(succes.json(), {'enregistre': True})
        self.assertEqual(m.CoordonneesPersonnelles.objects.get().ville, 'Bordeaux')
        conflit = self.client.post(url, data, HTTP_X_CONDITION_FORM='1')
        self.assertEqual(conflit.status_code, 409)
        self.assertContains(conflit, 'Bordeaux', status_code=409)
        self.assertEqual(m.RevisionCoordonneesPersonnelles.objects.count(), 1)

    def test_changement_social_propose_valeur_sans_reprendre_source(self):
        url = reverse('dossiers:social_nouveau', args=[self.p.pk, 'emploi'])
        r = self.client.get(url, {'date': '2026-10-10'}, HTTP_X_CONDITION_FORM='1')
        self.assertEqual(r.context['form'].initial['valeur'], 'sans_emploi')
        self.assertEqual(r.context['form'].initial['source'], '')
        self.assertEqual(r.context['form'].initial['debut'], date(2026, 10, 10))

    def test_droits_revalides_pour_fragment(self):
        lecteur = get_user_model().objects.create_user('lecteur-fictif')
        self.client.force_login(lecteur)
        self.assertEqual(self.client.get(reverse('dossiers:coordonnees_nouvelles', args=[self.p.pk]),
            HTTP_X_CONDITION_FORM='1').status_code, 403)
        request = RequestFactory().get('/')
        request.user = lecteur
        groupes, _ = condition_sociale.presentation(request, [], date(2026, 10, 10), self.m, 'menage', None, {})
        self.assertEqual(groupes, [])

    def test_requetes_regroupees_par_modele_pas_par_personne(self):
        personnes = [self.p] + [m.Personne.objects.create(designation=f'Personne fictive {i}', cree_par=self.u) for i in range(3)]
        request = RequestFactory().get('/')
        request.user = self.u
        self.u.get_all_permissions()
        with CaptureQueriesContext(connection) as un:
            condition_sociale.presentation(request, personnes[:1], date(2026, 10, 10), self.m, 'menage', None, {})
        with CaptureQueriesContext(connection) as quatre:
            condition_sociale.presentation(request, personnes, date(2026, 10, 10), self.m, 'menage', None, {})
        self.assertLessEqual(len(quatre), len(un) + 2)
        self.assertLessEqual(len(quatre), 35)
