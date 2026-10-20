from io import StringIO
from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command
from django.contrib.auth import get_user_model
from .models import Personne
from . import suivi, repas


class NavigationTests(TestCase):
    def setUp(self):
        self.u=get_user_model().objects.create_user('navigation-fictive')
        call_command('autoriser_chrs4',self.u.username,stdout=StringIO())
        self.u=get_user_model().objects.get(pk=self.u.pk)
        self.p=Personne.objects.create(designation='Navigation fictive',cree_par=self.u)
        self.m=suivi.creer_menage(self.u,'Ménage navigation',[self.p],date(2026,1,1))
        self.a=suivi.ouvrir(self.u,self.m,[self.p],date(2026,1,1))
        self.client.force_login(self.u)

    def test_liens_et_retour_apres_saisie(self):
        cible=reverse('suivi:accompagnement',args=[self.a.pk])
        self.assertContains(self.client.get(reverse('personnes:detail',args=[self.p.pk])),cible)
        self.assertContains(self.client.get(cible),'Bénéficiaires')
        reponse=self.client.post(reverse('suivi:accorder_repas',args=[self.a.pk]),{'beneficiaires':[self.p.pk],'debut':'2026-01-01','fin':'','service':'dejeuner','prestataire':''})
        accord=self.a.accords_repas.get()
        self.assertRedirects(reponse,reverse('suivi:accord_repas',args=[accord.pk]))
        self.assertContains(self.client.get(reverse('suivi:detail',args=[self.m.pk])),cible)

    def test_refus_direct_sans_droits(self):
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(reverse('suivi:accompagnement',args=[self.a.pk])).status_code,403)
        self.assertEqual(self.client.get(reverse('personnes:detail',args=[self.p.pk])).status_code,403)
