"""Form2 : vrais services, périmètres explicites, repli sans JavaScript."""
from datetime import date
from io import StringIO
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from .tests_hebergement import Donnees
from .models import AccordHebergement, Sejour, AccordRepas, RepasDistribue, Personne
from . import suivi, admission, hebergement


class Form2Tests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        self.client.force_login(self.u)
        self.detail = reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk])
        self.nouveau = reverse('dossiers:nouveau', args=['menage', self.m.pk, 'hebergement'])

    def donnees(self):
        self.a.refresh_from_db()
        return {'accompagnement': str(self.a.pk), 'beneficiaires': [str(self.p.pk)],
                'debut': '2026-04-01', 'fin': '2026-05-01', 'admission': '2026-04-01', 'arrivee_effectuee': 'on',
                'attendu': admission.jeton(self.a)}

    def test_selection_directe_et_conservation_autre_boite(self):
        r = AccordRepas.objects.create(accompagnement=self.a, debut=date(2026, 1, 1), service='diner', cree_par=self.u)
        r.beneficiaires.add(self.p)
        page = self.client.get(self.detail, {'repas': str(r.pk), 'q': 'Fictif'})
        self.assertNotContains(page, 'Afficher les actions')
        # Le sélecteur Situation / Évolution utilise deux radios ; les
        # prestations gardent leurs accès directs sans radio de sélection.
        self.assertContains(page, 'name="lecture_sociale"', count=2)
        from html.parser import HTMLParser
        class Radios(HTMLParser):
            noms=[]
            def handle_starttag(self, tag, attrs):
                a=dict(attrs)
                if tag=='input' and a.get('type')=='radio':self.noms.append(a.get('name'))
        parseur=Radios();parseur.feed(page.content.decode())
        self.assertEqual(set(parseur.noms), {'lecture_sociale'})
        self.assertContains(page, 'data-dossier-selection')
        self.assertContains(page, 'data-dossier-action')
        selection = page.context['sejours_dossier'][0].selection_url
        suivant = self.client.get(selection)
        self.assertEqual(suivant.context['selection_repas'].pk, r.pk)
        self.assertIn('q=Fictif', suivant.context['retour'])

    def test_creation_unique_get_sans_ecriture_et_rattachement_visible(self):
        page = self.client.get(self.nouveau)
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context['periode'].pk, self.a.pk)
        self.assertContains(page, 'Prise en charge :')
        self.assertEqual(AccordHebergement.objects.count(), 1)
        self.assertEqual(Sejour.objects.count(), 1)

    def test_admission_individuelle_et_retour_selectionne(self):
        hebergement.sortir(self.u, self.s, date(2026, 1, 20))
        data = self.donnees()
        data['lieu'] = str(self.lieu.pk)
        page = self.client.post(self.nouveau + '?q=Fictif', data)
        self.assertEqual(page.status_code, 302)
        retour = self.client.get(page.url)
        selection = retour.context['selection_sejour']
        self.assertNotEqual(selection.pk, self.s.pk)
        self.assertEqual(selection.beneficiaires.get(), self.p)
        self.assertEqual(selection.affectations.get().lieu, self.lieu)
        self.assertEqual(RepasDistribue.objects.count(), 0)
        self.assertIn('q=Fictif', retour.context['retour'])

    def test_admission_perimee_aucune_ecriture_et_saisie_conservee(self):
        data = self.donnees()
        data['attendu'] = 'perime'
        page = self.client.post(self.nouveau, data)
        self.assertEqual(page.status_code, 409)
        self.assertContains(page, '2026-04-01', status_code=409)
        self.assertEqual(AccordHebergement.objects.count(), 1)
        self.assertEqual(Sejour.objects.count(), 1)

    def test_plusieurs_periodes_choix_explicite_et_hors_dossier_refuse(self):
        a2 = suivi.ouvrir(self.u, self.m, [self.p], date(2025, 1, 1))
        page = self.client.get(self.nouveau)
        self.assertIsNone(page.context['periode'])
        self.assertNotIn('beneficiaires', page.context['form'].fields)
        self.assertContains(page, 'method="get"')
        choisi = self.client.get(self.nouveau, {'accompagnement': a2.pk})
        self.assertEqual(choisi.context['periode'].pk, a2.pk)
        m = suivi.creer_menage(self.u, 'Autre fictif', [self.p], date(2026, 1, 1))
        autre = suivi.ouvrir(self.u, m, [self.p], date(2026, 1, 1))
        data = self.donnees(); data['accompagnement'] = str(autre.pk)
        page = self.client.post(self.nouveau, data)
        self.assertIn('accompagnement', page.context['form'].errors)
        self.assertEqual(AccordHebergement.objects.count(), 1)

    def test_vue_personne_preselection_et_aucun_beneficiaire_invente(self):
        p2 = Personne.objects.create(designation='Autre fictive', cree_par=self.u)
        suivi.ajouter_appartenance(self.u, self.m, p2, date(2026, 1, 1))
        a2 = suivi.ouvrir(self.u, self.m, [self.p, p2], date(2025, 1, 1))
        url = reverse('dossiers:nouveau', args=['personne', self.p.pk, 'repas'])
        page = self.client.get(url, {'accompagnement': a2.pk})
        self.assertEqual(page.context['form'].initial['beneficiaires'], [self.p.pk])
        data = {'accompagnement': str(a2.pk), 'beneficiaires': [str(self.p.pk)], 'debut': '2026-04-01', 'service': 'diner'}
        page = self.client.post(url, data)
        self.assertEqual(page.status_code, 302)
        self.assertEqual(AccordRepas.objects.get().beneficiaires.get(), self.p)
        self.assertEqual(RepasDistribue.objects.count(), 0)

    def test_droits_creation_retires_refus_get_et_post(self):
        self.u.user_permissions.remove(Permission.objects.get(codename='add_sejour', content_type__app_label='personnes'))
        self.assertEqual(self.client.get(self.nouveau).status_code, 200)
        self.assertEqual(self.client.post(self.nouveau, self.donnees()).status_code, 403)
        self.assertEqual(Sejour.objects.count(), 1)

    def test_plusieurs_services_atomiques_et_aucune_distribution(self):
        from . import repas
        url = reverse('dossiers:nouveau', args=['menage', self.m.pk, 'services_repas'])
        self.a.refresh_from_db()
        data = {'accompagnement': str(self.a.pk), 'beneficiaires': [str(self.p.pk)],
                'debut': '2026-04-01', 'services': ['dejeuner', 'diner'], 'attendu': repas.jeton_services(self.a)}
        page = self.client.post(url, data)
        self.assertEqual(page.status_code, 302)
        self.assertEqual(set(AccordRepas.objects.values_list('service', flat=True)), {'dejeuner', 'diner'})
        self.assertEqual(RepasDistribue.objects.count(), 0)
        self.assertIn(self.client.get(page.url).context['selection_repas'].pk, set(AccordRepas.objects.values_list('pk', flat=True)))

    def test_beneficiaire_hors_periode_et_csrf_refuses(self):
        from django.test import Client
        p = Personne.objects.create(designation='Hors période fictive', cree_par=self.u)
        data = self.donnees(); data['beneficiaires'] = [str(p.pk)]
        page = self.client.post(self.nouveau, data)
        self.assertIn('beneficiaires', page.context['form'].errors)
        protege = Client(enforce_csrf_checks=True); protege.force_login(self.u)
        self.assertEqual(protege.post(self.nouveau, self.donnees()).status_code, 403)
        self.assertEqual(AccordHebergement.objects.count(), 1)
