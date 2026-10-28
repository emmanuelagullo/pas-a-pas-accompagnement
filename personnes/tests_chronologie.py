from datetime import date
from io import StringIO
from urllib.parse import urlsplit, parse_qs
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from .tests_hebergement import Donnees
from . import chronologie as c, hebergement as h, repas, models as m


class ChronologieTests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_chrs2', self.u.username, stdout=StringIO())
        self.u = type(self.u).objects.get(pk=self.u.pk)
        self.client.force_login(self.u)
        self.url = reverse('dossiers:chronologie', args=['personne', self.p.pk])
        self.params = {'chrono_debut': '2026-01-01', 'chrono_fin': '2026-04-01', 'chrono_type': ''}

    def test_limites_et_geometrie(self):
        self.assertIsNone(c.geometrie(date(2026, 1, 1), date(2026, 1, 3), date(2026, 1, 3), date(2026, 1, 8)))
        self.assertIsNone(c.geometrie(date(2026, 1, 8), None, date(2026, 1, 3), date(2026, 1, 8)))
        self.assertIsNone(c.geometrie(None, None, date(2026, 1, 3), date(2026, 1, 8)))
        geo = c.geometrie(date(2026, 1, 1), None, date(2026, 1, 3), date(2026, 1, 8))
        self.assertEqual(geo['largeur'], '100.0000')
        self.assertTrue(geo['avant'] and geo['apres'])
        self.assertFalse(c.Filtres({'chrono_debut': '2026-01-01', 'chrono_fin': '2030-01-01'}).is_valid())

    def test_lieux_absence_et_retour_exact(self):
        h.ajouter_periode(self.u, self.s, date(2026, 1, 3), date(2026, 1, 10), self.lieu)
        h.ajouter_periode(self.u, self.s, date(2026, 1, 5), date(2026, 1, 7), absence=True)
        r = self.client.get(self.url, self.params)
        self.assertContains(r, 'Absence enregistrée')
        self.assertContains(r, 'Chambre fictive')
        lignes = r.context['page_obj'].object_list
        sejour = next(x for x in lignes if x['id'] == 'sejour-' + str(self.s.pk))
        self.assertEqual(urlsplit(sejour['url']).fragment, 'sejour-' + str(self.s.pk))
        cible = self.client.get(sejour['url'])
        self.assertEqual(cible.status_code, 200)
        retour = cible.context['retour_dossier']
        self.assertEqual(urlsplit(retour).path, self.url)
        self.assertEqual(urlsplit(retour).fragment, 'chrono-sejour-' + str(self.s.pk))
        retour_page = self.client.get(retour)
        self.assertEqual(retour_page.context['form'].cleaned_data['chrono_debut'], date(2026, 1, 1))
        self.assertEqual(retour_page.context['selection'], 'sejour-' + str(self.s.pk))

    def test_beneficiaires_partiels_et_autorisation_distincte(self):
        autre = m.Personne.objects.create(designation='AUTRE BENEFICIAIRE PRIVE', cree_par=self.u)
        self.a.beneficiaires.add(autre)
        accord = repas.accorder(self.u, self.a, [autre], date(2026, 1, 1), date(2026, 3, 1), 'diner')
        visible = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), date(2026, 3, 1), 'dejeuner')
        r = self.client.get(self.url, self.params)
        self.assertNotContains(r, str(accord.pk))
        self.assertNotContains(r, 'AUTRE BENEFICIAIRE PRIVE')
        self.assertContains(r, str(visible.pk))
        self.assertContains(r, 'distributions distinctes')
        self.assertContains(r, 'Autorisation, sans preuve d’arrivée')

    def test_prevision_depassee_et_aucune_fin_fictive(self):
        self.a.fin_prevue = date(2026, 2, 1)
        self.a.save()
        r = self.client.get(self.url, self.params)
        lignes = [x for x in r.context['page_obj'] if x['groupe'] == 'prise']
        self.assertEqual(len(lignes), 2)
        self.assertIsNone(next(x for x in lignes if x['libelle'] == 'Prise en charge')['fin'])
        self.assertEqual(next(x for x in lignes if x['prevu'])['fin'], self.a.fin_prevue)
        self.assertContains(r, 'Fin prévue dépassée')

    def test_refus_prise_etrangere_et_dates_invalides(self):
        from uuid import uuid4
        self.assertEqual(self.client.get(self.url, {**self.params, 'chrono_prise': uuid4()}).status_code, 404)
        r = self.client.get(self.url, {**self.params, 'chrono_fin': 'date-invalide'})
        self.assertContains(r, 'Saisissez une date valide')
        self.assertEqual(len(r.context['page_obj']), 0)

    def test_continuation_et_arrivee_annulee_ne_sont_pas_une_continuite_inventee(self):
        from django.contrib.auth.models import Permission
        from django.utils import timezone
        self.s.fin = date(2026, 1, 10); self.s.save()
        suite = m.Sejour.objects.create(accord=self.accord, debut=date(2026, 1, 10), fin=date(2026, 1, 20), origine_collective=self.s, cree_par=self.u)
        suite.beneficiaires.add(self.p)
        annule = m.Sejour.objects.create(accord=self.accord, debut=date(2026, 2, 1), fin=date(2026, 2, 5), cree_par=self.u,
                                        annule_le=timezone.now(), annule_par=self.u, motif_annulation='Erreur fictive')
        annule.beneficiaires.add(self.p)
        r = self.client.get(self.url, self.params)
        self.assertContains(r, 'Continuation individuelle')
        self.assertNotContains(r, str(annule.pk))
        self.u.user_permissions.add(Permission.objects.get(content_type__app_label='personnes', codename='view_annulationarrivee'))
        r = self.client.get(self.url, self.params)
        self.assertContains(r, str(annule.pk))
        self.assertContains(r, 'Arrivée annulée')
        lignes = r.context['page_obj'].object_list
        self.assertEqual(next(x for x in lignes if x['id'] == 'sejour-' + str(self.s.pk))['fin'], date(2026, 1, 10))
        self.assertEqual(next(x for x in lignes if x['id'] == 'sejour-' + str(suite.pk))['debut'], date(2026, 1, 10))

    def test_dossier_long_pagination_et_requetes_groupees(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        with CaptureQueriesContext(connection) as petites:
            self.client.get(self.url, self.params)
        for i in range(125):
            x = m.AccordRepas.objects.create(accompagnement=self.a, debut=date(2026, 1, 1), fin=date(2026, 2, 1), service='dejeuner', cree_par=self.u)
            x.beneficiaires.add(self.p)
        with CaptureQueriesContext(connection) as grandes:
            r = self.client.get(self.url, {**self.params, 'chrono_page': '2'})
        self.assertEqual(len(r.context['page_obj']), 60)
        self.assertEqual(r.context['page_obj'].number, 2)
        self.assertLessEqual(len(grandes), len(petites) + 2)
        cible = self.client.get(r.context['page_obj'][0]['url'])
        retour = self.client.get(cible.context['retour_dossier'])
        self.assertEqual(retour.context['page_obj'].number, 2)

    def test_retour_depuis_prise_bd_et_signature(self):
        r = self.client.get(self.url, {**self.params, 'chrono_type': 'prise'})
        url = r.context['page_obj'][0]['url']
        prise = self.client.get(url)
        self.assertContains(prise, 'Revenir à la chronologie')
        retour = prise.context['retour_chronologie']
        self.assertEqual(urlsplit(retour).path, self.url)
        self.assertEqual(self.client.get(retour).context['form'].cleaned_data['chrono_type'], 'prise')
        self.assertEqual(self.client.post(self.url).status_code, 405)


from acteurs import tests as tests_acteurs
from acteurs.models import Service, Responsabilite, PorteeObjet, Habilitation


class ChronologieAccesTests(TestCase):
    setUp = tests_acteurs.AccesTests.setUp
    compte = tests_acteurs.AccesTests.compte
    dossier = tests_acteurs.AccesTests.dossier

    def test_objets_partiellement_accessibles_et_revocation(self):
        self.client.force_login(self.ua)
        url = reverse('dossiers:chronologie', args=['menage', self.ma.pk])
        params = {'chrono_debut': '2026-01-01', 'chrono_fin': '2026-03-01', 'chrono_type': ''}
        self.sa.politique = 'individuel'; self.sa.save()
        Responsabilite.objects.create(dossier=self.da, professionnel=self.pa, hebergement=self.h, cree_par=self.admin)
        prive = m.AccordHebergement.objects.create(accompagnement=self.a, debut=date(2026, 1, 1), cree_par=self.ua)
        prive.beneficiaires.add(self.personne_a)
        PorteeObjet.objects.create(modele=prive._meta.label_lower, identifiant=str(prive.pk), service=self.sa, dossier=self.da, prise=self.a,
                                  prestation_modele='accordhebergement', prestation_id=prive.pk)
        r = self.client.get(url, params)
        self.assertContains(r, str(self.h.pk))
        self.assertNotContains(r, str(prive.pk))
        self.assertNotContains(r, str(self.hb.pk))
        self.assertEqual(self.client.get(reverse('dossiers:chronologie', args=['menage', self.mb.pk]), params).status_code, 404)
        self.assertEqual(self.client.get(reverse('suivi:accord_hebergement', args=[prive.pk])).status_code, 404)
        Habilitation.objects.filter(compte=self.ua).update(revoque_le=__import__('django.utils.timezone', fromlist=['now']).now())
        self.assertIn(self.client.get(url, params).status_code, (403, 404))
