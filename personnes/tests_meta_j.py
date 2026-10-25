"""Paramétrage indépendant et préparation volontaire des petits-déjeuners."""
import copy
from datetime import date
from io import StringIO
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError,PermissionDenied
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from . import models as m,parametrage as s,partenaires,intervenants,hebergement as h,aides,financements as f,bd6,suivi,preparation_repas as pr,famille,repas

D=date(2026,1,1)
class ParametrageTests(TestCase):
    def setUp(self):
        self.u=get_user_model().objects.create_user('parametrage-fictif')
        for c in ('autoriser_chrs7','autoriser_solenne'):call_command(c,self.u.username,stdout=StringIO())
        self.org=partenaires.creer(self.u,D,'Source fictive',partenaires.jeton_creation(),nom='Organisme fictif J',rue='Rue fictive',code_postal='00100',ville='Ville fictive',pays='',telephone='+33 1 00 00 00 00',courriel='contact@example.invalid',fax='',informations='Fictif')
        self.prof=intervenants.creer(self.u,D,'Source fictive',intervenants.jeton_creation(),nom='Professionnel fictif J',fonction='Accompagnement',organisme=self.org,telephone='',courriel='',fax='')
        self.parent=h.creer_lieu(self.u,'Établissement fictif J',organisme=self.org,niveau='etablissement')
        self.chambre=h.creer_lieu(self.u,'Chambre fictive J',parent=self.parent,niveau='chambre')
        self.type=aides.cataloguer(self.u,aides.jeton_catalogue(),'Catalogue fictif',nature='transport',libelle='Carte fictive J',unite='carte',fractionnable=False,precision='Trois voyages par carte',actif=True)
        d=dict(debut=D,fin=None,libelle='Tarif fictif J',unite='chambre-nuit',categorie='',montant='12.3456',devise='EUR',prestataire=self.org,actif=True,source='Convention fictive')
        self.tarif=f.definir_tarif(self.u,f.creation_tarif(),'Définition fictive',**d)
        d.update(montant='13.0000',debut=date(2026,2,1));f.definir_tarif(self.u,bd6.jeton(self.tarif),'Nouveau prix fictif',action='changement',tarif=self.tarif,**d)
        self.x=s.exporter(self.u);self.client.force_login(self.u)
    def test_export_ferme_et_prix_exacts_sans_metier(self):
        self.assertEqual(set(self.x),set(('format',*s.FAMILLES)))
        self.assertEqual(self.x['tarifs'][0]['versions'][0]['montant'],'12.3456')
        for interdit in ('Personne','Menage','password','permissions','session'):self.assertNotIn(interdit,s.serialiser(self.x))
        self.assertEqual(len(self.x['tarifs'][0]['versions']),2)
    def test_apercu_sans_ecriture_confirmation_et_dependances_recreees(self):
        token,conflits=s.preparer(self.u,self.x);self.assertTrue(conflits)
        self.assertEqual(m.Partenaire.objects.count(),1);self.assertFalse(m.ImportParametrage.objects.exists())
        with self.assertRaises(ValidationError):s.confirmer(self.u,token,'Import fictif')
        self.assertFalse(m.ImportParametrage.objects.exists())
        j=s.confirmer(self.u,token,'Import fictif',True)
        nouveau=m.Partenaire.objects.get(pk=j.correspondances['organismes'][str(self.org.pk)])
        self.assertNotEqual(nouveau.pk,self.org.pk);self.assertEqual(nouveau.fiches.get().code_postal,'00100')
        prof=m.Intervenant.objects.get(pk=j.correspondances['professionnels'][str(self.prof.pk)])
        self.assertEqual(prof.fiches.get().organisme,nouveau)
        lieu=m.LieuHebergement.objects.get(pk=j.correspondances['lieux'][str(self.chambre.pk)])
        self.assertEqual(lieu.parent.organisme,nouveau)
        tarif=m.TarifPrestation.objects.get(pk=j.correspondances['tarifs'][str(self.tarif.pk)])
        self.assertEqual(tarif.versions.count(),2);self.assertEqual(str(tarif.versions.last().montant),'12.3456')
        self.assertEqual(self.org.fiches.count(),1);self.assertFalse(m.Personne.objects.exists())
        with self.assertRaises(ValidationError):s.confirmer(self.u,token,'Rejeu fictif',True)
        with self.assertRaises(ValidationError):s.preparer(self.u,self.x)
    def test_schema_types_email_references_et_cycles(self):
        cas=[]
        x=copy.deepcopy(self.x);x['personnes']=[];cas.append(x)
        x=copy.deepcopy(self.x);x['organismes'][0]['versions'][0]['courriel']='invalide';cas.append(x)
        x=copy.deepcopy(self.x);x['professionnels'][0]['versions'][0]['organisme']='absent';cas.append(x)
        x=copy.deepcopy(self.x);x['lieux'][0]['valeurs']['parent']=x['lieux'][0]['ref'];cas.append(x)
        x=copy.deepcopy(self.x);x['types_aide'][0]['valeurs']['actif']='false';cas.append(x)
        x=copy.deepcopy(self.x);x['tarifs'][0]['versions'][0]['montant']=12.34;cas.append(x)
        for x in cas:
            with self.subTest(x=x),self.assertRaises(ValidationError):s.decoder(s.serialiser(x).encode())
        for data in (b'{"format":1,"format":2}',b'[]',b'\xff',b'"\\ud800"',b' '*1_000_001):
            with self.subTest(data=data[:30]),self.assertRaises(ValidationError):s.decoder(data)
    def test_rollback_si_service_refuse_apres_creation_des_dependances(self):
        from unittest.mock import patch
        token,_=s.preparer(self.u,self.x)
        with patch('personnes.parametrage.aides.cataloguer',side_effect=ValidationError('Refus fictif')):
            with self.assertRaises(ValidationError):s.confirmer(self.u,token,'Import fictif',True)
        self.assertEqual(m.Partenaire.objects.count(),1);self.assertEqual(m.Intervenant.objects.count(),1)
        self.assertEqual(m.LieuHebergement.objects.count(),2);self.assertFalse(m.ImportParametrage.objects.exists())
    def test_apercu_perime_et_signature_et_droits(self):
        token,_=s.preparer(self.u,self.x);m.Partenaire.objects.filter(pk=self.org.pk).update(libelle='Autre nom fictif')
        with self.assertRaises(ValidationError):s.confirmer(self.u,token,'Import fictif',True)
        with self.assertRaises(ValidationError):s.confirmer(self.u,token+'x','Import fictif',True)
        autre=get_user_model().objects.create_user('sans-droits-j')
        for fn in (lambda:s.exporter(autre),lambda:s.preparer(autre,self.x),lambda:s.confirmer(autre,token,'Import fictif',True)):
            with self.assertRaises(PermissionDenied):fn()
    def test_http_fichier_prive_apercu_confirmation_et_recu(self):
        url=reverse('dossiers:parametrage');r=self.client.get(url+'?format=json')
        self.assertEqual(r.status_code,200);self.assertIn('no-store',r['Cache-Control'])
        r=self.client.post(url,{'action':'preparer','fichier':SimpleUploadedFile('catalogue.json',s.serialiser(self.x).encode())})
        self.assertContains(r,'Entrées à créer');self.assertFalse(m.ImportParametrage.objects.exists())
        token=r.context['confirmation'].initial['attendu']
        r=self.client.post(url,dict(action='confirmer',attendu=token,motif='Import fictif',accepter_homonymes='on',confirmer='on'))
        self.assertEqual(r.status_code,302);self.assertContains(self.client.get(r.url),'Import fictif')
    def test_repertoires_anciens_sans_fiche_non_inventee(self):
        p=m.Partenaire.objects.create(libelle='Ancien libellé fictif',cree_par=self.u)
        x=s.exporter(self.u);token,_=s.preparer(self.u,x);j=s.confirmer(self.u,token,'Import fictif',True)
        nouveau=m.Partenaire.objects.get(pk=j.correspondances['organismes'][str(p.pk)])
        self.assertFalse(nouveau.fiches.exists());self.assertEqual(nouveau.libelle,p.libelle)

class PreparationRepasTests(TestCase):
    def setUp(self):
        self.u=get_user_model().objects.create_user('preparation-fictive')
        for c in ('autoriser_chrs7','autoriser_solenne'):call_command(c,self.u.username,stdout=StringIO())
        self.ps=[m.Personne.objects.create(designation='Personne fictive '+str(i),cree_par=self.u,precision_naissance='exacte' if an else '',date_naissance=date(an,1,1) if an else None) for i,an in enumerate((2024,2023,2014,2013,1990,None))]
        menage=suivi.creer_menage(self.u,'Ménage fictif petit-déjeuner',self.ps,D)
        self.a=suivi.ouvrir(self.u,menage,self.ps,D);self.client.force_login(self.u)
    def test_age_borne_exclue_incluse_inconnu_et_tous(self):
        ps,inconnus=pr.proposer(self.u,self.a,D,'age',2,12)
        self.assertEqual(set(ps),set(self.ps[1:3]));self.assertIn(self.ps[-1],inconnus)
        self.assertEqual(set(pr.proposer(self.u,self.a,D,'tous')[0]),set(self.ps))
        self.assertFalse(m.AccordRepas.objects.exists());self.assertFalse(m.RepasDistribue.objects.exists())
    def test_grossesse_datee_sans_doubler_une_personne_et_droits(self):
        p=self.ps[2]
        for p in (self.ps[2],self.ps[4]):famille.renseigner(self.u,p,D,'Déclaration fictive',bd6.jeton(p),situation_familiale='',rapports_parentaux='',fratrie='',enfants_a_charge=None,enfants_non_a_charge=None,grossesse=True)
        ps,_=pr.proposer(self.u,self.a,D,'age_grossesse',2,12)
        self.assertEqual(len(ps),3);self.assertIn(self.ps[4],ps)
        self.assertNotIn(self.ps[4],pr.proposer(self.u,self.a,date(2025,12,31),'age_grossesse',2,12)[0])
        from django.contrib.auth.models import Permission
        self.u.user_permissions.remove(Permission.objects.get(content_type__app_label='personnes',codename='view_declarationfamiliale'))
        u=get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):pr.proposer(u,self.a,D,'age_grossesse',2,12)
    def donnees(self):return dict(accompagnement=str(self.a.pk),debut='2026-01-01',fin='',services=['dejeuner','diner'],beneficiaires=[str(p.pk) for p in self.ps],attendu=repas.jeton_services(self.a),regle_petit_dejeuner='age',age_min_petit_dejeuner='2',age_max_petit_dejeuner='12',action='proposer_petit_dejeuner')
    def test_bd_proposition_seule_puis_confirmation_sans_perte_selection(self):
        url=reverse('dossiers:nouveau',args=['menage',self.a.menage_id,'services_repas'])
        d=self.donnees();r=self.client.post(url,d)
        self.assertEqual(r.status_code,200);self.assertFalse(m.AccordRepas.objects.exists())
        self.assertContains(r,'Aucun accord ni repas distribué')
        self.assertEqual(r.context['form'].data.getlist('services'),['petit_dejeuner'])
        self.assertEqual(set(r.context['form'].data.getlist('beneficiaires')),{str(p.pk) for p in self.ps[1:3]})
        d=r.context['form'].data.copy();d.pop('action');r=self.client.post(url,dict(d.lists()))
        self.assertEqual(r.status_code,302)
        a=m.AccordRepas.objects.get();self.assertEqual(a.service,'petit_dejeuner');self.assertEqual(set(a.beneficiaires.all()),set(self.ps[1:3]))
        self.assertFalse(m.RepasDistribue.objects.exists())
    def test_ancien_formulaire_necrit_pas_pendant_proposition(self):
        url=reverse('suivi:accorder_services_repas',args=[self.a.pk])
        r=self.client.post(url,self.donnees());self.assertEqual(r.status_code,200)
        self.assertFalse(m.AccordRepas.objects.exists());self.assertContains(r,'Proposition pour le petit-déjeuner')

from django.test import TransactionTestCase
class ParametrageTransactions(TransactionTestCase):
    setUp=ParametrageTests.setUp
    def test_deux_confirmations_ne_dupliquent_pas_le_catalogue(self):
        from threading import Thread,Barrier
        from django.db import connections,OperationalError
        token,_=s.preparer(self.u,self.x);barriere=Barrier(2);resultats=[];erreurs=[]
        def executer():
            try:
                u=get_user_model().objects.get(pk=self.u.pk);u.has_perms(['personnes.add_importparametrage'])
                barriere.wait(timeout=10)
                try:s.confirmer(u,token,'Import fictif concurrent',True);resultats.append(True)
                except (ValidationError,OperationalError):resultats.append(False)
            except Exception as e:erreurs.append(repr(e))
            finally:connections.close_all()
        ts=[Thread(target=executer) for _ in range(2)]
        for t in ts:t.start()
        for t in ts:t.join(20)
        self.assertFalse(any(t.is_alive() for t in ts));self.assertFalse(erreurs,erreurs)
        self.assertEqual(sum(resultats),1,resultats)
        self.assertEqual(m.ImportParametrage.objects.count(),1);self.assertEqual(m.Partenaire.objects.count(),2)
    def test_copie_sqlite_conserve_recu_et_liaisons(self):
        import sqlite3,tempfile,json
        from contextlib import closing
        from pathlib import Path
        from django.db import connection
        if connection.vendor!='sqlite':self.skipTest('Recette SQLite')
        token,_=s.preparer(self.u,self.x);j=s.confirmer(self.u,token,'Import fictif',True)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'copie.sqlite3'
            with closing(sqlite3.connect(path)) as db,db:connection.connection.backup(db)
            with closing(sqlite3.connect(path)) as db,db:
                ligne=db.execute('SELECT empreinte,correspondances FROM personnes_importparametrage').fetchone()
                self.assertEqual(ligne[0],j.empreinte);self.assertEqual(json.loads(ligne[1]),j.correspondances)
                self.assertEqual(db.execute('SELECT count(*) FROM personnes_versiontarif').fetchone()[0],4)
            with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
