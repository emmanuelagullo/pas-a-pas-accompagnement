from datetime import date
from django.test import TestCase,Client
from django.urls import reverse
from django.core.exceptions import PermissionDenied,ValidationError
from django.utils import timezone
from . import tests as anciens,services as s,reperage
from .models import *
from .contexte import perimetre
from personnes import models as m,ouverture_prise,repas

class ReperageTests(TestCase):
    setUp=anciens.AccesTests.setUp
    compte=anciens.AccesTests.compte
    dossier=anciens.AccesTests.dossier
    def activer(self):
        Etablissement.objects.filter(pk=self.etab.pk).update(reperage_identites=True)
        Service.objects.filter(pk=self.sa.pk).update(politique='individuel')
    def connecte(self,u=None):
        c=Client();c.force_login(u or self.ua);return c
    def url(self,ds):return reverse('dossiers:detail',args=['menage',ds.menage_id])
    def test_option_et_frontiere_etablissement(self):
        c=self.connecte();self.assertNotContains(c.get('/',{'q':'fictive','fragment':1}),'Ménage fictif B')
        self.activer();self.assertContains(c.get('/',{'q':'fictive','fragment':1}),'Ménage fictif B')
        e=Etablissement.objects.create(organisme=self.org,fiche=m.Partenaire.objects.create(libelle='Autre établissement',cree_par=self.admin),reperage_identites=True)
        Service.objects.filter(pk=self.sb.pk).update(etablissement=e)
        self.assertEqual(c.get(self.url(self.db)).status_code,404)
    def test_identite_sans_contenu_et_aucune_ecriture(self):
        self.activer();c=self.connecte();self.assertContains(c.get(self.url(self.da)),'Identité repérée')
        self.assertEqual(c.get(reverse('dossiers:prise',args=['menage',self.ma.pk,self.a.pk])).status_code,404)
        self.assertEqual(c.get('/personnes/'+str(self.personne_b.pk)+'/pdf/').status_code,404)
        with perimetre(self.ua,reperage=True):
            self.assertTrue(m.Personne.objects.filter(pk=self.personne_b.pk).exists())
            self.assertFalse(m.Accompagnement.objects.filter(pk=self.b.pk).exists())
            self.assertEqual(m.Menage.objects.filter(pk=self.mb.pk).update(libelle='Interdit'),0)
            self.assertTrue(m.Menage.objects.filter(pk=self.mb.pk).exists())
            with perimetre(self.ua,export_demande=True):self.assertFalse(m.Menage.objects.filter(pk=self.mb.pk).exists())
        for option in ({'statistiques':'accessibles'},{'export_demande':True}):
            with perimetre(self.ua,reperage=True,**option):self.assertFalse(m.Menage.objects.filter(pk=self.mb.pk).exists())
    def test_creation_suggeree_ignore_les_filtres_pas_le_repertoire(self):
        self.activer();r=self.connecte().get('/',{'q':'Ménage fictif B','filtre':'mes','fragment':1})
        self.assertContains(r,'data-creation-suggeree="non"')
        self.assertContains(r,'Voir les correspondances dans Tous')
    def test_demande_acceptation_et_double_confirmation(self):
        self.activer();Responsabilite.objects.create(dossier=self.da,professionnel=self.pc,cree_par=self.admin)
        d=reperage.demander(self.ua,self.da);self.assertEqual(reperage.demander(self.ua,self.da).pk,d.pk)
        avant=Habilitation.objects.count()
        reperage.decider(self.uc,d,True,s.jeton(d),s.jeton(self.da))
        self.assertEqual(Habilitation.objects.count(),avant)
        with perimetre(self.ua):self.assertTrue(m.Accompagnement.objects.filter(pk=self.a.pk).exists())
        with self.assertRaises(ValidationError):reperage.decider(self.uc,d,True,s.jeton(d),s.jeton(self.da))
    def test_demande_expiree_ne_cree_aucun_droit(self):
        self.activer();Responsabilite.objects.create(dossier=self.da,professionnel=self.pc,cree_par=self.admin)
        d=reperage.demander(self.ua,self.da)
        Habilitation.objects.filter(compte=self.ua).update(revoque_le=timezone.now())
        with self.assertRaises(ValidationError):reperage.decider(self.uc,d,True,s.jeton(d),s.jeton(self.da))
        self.assertFalse(Responsabilite.objects.filter(dossier=self.da,professionnel=self.pa).exists())
    def test_autre_service_reste_sans_habilitation(self):
        self.activer()
        with self.assertRaises(PermissionDenied):reperage.demander(self.ua,self.db)
        d=DemandeRattachement.objects.create(dossier=self.db,demandeur=self.ub,professionnel=self.pb)
        self.assertEqual(self.connecte().get(reverse('acteurs:decider_rattachement',args=[d.pk])).status_code,404)
        with perimetre(self.ua,self.sa,reperage='prestation'):self.assertFalse(m.Accompagnement.objects.filter(pk=self.b.pk).exists())
    def test_nouvelle_prise_ne_reprend_pas_les_anciennes(self):
        self.activer()
        with perimetre(self.ua,self.sa,creation='prise',reperage=True):
            token=ouverture_prise.jeton(self.ma)
            a=ouverture_prise.ouvrir(self.ua,self.ma,[self.personne_a],timezone.localdate(),None,token,menage=self.ma)
        with perimetre(self.ua):
            self.assertTrue(m.Accompagnement.objects.filter(pk=a.pk).exists())
            self.assertFalse(m.Accompagnement.objects.filter(pk=self.a.pk).exists())
            self.assertFalse(m.AccordHebergement.objects.filter(pk=self.h.pk).exists())
        with self.assertRaises(ValidationError),perimetre(self.ua,self.sa,creation='prise',reperage=True):ouverture_prise.ouvrir(self.ua,self.ma,[self.personne_a],timezone.localdate(),None,token,menage=self.ma)
    def test_prestation_sans_suivi_social(self):
        self.activer()
        with perimetre(self.ua,self.sa,creation='prestation',reperage='prestation'):a=repas.accorder(self.ua,self.a,[self.personne_a],date(2026,1,1),date(2027,1,1),'dejeuner')
        with perimetre(self.ua):
            self.assertTrue(m.AccordRepas.objects.filter(pk=a.pk).exists())
            self.assertFalse(m.AccordHebergement.objects.filter(pk=self.h.pk).exists())
        self.assertFalse(Responsabilite.objects.filter(dossier=self.da,professionnel=self.pa,prise__isnull=True,hebergement__isnull=True,repas__isnull=True,aide__isnull=True).exists())
    def test_fin_politique_et_membre(self):
        self.activer();c=self.connecte();self.assertEqual(c.get(self.url(self.da)).status_code,200)
        Etablissement.objects.filter(pk=self.etab.pk).update(reperage_identites=False)
        self.assertEqual(c.get(self.url(self.da)).status_code,404)
    def test_formulaires_prestations_et_http_demande(self):
        self.activer();c=self.connecte()
        for prestation in ('hebergement','repas','services_repas'):
            self.assertEqual(c.get(reverse('dossiers:nouveau',args=['menage',self.ma.pk,prestation]),{'accompagnement':str(self.a.pk)}).status_code,200)
        self.assertEqual(c.get(reverse('dossiers:aide_accorder',args=[self.a.pk,'transport'])).status_code,200)
        url=reverse('acteurs:demander_rattachement',args=[self.da.pk]);self.assertEqual(c.post(url).status_code,302)
        self.assertTrue(DemandeRattachement.objects.filter(dossier=self.da,demandeur=self.ua).exists())
