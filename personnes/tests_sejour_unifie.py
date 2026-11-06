"""Un parcours pour prévoir l’accueil et enregistrer l’arrivée, sans faits implicites."""
from datetime import date, timedelta
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from django.utils import timezone
from .tests_hebergement import Donnees
from . import admission, accords, suivi
from .models import Personne, AccordHebergement, Sejour, Affectation, OperationHebergement


class SejourUnifieTests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        self.client.force_login(self.u)
        self.prise = reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk])
        self.creation = reverse('dossiers:nouveau', args=['menage', self.m.pk, 'hebergement'])

    def test_une_arrivee_commune_cree_un_seul_sejour(self):
        autre = Personne.objects.create(designation='Autre bénéficiaire fictif', cree_par=self.u)
        self.a.beneficiaires.add(autre)
        accord = admission.accueillir(
            self.u, self.a, [self.p, autre], date(2026, 1, 10), None,
            date(2026, 1, 10), admission.jeton(self.a), lieu=self.lieu,
        )
        sejour = accord.sejours.get()
        self.assertEqual(set(sejour.beneficiaires.all()), {self.p, autre})
        self.assertEqual(sejour.affectations.get().lieu, self.lieu)
        self.assertEqual(accord.operations.filter(action='Admission effective').count(), 1)

    def test_reouverture_confirmee_avec_le_sejour(self):
        self.u.user_permissions.add(Permission.objects.get(
            content_type__app_label='personnes', codename='change_accompagnement',
        ))
        self.a.fin = date(2026, 3, 1)
        self.a.save(update_fields=['fin'])
        url = self.creation
        donnees = {'accompagnement': str(self.a.pk), 'beneficiaires': [self.p.pk], 'debut': '02/03/2026',
                   'arrivee_effectuee': 'on', 'admission': '02/03/2026',
                   'attendu': admission.jeton(self.a)}
        page = self.client.post(url, donnees)
        self.assertContains(page, 'Rouvrir la prise en charge et enregistrer le séjour')
        self.a.refresh_from_db()
        self.assertEqual(self.a.fin, date(2026, 3, 1))
        self.assertEqual(Sejour.objects.count(), 1)
        reponse = self.client.post(url, {**donnees, 'confirmation_fin': page.context['form'].jeton_fin})
        self.assertEqual(reponse.status_code, 302)
        self.a.refresh_from_db()
        self.assertIsNone(self.a.fin)
        self.assertEqual(Sejour.objects.count(), 2)
        self.assertEqual(self.a.evolutions_prevision.get().action, 'fin_effective')

    def prevoir(self, personnes=None):
        self.a.refresh_from_db()
        return admission.accueillir(self.u, self.a, personnes or [self.p], date(2026, 1, 1), None,
            None, admission.jeton(self.a), arrivee_effectuee=False)

    def test_arrivee_simple_en_un_geste(self):
        with patch('acteurs.profils_collectifs.parcours_simple', return_value=True):
            form = self.client.get(self.creation).context['form']
            self.assertNotIn('arrivee_effectuee', form.fields)
            self.assertNotIn('admission', form.fields)
            rep = self.client.post(self.creation, {
                'accompagnement': str(self.a.pk), 'beneficiaires': [str(self.p.pk)],
                'debut': '2026-01-05', 'attendu': form.initial['attendu'],
                'lieu': str(self.lieu.pk),
            })
        self.assertEqual(rep.status_code, 302)
        sejour = AccordHebergement.objects.exclude(pk=self.accord.pk).get().sejours.get()
        self.assertEqual(sejour.debut, date(2026, 1, 5))
        self.assertEqual(sejour.affectations.get().lieu, self.lieu)

    def test_non_presentation_ne_cree_pas_de_sejour(self):
        self.u.user_permissions.add(*Permission.objects.filter(codename__in=['annuler_accordhebergement', 'view_evolutionaccord']))
        accord = self.prevoir()
        url = reverse('suivi:annuler_accord', args=['hebergement', accord.pk]) + '?non_presentation=1'
        form = self.client.get(url).context['form']
        self.assertEqual(self.client.post(url, {
            'attendu': form.initial['attendu'], 'confirmer': 'on',
        }).status_code, 302)
        accord.refresh_from_db()
        self.assertEqual(accord.motif_annulation, 'Non-présentation')
        self.assertFalse(accord.sejours.exists())

    def test_futur_ne_cree_ni_sejour_ni_affectation(self):
        debut = timezone.localdate() + timedelta(days=30)
        self.a.refresh_from_db()
        accord = admission.accueillir(self.u, self.a, [self.p], debut, debut + timedelta(days=30),
            None, admission.jeton(self.a), arrivee_effectuee=False)
        self.assertEqual(accord.debut, debut)
        self.assertEqual(Sejour.objects.count(), 1)
        self.assertFalse(Affectation.objects.exists())
        self.assertEqual(list(accord.operations.values_list('action', flat=True)), ['Hébergement accordé'])
        page = self.client.get(self.prise)
        self.assertContains(page, 'Prévu — arrivée à confirmer')
        from urllib.parse import quote
        # Une seule barre NAV : l’arrivée agit sur l’accueil sélectionné.
        page = self.client.get(self.prise + '?sejour=' + str(accord.pk))
        self.assertContains(page, 'operation=' + quote(reverse('suivi:arrivee_prevue', args=[accord.pk]), safe=''))
        self.assertNotContains(page, 'Autorisation sans admission')
        self.assertNotContains(page, 'Accorder un hébergement sans admission')

    def test_post_decoche_ignore_anciens_champs_arrivee_meme_sans_js(self):
        self.a.refresh_from_db()
        from urllib.parse import urlencode
        token = self.client.get(self.prise).context['prise'].navigation['contexte_dossier']
        page = self.client.post(self.creation + '?' + urlencode({'contexte_dossier': token}), {'accompagnement': str(self.a.pk), 'beneficiaires': [str(self.p.pk)],
            'debut': '2026-01-01', 'fin': '', 'admission': 'date-non-valide', 'lieu': str(self.lieu.pk), 'attendu': admission.jeton(self.a)})
        self.assertEqual(page.status_code, 302)
        self.assertIn('#hebergement-prevu-', page.url)
        accord = AccordHebergement.objects.exclude(pk=self.accord.pk).get()
        self.assertFalse(accord.sejours.exists())
        self.assertFalse(Affectation.objects.exists())
        self.assertContains(self.client.get(page.url), 'hebergement-prevu-' + str(accord.pk))

    def test_arrivee_effectuee_exige_date_et_refuse_future_sans_ecriture(self):
        self.a.refresh_from_db()
        data = {'accompagnement': str(self.a.pk), 'beneficiaires': [str(self.p.pk)], 'debut': '2026-01-01',
            'arrivee_effectuee': 'on', 'attendu': admission.jeton(self.a)}
        page = self.client.post(self.creation, data)
        self.assertIn('admission', page.context['form'].errors)
        data['admission'] = (timezone.localdate() + timedelta(days=1)).isoformat()
        self.assertEqual(self.client.post(self.creation, data).status_code, 409)
        self.assertEqual(AccordHebergement.objects.count(), 1)
        self.assertEqual(Sejour.objects.count(), 1)

    def test_compte_sans_droit_arrivee_peut_seulement_prevoir(self):
        self.u.user_permissions.remove(Permission.objects.get(content_type__app_label='personnes', codename='add_sejour'))
        self.u = get_user_model().objects.get(pk=self.u.pk)
        page = self.client.get(self.creation)
        self.assertEqual(page.status_code, 200)
        self.assertFalse(page.context['form']['arrivee_effectuee'].value())
        accord = self.prevoir()
        self.assertFalse(accord.sejours.exists())
        with self.assertRaises(PermissionDenied):
            admission.accueillir(self.u, self.a, [self.p], date(2026, 1, 1), None,
                date(2026, 1, 2), admission.jeton(self.a))
        self.assertEqual(self.client.get(reverse('suivi:arrivee_prevue', args=[accord.pk])).status_code, 403)

    def test_arrivee_reutilise_accord_avec_lieu_et_refuse_rejeu(self):
        accord = self.prevoir()
        attendu = accords.jeton(accord)
        sejours = admission.enregistrer_arrivee(self.u, accord, [self.p], date(2026, 1, 2), attendu, self.lieu)
        self.assertEqual(AccordHebergement.objects.count(), 2)
        self.assertEqual(sejours[0].accord_id, accord.pk)
        self.assertEqual(sejours[0].affectations.get().lieu, self.lieu)
        self.assertIsNone(sejours[0].fin)
        with self.assertRaises(ValidationError):
            admission.enregistrer_arrivee(self.u, accord, [self.p], date(2026, 1, 3), attendu)
        self.assertEqual(accord.sejours.count(), 1)

    def test_arrivee_partielle_famille_et_vue_personne(self):
        enfant = Personne.objects.create(designation='Enfant fictif', cree_par=self.u)
        self.a.beneficiaires.add(enfant)
        accord = self.prevoir([self.p, enfant])
        admission.enregistrer_arrivee(self.u, accord, [self.p], date(2026, 1, 2), accords.jeton(accord))
        page = self.client.get(self.prise)
        prevu = next(x for x in page.context['hebergements_prevus'] if x.pk == accord.pk)
        self.assertEqual([p.pk for p in prevu.personnes_attendues], [enfant.pk])
        page = self.client.get(reverse('dossiers:prise', args=['personne', self.p.pk, self.a.pk]))
        self.assertNotIn(accord.pk, [x.pk for x in page.context['hebergements_prevus']])
        admission.enregistrer_arrivee(self.u, accord, [enfant], date(2026, 1, 3), accords.jeton(accord))
        self.assertNotIn(accord.pk, [x.pk for x in self.client.get(self.prise).context['hebergements_prevus']])

    def test_arrivee_annulee_ou_modifiee_ou_hors_beneficiaires_refusee(self):
        accord = self.prevoir()
        attendu = accords.jeton(accord)
        accord.fin = date(2026, 2, 1); accord.save(update_fields=['fin'])
        with self.assertRaises(ValidationError):
            admission.enregistrer_arrivee(self.u, accord, [self.p], date(2026, 1, 2), attendu)
        autre = Personne.objects.create(designation='Autre fictif', cree_par=self.u)
        with self.assertRaises(ValidationError):
            admission.enregistrer_arrivee(self.u, accord, [autre], date(2026, 1, 2), accords.jeton(accord))
        call_command('autoriser_bd3', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        accords.annuler(self.u, accord, 'Erreur fictive', accords.jeton(accord))
        with self.assertRaises(ValidationError):
            admission.enregistrer_arrivee(self.u, accord, [self.p], date(2026, 1, 2), accords.jeton(accord))
        self.assertFalse(accord.sejours.exists())

    def test_echec_lieu_annule_toute_arrivee(self):
        accord = self.prevoir()
        with patch('personnes.admission.h.ajouter_periode', side_effect=ValidationError('Lieu indisponible fictif')):
            with self.assertRaises(ValidationError):
                admission.enregistrer_arrivee(self.u, accord, [self.p], date(2026, 1, 2), accords.jeton(accord), self.lieu)
        self.assertFalse(accord.sejours.exists())
        self.assertFalse(accord.operations.filter(action='Admission effective').exists())

    def test_confirmation_retour_form3_selection_et_csrf(self):
        accord = self.prevoir()
        page = self.client.get(self.prise, {'q': 'Fictif'})
        prevu = next(x for x in page.context['hebergements_prevus'] if x.pk == accord.pk)
        token = prevu.navigation['contexte_dossier']
        url = reverse('suivi:arrivee_prevue', args=[accord.pk])
        page = self.client.get(url, {'contexte_dossier': token})
        data = {'contexte_dossier': token, 'attendu': page.context['form'].initial['attendu'],
            'beneficiaires': [str(self.p.pk)], 'debut': '2026-01-02', 'lieu': ''}
        protege = Client(enforce_csrf_checks=True); protege.force_login(self.u)
        self.assertEqual(protege.post(url, data).status_code, 403)
        page = self.client.post(url, data)
        self.assertEqual(page.status_code, 302)
        self.assertIn('/prises/' + str(self.a.pk), page.url)
        retour = self.client.get(page.url)
        self.assertEqual(retour.context['selection_sejour'].accord_id, accord.pk)
        self.assertIn('q=Fictif', retour.context['retour'])

    def test_ancien_formulaire_refuse_et_prevision_ne_rejoue_pas(self):
        from django.core import signing
        ancien = signing.dumps(admission.etat(self.a), salt='chrs25-admission')
        with self.assertRaises(ValidationError):
            admission.accueillir(self.u, self.a, [self.p], date(2026, 1, 1), None, None, ancien, arrivee_effectuee=False)
        self.a.refresh_from_db()
        token = admission.jeton(self.a)
        for i in range(2):
            if i:
                with self.assertRaises(ValidationError):
                    admission.accueillir(self.u, self.a, [self.p], date(2026, 1, 1), None, None, token, arrivee_effectuee=False)
            else:
                admission.accueillir(self.u, self.a, [self.p], date(2026, 1, 1), None, None, token, arrivee_effectuee=False)
        self.assertEqual(AccordHebergement.objects.count(), 2)


class ConcurrenceArrivee(Donnees, TransactionTestCase):
    def test_deux_confirmations_ne_creent_quune_arrivee(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections, OperationalError
        self.preparer()
        self.a.refresh_from_db()
        accord = admission.accueillir(self.u, self.a, [self.p], date(2026, 1, 1), None, None,
            admission.jeton(self.a), arrivee_effectuee=False)
        token = accords.jeton(accord)
        depart = Barrier(2)
        def ecrire(_):
            close_old_connections()
            try:
                u = get_user_model().objects.get(pk=self.u.pk)
                u.get_all_permissions()
                # Chaque requête possède ses instances. Résoudre la chaîne du
                # verrou avant le départ : une lecture paresseuse du ménage
                # pendant l'UPDATE adverse peut bloquer les deux écritures sur
                # SQLite en mémoire partagée, sans remettre en cause l'absence
                # de doublon garantie par le service.
                accord_local = AccordHebergement.objects.select_related(
                    'accompagnement__menage').get(pk=accord.pk)
                personne_locale = Personne.objects.get(pk=self.p.pk)
                depart.wait(timeout=10)
                try:
                    admission.enregistrer_arrivee(u, accord_local, [personne_locale], date(2026, 1, 2), token)
                    return True, ''
                except (ValidationError, OperationalError) as erreur:
                    return False, f'{type(erreur).__name__}: {erreur}'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultats = list(pool.map(ecrire, range(2)))
        self.assertEqual(sum(succes for succes, _ in resultats), 1, resultats)
        self.assertEqual(accord.sejours.count(), 1)
        self.assertEqual(accord.operations.filter(action='Admission effective').count(), 1)
        with self.assertRaises(ValidationError):
            admission.enregistrer_arrivee(self.u, accord, [self.p], date(2026, 1, 2), token)
        self.assertEqual(accord.sejours.count(), 1)
