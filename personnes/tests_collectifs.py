from datetime import date, timedelta
from decimal import Decimal
from copy import deepcopy
from django.test import TestCase
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError, PermissionDenied
from django.urls import reverse
from django.utils import timezone
from acteurs.models import OrganismeGestionnaire, Etablissement, Service, DossierService, PorteeObjet
from acteurs.profils_collectifs import defaut, verifier
from . import models as m, collectifs as c
from .tests_hebergement import Donnees

class CollectifsTests(Donnees,TestCase):
    def setUp(self):
        self.preparer()
        self.u.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes'))
        self.u=type(self.u).objects.get(pk=self.u.pk)
        self.p.date_naissance=date(1980,1,1);self.p.precision_naissance='exacte';self.p.save()
        org=m.Partenaire.objects.create(libelle='Gestionnaire fictif',cree_par=self.u)
        fiche=m.Partenaire.objects.create(libelle='Établissement fictif',cree_par=self.u)
        g=OrganismeGestionnaire.objects.create(organisme=org)
        e=Etablissement.objects.create(organisme=g,fiche=fiche)
        self.service=Service.objects.create(etablissement=e,libelle='Les Amandiers',profil_collectif=defaut())
        ds=DossierService.objects.create(service=self.service,menage=self.m,cree_par=self.u)
        for objet in (self.m,self.p,self.a):PorteeObjet.objects.create(service=self.service,dossier=ds,modele=objet._meta.label_lower,identifiant=str(objet.pk),prise=self.a if objet==self.a else None)
        self.comp=self.declarer()

    def declarer(self,**kw):
        d=dict(debut=date(2026,1,1),reference=self.p,identifies=[self.p],complements=[{'categorie':'adulte','nombre':1,'age':None,'naissance':''},{'categorie':'enfant','nombre':2,'age':None,'naissance':''}],revenu=Decimal('1500'),devise='EUR')
        d.update(kw)
        self.a= m.Accompagnement.objects.select_related('menage').get(pk=self.a.pk)
        return c.renseigner(self.u,self.a,c.jeton(self.a),**d)

    def restaurer(self,**kw):
        self.a=m.Accompagnement.objects.select_related('menage').get(pk=self.a.pk)
        d=dict(debut=date(2026,1,10),fin_prevue=date(2026,1,13),dejeuner=True,diner=True,premier='diner',dernier='dejeuner')
        d.update(kw)
        return c.creer(self.u,self.a,'restauration',self.comp,c.jeton(self.a),[{'categorie':'adulte','nombre':2,'prix':Decimal('8')},{'categorie':'enfant','nombre':2,'prix':Decimal('5')}],**d)

    def test_resolution_collective_atomique(self):
        prestation = self.restaurer()
        self.a.fin = date(2026, 1, 15)
        self.a.save(update_fields=['fin'])
        self.a.refresh_from_db()
        confirme = self.a.fin, self.a.revision_sociale
        with self.assertRaises(ValidationError):
            c.modifier(self.u, prestation, c.jeton(prestation), 'correction',
                       fin_prevue=date(2026, 1, 18), dejeuner=False, diner=False,
                       prise_confirmee=confirme)
        self.a.refresh_from_db()
        self.assertEqual(self.a.fin, confirme[0])
        prestation.refresh_from_db()
        version = c.modifier(self.u, prestation, c.jeton(prestation), 'correction',
                             fin_prevue=date(2026, 1, 18), prise_confirmee=confirme)
        self.a.refresh_from_db()
        self.assertEqual(self.a.fin, version.fin_prevue + timedelta(days=1))

    def test_volumes_et_couts_sans_distribution(self):
        p=self.restaurer();r=c.bilan(p.courante,date(2026,1,10),date(2026,1,14))
        self.assertEqual((r['dejeuners'],r['diners'],r['repas'],r['cout']),(3,3,24,Decimal('156')))
        self.assertEqual(m.RepasDistribue.objects.count(),0)
        r=c.bilan(p.courante,date(2026,1,11),date(2026,1,12));self.assertEqual(r['repas'],8)

    def test_collectif_partiel_sans_identites_inventees(self):
        self.assertEqual(c.effectifs(self.comp),{'adulte':2,'enfant':2,'bas_age':0,'inconnu':0})
        self.assertEqual(self.comp.identifies.count(),1)
        self.assertEqual(m.Personne.objects.count(),1)

    def test_age_declare_non_actualise_et_naissance_calculee(self):
        comp=self.declarer(complements=[{'categorie':'inconnu','nombre':1,'age':17,'naissance':''},{'categorie':'inconnu','nombre':1,'age':None,'naissance':'2008-01-02'}])
        r=c.effectifs(comp,date(2026,1,2));self.assertEqual(r['inconnu'],1);self.assertEqual(r['adulte'],2)

    def test_correction_garde_composition_et_versions(self):
        p=self.restaurer();v=p.courante;ancien=v.composition_id
        self.declarer(complements=[])
        c.modifier(self.u,p,c.jeton(p),'prolongation',fin_prevue=date(2026,1,15))
        self.assertEqual(p.versions.count(),2);self.assertEqual(p.courante.composition_id,ancien)
        self.assertEqual(v.fin_prevue,date(2026,1,13))

    def test_double_confirmation_refusee(self):
        self.a.refresh_from_db();self.a.menage.refresh_from_db();token=c.jeton(self.a)
        self.restaurer()
        self.a=m.Accompagnement.objects.select_related('menage').get(pk=self.a.pk)
        with self.assertRaises(ValidationError):c.creer(self.u,self.a,'restauration',self.comp,token,[{'categorie':'adulte','nombre':1}],debut=date(2026,1,10))

    def test_annulation_historique_et_zero_bilan(self):
        p=self.restaurer();c.modifier(self.u,p,c.jeton(p),'annulation',motif='Doublon fictif')
        self.assertEqual(p.versions.count(),2);self.assertEqual(c.bilan(p.courante,date(2026,1,1),date(2026,2,1))['repas'],0)
        with self.assertRaises(ValidationError):c.modifier(self.u,p,c.jeton(p),'correction')

    def test_categories_refusent_recouvrement(self):
        cfg=defaut();cfg['categories'][0]['min']=17
        with self.assertRaises(ValidationError):verifier(cfg)

    def test_ancien_menage_non_remplace_par_composition_anterieure(self):
        self.declarer(debut=date(2026,2,1),actualiser=True)
        with self.assertRaises(ValidationError):self.declarer(debut=date(2026,1,1),actualiser=True)
        self.assertEqual(c.composition(self.m,date(2026,3,1)).debut,date(2026,2,1))

    def test_hebergement_un_groupe_un_lieu(self):
        self.a=m.Accompagnement.objects.select_related('menage').get(pk=self.a.pk)
        p=c.creer(self.u,self.a,'hebergement',self.comp,c.jeton(self.a),[],debut=date(2026,1,10),arrivee=date(2026,1,10),fin_prevue=date(2026,1,13),lieu=self.lieu)
        self.client.force_login(self.u)
        url = reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk])
        self.assertContains(self.client.get(url, {'sejour': p.pk}), 'Enregistrer le départ')
        c.mouvement(self.u,p,'absence',c.jeton(p),date(2026,1,11))
        p.refresh_from_db();absence=p.mouvements.get()
        c.reviser_mouvement(self.u,p,absence,c.jeton(p),date(2026,1,12))
        p.refresh_from_db();c.modifier(self.u,p,c.jeton(p),'depart',fin=date(2026,1,13),destination_sortie='Logement social')
        self.assertEqual(p.courante.destination_sortie, 'Logement social')
        self.assertEqual(c.bilan(p.courante,date(2026,1,10),date(2026,1,14))['nuits'],3)
        self.assertEqual(p.mouvements.count(),1)

    def test_droits_et_routes(self):
        self.client.force_login(self.u)
        url=reverse('dossiers:collectif_action',args=['prise',self.a.pk,'creation'])+'?nature=restauration'
        self.assertContains(self.client.get(url),'Couverts par repas')
        page=reverse('dossiers:prise',args=['menage',self.m.pk,self.a.pk])
        self.assertContains(self.client.get(page),'Nouvelle période de repas')
        self.assertContains(self.client.get(page+'?prestation=nouveau:commun_restauration'),'id="collectif-form"')
        self.u.user_permissions.clear();self.u=type(self.u).objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):self.restaurer()

    def test_prix_inconnu_pas_zero(self):
        p=self.restaurer();v=p.courante
        c.modifier(self.u,p,c.jeton(p),'correction',couverts=[{'categorie':'adulte','nombre':2,'prix':None}])
        self.assertTrue(c.bilan(p.courante,date(2026,1,10),date(2026,1,14))['prix_inconnus'])

    def test_composition_etrangere_refusee(self):
        autre=m.Menage.objects.create(libelle='Autre fictif',cree_par=self.u)
        self.comp.menage=autre;self.comp.save()
        with self.assertRaises(ValidationError):self.restaurer()

    def test_formulaire_composition_reference_sans_liste_cachee(self):
        from .forms_collectifs import CompositionForm
        self.a=m.Accompagnement.objects.select_related('menage').get(pk=self.a.pk)
        form=CompositionForm({'debut':'2026-01-02','reference':str(self.p.pk),'devise':'EUR',
            'nombre_adulte':'1','nombre_enfant':'2','nombre_bas_age':'0','nombre_inconnu':'0',
            'attendu':c.jeton(self.a)},objet=self.a,jour=date(2026,1,2))
        self.assertTrue(form.is_valid(),form.errors)
        comp=c.renseigner(self.u,self.a,**form.cleaned_data)
        self.assertEqual(comp.identifies.count(),1)

    def test_sous_groupe_possible_en_mode_collectif(self):
        self.a=m.Accompagnement.objects.select_related('menage').get(pk=self.a.pk)
        p=c.creer(self.u,self.a,'hebergement',self.comp,c.jeton(self.a),[],selection=[],selection_complements={'enfant':1},debut=date(2026,1,10))
        self.assertEqual(sum(c.effectifs(p.courante.composition).values()),1)
        self.assertEqual(p.courante.composition.reference,self.p)
        self.assertEqual(p.courante.composition.identifies.count(),0)

    def test_selection_facultative_ne_change_pas_la_composition_courante(self):
        self.service.profil_collectif['hebergement']='option';self.service.save()
        self.a=m.Accompagnement.objects.select_related('menage').get(pk=self.a.pk)
        p=c.creer(self.u,self.a,'hebergement',self.comp,c.jeton(self.a),[],selection=[self.p],reference_selection=self.p,debut=date(2026,1,10))
        self.assertTrue(p.courante.composition.pour_prestation)
        self.assertEqual(c.composition(self.a,date(2026,1,12)).pk,self.comp.pk)

    def test_portees_actives_refusent_un_autre_service(self):
        from acteurs.models import LienCompteProfessionnel,AppartenanceProfessionnelle,Habilitation,ConfigurationAcces
        from acteurs.contexte import perimetre
        from django.contrib.auth import get_user_model
        prof=m.Intervenant.objects.create(libelle='Professionnel fictif',cree_par=self.u)
        LienCompteProfessionnel.objects.create(compte=self.u,professionnel=prof)
        AppartenanceProfessionnelle.objects.create(service=self.service,professionnel=prof,debut=date(2020,1,1))
        Habilitation.objects.create(compte=self.u,service=self.service,tache='social',debut=date(2020,1,1),accorde_par=self.u)
        # L'initialisation précédente a été faite hors contrôle, comme une reprise exacte.
        for obj in [self.comp,*m.JournalCollectif.objects.all()]:
            origine=PorteeObjet.objects.get(modele=self.a._meta.label_lower,identifiant=str(self.a.pk))
            PorteeObjet.objects.create(modele=obj._meta.label_lower,identifiant=str(obj.pk),service=self.service,dossier=origine.dossier,prise=self.a)
        ConfigurationAcces.objects.update_or_create(pk=1,defaults={'active':True})
        with perimetre(self.u,service=self.service):
            self.a=m.Accompagnement.objects.select_related('menage').get(pk=self.a.pk)
            p=self.restaurer();self.assertIsNotNone(p.courante)
        autre=get_user_model().objects.create_user('autre-service-fictif')
        autre.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes'))
        with perimetre(autre):self.assertFalse(m.PrestationCollective.objects.filter(pk=p.pk).exists())
