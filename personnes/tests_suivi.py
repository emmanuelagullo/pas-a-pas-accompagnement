from datetime import date
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from .models import Personne, Menage, Appartenance, Accompagnement, EvenementSuivi
from . import suivi


class SuiviTests(TestCase):
    def setUp(self):
        self.compte = get_user_model().objects.create_user('fictif', password='mot-de-passe-fictif')
        self.personne = Personne.objects.create(designation='Personne fictive', cree_par=self.compte)
        call_command('autoriser_chrs1', 'fictif', verbosity=0)
        self.compte = get_user_model().objects.get(pk=self.compte.pk)
        self.debut = date(2026, 1, 1)

    def creer(self):
        return suivi.creer_menage(self.compte, 'Ménage fictif', [self.personne], self.debut)

    def test_beneficiaires_stables_et_simultaneite(self):
        menage = self.creer()
        autre = self.creer()
        a = suivi.ouvrir(self.compte, menage, [self.personne], self.debut)
        suivi.ouvrir(self.compte, autre, [self.personne], self.debut)
        suivi.ouvrir(self.compte, menage, [self.personne], self.debut)
        suivi.clore(self.compte, menage.appartenances.get(), date(2026, 2, 1))
        self.assertEqual(list(a.beneficiaires.all()), [self.personne])
        self.assertEqual(Accompagnement.objects.filter(fin=None).count(), 3)
        self.assertEqual(EvenementSuivi.objects.filter(type='appartenance_close').count(), 1)

    def test_periodes_et_rollback(self):
        menage = self.creer()
        avant = EvenementSuivi.objects.count()
        with self.assertRaises(ValidationError):
            suivi.ajouter_appartenance(self.compte, menage, self.personne, self.debut, self.debut)
        self.assertEqual(EvenementSuivi.objects.count(), avant)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Appartenance.objects.create(menage=menage, personne=self.personne, debut=self.debut, fin=self.debut)
        with self.assertRaises(ValidationError):
            suivi.ouvrir(self.compte, menage, [], self.debut)
        self.assertFalse(Accompagnement.objects.exists())

    def test_cloture_conditionnelle_et_audit(self):
        menage = self.creer()
        a = suivi.ouvrir(self.compte, menage, [self.personne], self.debut)
        copie = Accompagnement.objects.get(pk=a.pk)
        suivi.clore(self.compte, a, date(2026, 2, 1))
        with self.assertRaises(ValidationError):
            suivi.clore(self.compte, copie, date(2026, 3, 1))
        a.refresh_from_db()
        self.assertEqual(a.fin, date(2026, 2, 1))
        self.assertEqual(EvenementSuivi.objects.filter(type='accompagnement_clos').count(), 1)

    def test_parcours_http_et_acces_direct_sans_droits(self):
        self.client.force_login(self.compte)
        reponse = self.client.post(reverse('suivi:creer'), {'libelle': 'Seul', 'personnes': [self.personne.pk], 'debut': '2026-01-01'})
        self.assertEqual(reponse.status_code, 302)
        menage = Menage.objects.get()
        url = reverse('suivi:detail', args=[menage.pk])
        self.assertContains(self.client.get(url), 'Seul')
        reponse = self.client.post(reverse('suivi:ouvrir', args=[menage.pk]), {'beneficiaires': [self.personne.pk], 'debut': '2026-01-01'})
        self.assertEqual(reponse.status_code, 302)
        a = Accompagnement.objects.get()
        self.assertEqual(self.client.post(reverse('suivi:clore_accompagnement', args=[menage.pk, a.pk]), {'fin': '2026-02-01'}).status_code, 302)
        nu = get_user_model().objects.create_user('sans-droit')
        self.assertFalse(nu.user_permissions.exists())
        self.client.force_login(nu)
        for cible in [reverse('suivi:liste'), url, reverse('suivi:creer'), reverse('suivi:ouvrir', args=[menage.pk]), reverse('suivi:ajouter', args=[menage.pk])]:
            self.assertEqual(self.client.get(cible).status_code, 403)
            self.assertIn(self.client.post(cible, {}).status_code, (403, 405))
        with self.assertRaises(PermissionDenied):
            suivi.ouvrir(nu, menage, [self.personne], self.debut)
