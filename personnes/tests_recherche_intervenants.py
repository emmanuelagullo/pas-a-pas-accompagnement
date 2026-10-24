from datetime import date
from io import StringIO
import csv
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from .tests_hebergement import Donnees
from . import bd6, partenaires, intervenants, interventions, suivi, hebergement
from .tests_partenaires import valeurs as valeurs_organisme
from .tests_interventions import valeurs


class RechercheIntervenantsTests(Donnees,TestCase):
    def setUp(self):
        self.preparer();call_command('autoriser_solenne',self.u.username,stdout=StringIO())
        self.u=get_user_model().objects.get(pk=self.u.pk);self.client.force_login(self.u)
        self.org=partenaires.creer(self.u,date(2026,1,1),'Fictif',partenaires.jeton_creation(),**valeurs_organisme())
        self.prof=intervenants.creer(self.u,date(2026,1,1),'Fictif',intervenants.jeton_creation(),**valeurs(organisme=self.org))
        self.x=interventions.affecter(self.u,self.a,date(2026,1,1),None,'referent',self.prof,None,'Fictif',bd6.jeton(self.a))
        self.url=reverse('dossiers:recherche_intervenants')

    def test_selection_date_role_organisme_et_csv_meme_population(self):
        d={'date':'2026-01-02','organisme':self.org.pk,'role':'referent'}
        page=self.client.get(self.url,d)
        self.assertEqual(page.context['nombre_missions'],1);self.assertEqual(page.context['nombre_prises'],1)
        self.assertContains(page,reverse('dossiers:prise',args=['menage',self.m.pk,self.a.pk]))
        response=self.client.get(self.url,{**d,'format':'csv'})
        lignes=list(csv.DictReader(StringIO(response.content.decode()),delimiter=';'))
        self.assertEqual(len(lignes),1);self.assertEqual(lignes[0]['prise_id'],str(self.a.pk))
        self.assertEqual(self.client.get(self.url,{**d,'role':'prescripteur'}).context['nombre_missions'],0)
        self.assertEqual(self.client.get(self.url,{**d,'date':'2025-12-31'}).context['nombre_missions'],0)
        page=self.client.get(self.url,{**d,'date':'invalide','format':'csv'})
        self.assertEqual(page['Content-Type'],'text/html; charset=utf-8');self.assertContains(page,'errorlist')

    def test_changement_organisme_historique_parent_clos_annulation(self):
        intervenants.renseigner(self.u,self.prof,date(2026,2,1),'Fictif',bd6.jeton(self.prof),**valeurs())
        d={'organisme':self.org.pk,'date':'2026-01-31'}
        self.assertEqual(self.client.get(self.url,d).context['nombre_missions'],1)
        self.assertEqual(self.client.get(self.url,{**d,'date':'2026-02-01'}).context['nombre_missions'],0)
        hebergement.sortir(self.u,self.s,date(2026,1,20));suivi.clore(self.u,self.a,date(2026,2,1))
        self.assertEqual(self.client.get(self.url,{'date':'2026-02-01'}).context['nombre_missions'],0)
        interventions.annuler(self.u,self.a,self.x,'Mauvais dossier fictif',bd6.jeton(self.a))
        self.assertEqual(self.client.get(self.url,{'date':'2026-01-31'}).context['nombre_missions'],0)

    def test_droits_explicites_et_pas_de_recherche_legacy_par_nom(self):
        self.u.user_permissions.remove(Permission.objects.get(codename='view_affectationintervenant'))
        self.assertEqual(self.client.get(self.url).status_code,403)
        self.assertNotContains(self.client.get(reverse('dossiers:intervenants')),'Rechercher les prises en charge par intervenant')
