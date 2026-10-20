from datetime import date
from io import StringIO
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from .models import Personne, AccordRepas, RepasDistribue, OperationRepas
from . import suivi, repas


class RepasTests(TestCase):
    def setUp(self):
        self.u = get_user_model().objects.create_user('repas-fictif')
        call_command('autoriser_chrs2', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        self.p = Personne.objects.create(designation='Bénéficiaire fictif', cree_par=self.u)
        self.autre = Personne.objects.create(designation='Autre personne fictive', cree_par=self.u)
        m = suivi.creer_menage(self.u, 'Ménage fictif', [self.p], date(2026,1,1))
        self.a = suivi.ouvrir(self.u, m, [self.p], date(2026,1,1))
        self.accord = repas.accorder(self.u, self.a, [self.p], date(2026,1,1), date(2026,2,1), 'dejeuner', 'Partenaire fictif')

    def distribuer(self, **kw):
        d = dict(accord=self.accord, beneficiaire=self.p, date=date(2026,1,2), quantite=1)
        d.update(kw)
        return repas.distribuer(self.u, **d)

    def test_accord_et_effectif_independants_annulation_et_correction(self):
        self.assertFalse(self.accord.realisations.exists())
        r = self.distribuer()
        with self.assertRaises(ValidationError): self.distribuer()
        repas.annuler(self.u, r, 'Erreur de saisie')
        with self.assertRaises(ValidationError): repas.annuler(self.u, r, 'Seconde annulation')
        self.distribuer(quantite=2)
        self.assertEqual(RepasDistribue.objects.filter(annule_le=None).get().quantite, 2)
        self.assertEqual(OperationRepas.objects.count(), 4)
        self.assertEqual(self.accord.beneficiaires.get(), self.p)

    def test_refus_dates_quantites_beneficiaire_et_accord(self):
        for valeurs in ({'date':date(2025,12,31)}, {'date':date(2026,2,1)}, {'quantite':0}, {'beneficiaire':self.autre}):
            with self.assertRaises(ValidationError): self.distribuer(**valeurs)
        with self.assertRaises(ValidationError):
            repas.accorder(self.u,self.a,[self.autre],date(2026,1,1),None,'diner')
        self.assertFalse(RepasDistribue.objects.exists())
        self.assertEqual(OperationRepas.objects.count(),1)

    def test_contrainte_sql_doublon_et_quantite(self):
        r = self.distribuer()
        for q in [0,1]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                RepasDistribue.objects.create(accord=self.accord,beneficiaire=self.p,date=r.date,quantite=q,cree_par=self.u)

    def test_droits_et_parcours_http(self):
        self.client.force_login(self.u)
        url = reverse('suivi:accord_repas',args=[self.accord.pk])
        self.assertContains(self.client.get(url),'Partenaire fictif')
        self.assertEqual(self.client.post(reverse('suivi:distribuer_repas',args=[self.accord.pk]), {'beneficiaire':self.p.pk,'date':'2026-01-03','quantite':1}).status_code,302)
        self.assertContains(self.client.get(url),'1 repas distribués')
        r = RepasDistribue.objects.get()
        self.assertEqual(self.client.post(reverse('suivi:annuler_repas',args=[r.pk]),{'motif':'Erreur'}).status_code,302)
        self.assertContains(self.client.get(url),'0 repas distribués')
        nu = get_user_model().objects.create_user('sans-repas')
        self.client.force_login(nu)
        for cible in [url,reverse('suivi:accorder_repas',args=[self.a.pk]),reverse('suivi:distribuer_repas',args=[self.accord.pk]),reverse('suivi:annuler_repas',args=[r.pk])]:
            self.assertEqual(self.client.get(cible).status_code,403)
        with self.assertRaises(PermissionDenied): repas.annuler(nu,r,'Erreur')

    def test_cloture_et_future(self):
        self.distribuer()
        with self.assertRaises(ValidationError):
            suivi.clore(self.u, self.a, date(2026,1,2))
        suivi.clore(self.u, self.a, date(2026,1,3))
        with self.assertRaises(ValidationError):
            self.distribuer(date=date(2026,1,3))
        from unittest.mock import patch
        with patch('personnes.repas.timezone.localdate', return_value=date(2026,1,1)):
            with self.assertRaises(ValidationError): self.distribuer()

    def test_accord_http(self):
        self.client.force_login(self.u)
        reponse = self.client.post(reverse('suivi:accorder_repas',args=[self.a.pk]), {
            'beneficiaires':[self.p.pk], 'debut':'2026-01-01', 'fin':'2026-01-20',
            'service':'diner', 'prestataire':'Cuisine fictive'})
        self.assertEqual(reponse.status_code,302)
        self.assertEqual(AccordRepas.objects.count(),2)
