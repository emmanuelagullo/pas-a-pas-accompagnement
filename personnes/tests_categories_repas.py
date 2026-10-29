"""Catégories suggérées et correction ordinaire, uniquement données fictives."""
from datetime import date
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from . import models as m, repas, suivi, correction_repas
from .forms_repas import CorrectionDistributionForm, DistributionForm
from acteurs import tests as tests_acteurs
from acteurs.contexte import perimetre


class CategoriesRepasTests(TestCase):
    def setUp(self):
        self.u = get_user_model().objects.create_superuser('repas-categories-fictives', password='Fictif-2026!')
        self.p = m.Personne.objects.create(designation='Maïa fictive', cree_par=self.u)
        self.m = suivi.creer_menage(self.u,'Les Passerelles — fictif',[self.p],date(2026,1,1))
        self.a = suivi.ouvrir(self.u,self.m,[self.p],date(2026,1,1))
        self.accord = repas.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,2,1),'dejeuner')
        self.r = repas.distribuer(self.u,self.accord,self.p,date(2026,1,2),1,'Jeune fictif')
        self.client.force_login(self.u)
        self.url = reverse('dossiers:corriger_distribution',args=[self.r.pk])

    def test_creation_suggestions_sans_defaut_arbitraire_et_saisie_libre(self):
        autre = repas.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,2,1),'diner')
        repas.distribuer(self.u,autre,self.p,date(2026,1,2),1,'Autre accord privé fictif')
        form = DistributionForm(accord=self.accord)
        self.assertEqual(form.fields['categorie_declaree'].widget.propositions,['Jeune fictif'])
        self.assertFalse(form.initial.get('categorie_declaree'))
        form = DistributionForm({'beneficiaire':self.p.pk,'date':'2026-01-03','quantite':1,'categorie_declaree':'Catégorie libre fictive'},accord=self.accord)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['categorie_declaree'],'Catégorie libre fictive')

    def test_correction_conserve_categorie_motif_facultatif_et_trace_complete(self):
        for headers in [{}, {'HTTP_X_CONDITION_FORM':'1'}]:
            page = self.client.get(self.url,**headers)
            self.assertContains(page,'Précisions facultatives')
            self.assertEqual(page.context['form'].initial['categorie_declaree'],'Jeune fictif')
            self.assertContains(page,'<datalist')
        form = CorrectionDistributionForm(repas=self.r)
        data={'quantite':2,'categorie_declaree':form.initial['categorie_declaree'],'attendu':form.initial['attendu']}
        response = self.client.post(self.url,data,HTTP_X_CONDITION_FORM='1')
        self.assertEqual(response.json(),{'enregistre':True})
        self.r.refresh_from_db()
        self.assertEqual((self.r.quantite,self.r.categorie_declaree),(2,'Jeune fictif'))
        revision = self.r.revisions.get()
        self.assertEqual(revision.motif,'')
        self.assertEqual(revision.auteur,self.u)
        self.assertEqual((revision.avant[0]['quantite'],revision.apres[0]['quantite']),(1,2))
        self.assertEqual(self.client.post(self.url,data,HTTP_X_CONDITION_FORM='1').status_code,409)
        trop_long = {**data,'motif':'x'*241,'attendu':correction_repas.jeton(self.r)}
        erreur = self.client.post(self.url,trop_long,HTTP_X_CONDITION_FORM='1')
        self.assertContains(erreur,'class="condition-precisions" open',status_code=200)
        repas.annuler(self.u,self.r,'Annulation fictive')
        with self.assertRaises(ValidationError):
            correction_repas.corriger(self.u,self.r,3,'Jeune fictif','',correction_repas.jeton(self.r))


class CategoriesAccesTests(TestCase):
    compte = tests_acteurs.AccesTests.compte
    dossier = tests_acteurs.AccesTests.dossier

    def setUp(self):
        tests_acteurs.AccesTests.setUp(self)

    def test_suggestions_bornees_service_et_dossiers_accessibles(self):
        def creer(u,service,prise,p,categorie):
            with perimetre(u,service=service):
                a=repas.accorder(u,prise,[p],date(2026,1,1),date(2026,2,1),'dejeuner')
                repas.distribuer(u,a,p,date(2026,1,2),1,categorie)
                return a
        a=creer(self.ua,self.sa,self.a,self.personne_a,'Service A fictif')
        b=creer(self.ub,self.sb,self.b,self.personne_b,'Secret B fictif')
        # Même un compte habilité aux deux services reçoit les choix de l'accord visé.
        from acteurs import services as services_acteurs
        from acteurs.models import AppartenanceProfessionnelle
        AppartenanceProfessionnelle.objects.create(professionnel=self.pa,service=self.sb,debut=date(2020,1,1))
        services_acteurs.habiliter(self.admin,self.ua,self.sb,'social',date(2020,1,1))
        with perimetre(self.ua,service=self.sb):
            f=DistributionForm(accord=a)
            self.assertEqual(f.fields['categorie_declaree'].widget.propositions,['Service A fictif'])
        # Une catégorie d'un dossier du même service non accessible reste exclue.
        from acteurs.models import PorteeObjet, Service
        PorteeObjet.objects.filter(modele=b._meta.label_lower,identifiant=str(b.pk)).update(service=self.sa)
        PorteeObjet.objects.filter(modele='personnes.repasdistribue',prise=self.b).update(service=self.sa)
        Service.objects.filter(pk=self.sa.pk).update(politique='individuel')
        with perimetre(self.uc,service=self.sa):
            f=DistributionForm(accord=a)
            self.assertEqual(f.fields['categorie_declaree'].widget.propositions,[])
