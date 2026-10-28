from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
from . import tests as anciens,services as s
from .models import Responsabilite,Service
from .contexte import perimetre
from personnes import models as m

class RemplacementsTests(TestCase):
    setUp=anciens.AccesTests.setUp
    compte=anciens.AccesTests.compte
    dossier=anciens.AccesTests.dossier
    def test_fin_de_mission_et_politique_explicite(self):
        Service.objects.filter(pk=self.sa.pk).update(politique='individuel')
        Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin)
        demain=timezone.localdate()+timedelta(days=1)
        r=s.ajouter_responsabilite(self.ua,self.da,self.da,self.pc,timezone.localdate(),'suppleance',s.jeton(self.da),fin=demain)
        self.assertEqual(timezone.localtime(r.fin).date(),demain)
        self.client.force_login(self.ua)
        self.assertContains(self.client.get(reverse('dossiers:detail',args=['menage',self.ma.pk])),f'jusqu’au {demain:%d/%m/%Y} exclu')
        with perimetre(self.uc):self.assertTrue(m.Accompagnement.objects.filter(pk=self.a.pk).exists())
        Responsabilite.objects.filter(pk=r.pk).update(debut=timezone.now()-timedelta(days=2),fin=timezone.now()-timedelta(seconds=1))
        with perimetre(self.uc):self.assertFalse(m.Accompagnement.objects.filter(pk=self.a.pk).exists())
        Service.objects.filter(pk=self.sa.pk).update(politique='lecture')
        with perimetre(self.uc):
            self.assertTrue(m.Accompagnement.objects.filter(pk=self.a.pk).exists())
            self.assertEqual(m.Accompagnement.objects.filter(pk=self.a.pk).update(fin=demain),0)
    def test_fin_invalide_et_confirmation_perimee(self):
        token=s.jeton(self.da)
        with self.assertRaises(ValidationError):s.ajouter_responsabilite(self.ua,self.da,self.da,self.pc,timezone.localdate(),'suppleance',token,fin=timezone.localdate())
        self.da.refresh_from_db();token=s.jeton(self.da)
        s.ajouter_responsabilite(self.ua,self.da,self.da,self.pc,timezone.localdate(),'suppleance',token,fin=timezone.localdate()+timedelta(days=2))
        with self.assertRaises(s.Conflit):s.ajouter_responsabilite(self.ua,self.da,self.da,self.pc,timezone.localdate(),'suivi',token)
        self.assertEqual(Responsabilite.objects.filter(dossier=self.da,professionnel=self.pc).count(),1)
