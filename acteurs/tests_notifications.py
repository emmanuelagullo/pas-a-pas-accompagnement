from datetime import date,timedelta
from django.test import TestCase,Client
from django.urls import reverse
from django.db import transaction
from django.core.exceptions import PermissionDenied,ValidationError
from django.utils import timezone
from . import tests as anciens,services as s,notifications as n,reperage
from .models import *
from .contexte import perimetre
from personnes import models as m,repas

class NotificationsTests(TestCase):
    setUp=anciens.AccesTests.setUp
    compte=anciens.AccesTests.compte
    dossier=anciens.AccesTests.dossier
    def preparer(self):
        r=Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin)
        Notification.objects.all().delete();return r
    def test_attribution_a_autrui_pas_a_soi(self):
        s.ajouter_responsabilite(self.ua,self.da,self.da,self.pc,timezone.localdate(),'suivi',s.jeton(self.da))
        self.assertEqual(Notification.objects.filter(compte=self.uc,nature='attribution').count(),1)
        self.assertFalse(Notification.objects.filter(compte=self.ua).exists())
        with perimetre(self.uc):self.assertEqual(len(n.visibles(self.uc)),1)
    def test_modifications_regroupees_lecture_et_concurrence(self):
        self.preparer()
        with perimetre(self.uc,self.sa):
            self.ma.libelle='Ménage mis à jour';self.ma.save()
            self.ma.libelle='Ménage complété';self.ma.save()
        x=Notification.objects.get(compte=self.ua,nature='modification');self.assertEqual(x.occurrences,2)
        with perimetre(self.ua):n.lire(self.ua,x.pk,s.jeton(x))
        x.refresh_from_db();self.assertIsNotNone(x.lu_le);ancien=s.jeton(x)
        with perimetre(self.uc,self.sa):self.ma.libelle='Ménage encore complété';self.ma.save()
        x.refresh_from_db();self.assertIsNone(x.lu_le)
        with perimetre(self.ua):
            with self.assertRaises(s.Conflit):n.lire(self.ua,x.pk,ancien)
    def test_prestation_au_referent_sans_propres_signaux(self):
        self.preparer()
        with perimetre(self.ua,self.sa):self.ma.libelle='Ma saisie';self.ma.save()
        self.assertFalse(Notification.objects.exists())
        with perimetre(self.uc,self.sa,creation='prestation'):repas.accorder(self.uc,self.a,[self.personne_a],date(2026,1,1),date(2027,1,1),'dejeuner')
        self.assertEqual(Notification.objects.filter(compte=self.ua,nature='prestation').count(),1)
        with perimetre(self.ua):self.assertEqual(len(n.visibles(self.ua)),1)
    def test_fin_mission_et_habilitation_meme_depuis_totaux(self):
        Service.objects.filter(pk=self.sa.pk).update(politique='individuel')
        r=Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin,debut=timezone.now()-timedelta(days=2))
        with perimetre(self.ua):self.assertEqual(len(n.visibles(self.ua)),1)
        Responsabilite.objects.filter(pk=r.pk).update(fin=timezone.now()-timedelta(seconds=1))
        with perimetre(self.ua,statistiques='etablissement'):self.assertEqual(n.visibles(self.ua),[])
        Service.objects.filter(pk=self.sa.pk).update(politique='lecture')
        with perimetre(self.ua):self.assertEqual(len(n.visibles(self.ua)),1)
        Habilitation.objects.filter(compte=self.ua).update(revoque_le=timezone.now())
        with perimetre(self.ua):self.assertEqual(n.visibles(self.ua),[])
    def test_transaction_annulee_annule_le_signal(self):
        self.preparer()
        try:
            with transaction.atomic():
                s.ajouter_responsabilite(self.ua,self.da,self.da,self.pc,timezone.localdate(),'suivi',s.jeton(self.da))
                raise ValidationError('Annulation de recette')
        except ValidationError:pass
        self.assertFalse(Notification.objects.exists())
    def test_direct_et_autre_compte_refuses(self):
        self.preparer();c=Client();c.force_login(self.uc)
        x=Notification.objects.create(compte=self.ua,dossier=self.da,cle='recette',nature='modification')
        self.assertEqual(c.post(reverse('acteurs:notification_lue',args=[x.pk]),{'attendu':s.jeton(x)}).status_code,403)
        self.assertNotContains(c.get(reverse('acteurs:notifications')),'Ménage fictif A')
    def test_demande_disparait_apres_decision(self):
        self.preparer();Etablissement.objects.filter(pk=self.etab.pk).update(reperage_identites=True)
        d=reperage.demander(self.uc,self.da)
        with perimetre(self.ua):self.assertEqual(len(n.visibles(self.ua)),1)
        reperage.decider(self.ua,d,False,s.jeton(d),s.jeton(self.da))
        with perimetre(self.ua):self.assertEqual(n.visibles(self.ua),[])

    def test_responsabilite_metier_ne_vaut_pas_acces_applicatif(self):
        coord,prof=self.compte('coordination-recette',self.sa,tache='coordination',statistiques_service=True)
        Responsabilite.objects.create(dossier=self.da,professionnel=prof,cree_par=self.ua)
        self.assertTrue(Notification.objects.filter(compte=coord).exists())
        with perimetre(coord,statistiques='service'):self.assertEqual(n.visibles(coord),[])
        c=Client();c.force_login(coord)
        self.assertNotContains(c.get(reverse('acteurs:notifications')),'Ménage fictif A')
