from datetime import date
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError,PermissionDenied
from django.core.management import call_command
from django.test import TestCase,TransactionTestCase,Client
from django.urls import reverse
from . import bd6,complements_identite as ci,relations_personnelles as liens
from .models import Personne,ComplementIdentite,RevisionComplementIdentite,RelationPersonnelle,RevisionRelationPersonnelle,Appartenance,Accompagnement


def valeurs(**kw):
    v=dict(sexe_declare='Non précisé',naissance_lieu='Lieu fictif',naissance_ville='Ville fictive',naissance_pays='Pays fictif',nationalites=['Nationalité fictive A'],apatridie_declaree=None)
    v.update(kw);return v


class IdentiteLiensTests(TestCase):
    def setUp(self):
        self.u=get_user_model().objects.create_user('relations-fictives')
        call_command('autoriser_solenne',self.u.username,stdout=StringIO())
        self.u.user_permissions.add(Permission.objects.get(codename='view_personne'))
        self.u=get_user_model().objects.get(pk=self.u.pk);self.client.force_login(self.u)
        self.p=Personne.objects.create(designation='Première personne fictive',cree_par=self.u)
        self.q=Personne.objects.create(designation='Autre personne fictive',cree_par=self.u)

    def rel(self,**kw):
        v=dict(autre=self.q,debut=date(2026,1,1),fin=None,role='parent',precision='',source='Entretien fictif',attendu=bd6.jeton(self.p));v.update(kw)
        return liens.enregistrer(self.u,self.p,**v)

    def identite(self,d,**kw):
        return ci.renseigner(self.u,self.p,d,'Entretien fictif',bd6.jeton(self.p),**kw)

    def test_identite_multinationale_historique_correction_et_inconnus(self):
        self.identite(date(2026,1,1),**valeurs())
        x=self.identite(date(2026,3,1),**valeurs(nationalites=['Nationalité fictive A','Nationalité fictive B']))
        ci.renseigner(self.u,self.p,date(2026,2,1),'Document fictif',bd6.jeton(self.p),correction=x.pk,motif='Date erronée fictive',**valeurs(nationalites=[],apatridie_declaree=True))
        self.assertEqual(ci.a_date([self.p],date(2026,1,31)).get().nationalites,['Nationalité fictive A'])
        self.assertTrue(ci.a_date([self.p],date(2026,2,1)).get().apatridie_declaree)
        self.assertEqual(RevisionComplementIdentite.objects.first().avant[-1]['nationalites'],['Nationalité fictive A','Nationalité fictive B'])
        self.assertFalse(ci.a_date([self.q],date(2026,1,1)).exists())

    def test_identite_refus_doublon_contradiction_et_rollback(self):
        for v in (valeurs(nationalites=['A',' a ']),valeurs(nationalites='A,B'),valeurs(apatridie_declaree=True),valeurs(nationalites=[''])):
            with self.assertRaises(ValidationError):self.identite(date(2026,1,1),**v)
        self.assertFalse(ComplementIdentite.objects.exists())
        with patch.object(RevisionComplementIdentite.objects,'create',side_effect=RuntimeError('Fictif')):
            with self.assertRaises(RuntimeError):self.identite(date(2026,1,1),**valeurs())
        self.assertFalse(ComplementIdentite.objects.exists())

    def test_relations_dans_les_deux_sens_sans_liens_de_menage_ni_comptes(self):
        x=self.rel()
        self.assertEqual(x.role_depuis(self.p),'parent');self.assertEqual(x.role_depuis(self.q),'enfant')
        self.assertEqual(liens.a_date(self.q,date(2026,1,2)).get(),x)
        self.assertFalse(Appartenance.objects.exists());self.assertFalse(Accompagnement.objects.exists())
        self.assertEqual(get_user_model().objects.count(),1)
        with self.assertRaises(ValidationError):
            liens.enregistrer(self.u,self.q,self.p,x.debut,None,'enfant','','Fictif',bd6.jeton(self.q))
        self.assertEqual(RelationPersonnelle.objects.count(),1)

    def test_parent_inverse_self_lien_etranger_et_dates_refuses(self):
        x=self.rel()
        for d in [dict(role='enfant'),dict(autre=self.p),dict(debut=date(9999,1,1)),dict(fin=date(2025,12,31)),dict(role='representant_legal')]:
            with self.assertRaises(ValidationError):self.rel(**d)
        r=Personne.objects.create(designation='Troisième personne fictive',cree_par=self.u)
        with self.assertRaises(ValidationError):self.rel(autre=r,correction=x.pk,motif='Fictif')
        self.assertEqual(RelationPersonnelle.objects.count(),1)

    def test_changement_fin_correction_annulation_et_formulaire_perime(self):
        x=self.rel(role='couple');ancien=bd6.jeton(self.p)
        y=self.rel(role='proche',debut=date(2026,2,1),remplace=x.pk)
        x.refresh_from_db();self.assertEqual(x.fin,date(2026,2,1))
        self.assertEqual(liens.a_date(self.p,date(2026,2,1)).get(),y)
        with self.assertRaises(ValidationError):self.rel(attendu=ancien)
        self.rel(role='proche',debut=y.debut,fin=date(2026,3,1),correction=y.pk,cloture=True,motif='Fin du lien fictive')
        y.refresh_from_db();self.assertEqual(y.fin,date(2026,3,1))
        self.rel(role='proche',debut=y.debut,fin=date(2026,2,20),correction=y.pk,motif='Fin saisie trop tard fictive')
        liens.annuler(self.u,self.p,y,'Mauvaise personne fictive',bd6.jeton(self.p))
        self.assertFalse(liens.a_date(self.q,date(2026,2,15)).exists())
        self.assertEqual(list(RevisionRelationPersonnelle.objects.values_list('action',flat=True))[:4],['annulation','correction','cloture','changement'])

    def test_rollback_et_jeton_de_l_autre_personne_invalide(self):
        jeton_q=bd6.jeton(self.q)
        with patch.object(RevisionRelationPersonnelle.objects,'create',side_effect=RuntimeError('Fictif')):
            with self.assertRaises(RuntimeError):self.rel()
        self.assertFalse(RelationPersonnelle.objects.exists());self.q.refresh_from_db();self.assertEqual(bd6.revision(self.q),0)
        self.rel()
        with self.assertRaises(ValidationError):liens.enregistrer(self.u,self.q,self.p,date(2026,1,1),None,'proche','','Fictif',jeton_q)

    def test_html_formulaire_nationalites_et_csv_exact(self):
        url=reverse('dossiers:complements_identite_nouveaux',args=[self.p.pk])
        f=self.client.get(url).context['form']
        d=dict(valeurs(),debut='2026-01-01',source='Fictif',attendu=f.initial['attendu'],nationalites='Fictive A\nFictive B',apatridie_declaree='unknown')
        r=self.client.post(url,d);self.assertEqual(r.status_code,302,r.content)
        self.assertEqual(self.p.complements_identite.get().nationalites,['Fictive A','Fictive B'])
        self.assertContains(self.client.get(reverse('dossiers:complements_identite',args=[self.p.pk])),'Fictive B')
        report=reverse('dossiers:rapport_complements_identite')
        page=self.client.get(report,{'date':'2026-01-02','nationalite':'fictive b'})
        self.assertEqual(page.context['nombre'],1)
        self.assertEqual(self.client.get(report,{'date':'2026-01-02','ville':'ville fictive','lieu':'lieu fictif','apatridie':'inconnue'}).context['nombre'],1)
        self.assertEqual(self.client.get(report,{'date':'2026-01-02','apatridie':'oui'}).context['nombre'],0)
        csv=self.client.get(report,{'date':'2026-01-02','nationalite':'fictive b','format':'csv'})
        self.assertIn('Fictive A',csv.content.decode());self.assertNotIn(str(self.q.pk),csv.content.decode())

    def test_http_relations_dates_retours_erreurs_et_csrf(self):
        url=reverse('dossiers:relation_nouvelle',args=[self.p.pk]);f=self.client.get(url).context['form']
        d=dict(autre=self.q.pk,debut='2026-01-01',fin='',role='parent',precision='Déclaration fictive',source='Fictif',attendu=f.initial['attendu'])
        protege=Client(enforce_csrf_checks=True);protege.force_login(self.u);self.assertEqual(protege.post(url,d).status_code,403)
        self.assertEqual(self.client.post(url,d).status_code,302)
        self.assertContains(self.client.get(reverse('dossiers:relations_personnelles',args=[self.q.pk])),'Enfant déclaré de')
        self.assertContains(self.client.get(reverse('dossiers:relations_personnelles',args=[self.p.pk])),'Parent déclaré de')
        rapport=reverse('dossiers:rapport_relations')
        self.assertEqual(self.client.get(rapport,{'date':'2026-01-02','nature':'parent'}).context['nombre'],1)
        self.assertIn(str(self.p.pk),self.client.get(rapport,{'date':'2026-01-02','nature':'parent','format':'csv'}).content.decode())

    def test_droits_independants(self):
        self.u.user_permissions.remove(Permission.objects.get(codename='view_relationpersonnelle'))
        self.assertEqual(self.client.get(reverse('dossiers:relations_personnelles',args=[self.p.pk])).status_code,403)
        with self.assertRaises(PermissionDenied):self.rel()
        self.assertEqual(self.client.get(reverse('dossiers:complements_identite',args=[self.p.pk])).status_code,200)

    def test_insertion_anterieure_et_changement_invalide_atomiques(self):
        x=self.rel(debut=date(2026,3,1),role='proche')
        with self.assertRaises(ValidationError):self.rel(role='proche',fin=date(2026,2,1))
        ancien=self.rel(role='proche',fin=date(2026,2,1),motif='Fait ancien fictif oublié')
        self.assertEqual(RevisionRelationPersonnelle.objects.first().action,'insertion')
        self.rel(role='couple',debut=date(2026,2,1))
        revision=bd6.revision(self.p)
        with self.assertRaises(ValidationError):self.rel(role='couple',debut=date(2026,4,1),remplace=x.pk)
        x.refresh_from_db();self.p.refresh_from_db()
        self.assertIsNone(x.fin);self.assertEqual(bd6.revision(self.p),revision)

    def test_http_annulation_et_droit_sans_droit_de_creation(self):
        x=self.rel()
        self.u.user_permissions.remove(Permission.objects.get(codename='add_relationpersonnelle'))
        url=reverse('dossiers:relation_annuler',args=[self.q.pk,x.pk])
        page=self.client.get(url);self.assertEqual(page.status_code,200)
        token=page.context['form'].fields['attendu'].initial
        self.assertEqual(self.client.post(url,{'attendu':token,'motif':'Mauvais homonyme fictif'}).status_code,302)
        self.assertFalse(liens.a_date(self.p,date(2026,1,2)).exists())
        self.assertEqual(self.client.get(reverse('dossiers:rapport_relations'),{'date':'invalide','format':'csv'})['Content-Type'],'text/html; charset=utf-8')

    def test_fiche_pdf_respecte_les_droits_sur_les_complements(self):
        self.identite(date(2026,1,1),**valeurs())
        url=reverse('personnes:fiche_pdf',args=[self.p.pk])
        with patch('personnes.pdf.produire',return_value=b'%PDF-fictif') as produire:
            self.assertEqual(self.client.get(url).status_code,200)
            self.assertIsNotNone(produire.call_args.kwargs['complement'])
        self.u.user_permissions.remove(Permission.objects.get(codename='view_complementidentite'))
        with patch('personnes.pdf.produire',return_value=b'%PDF-fictif') as produire:
            self.assertEqual(self.client.get(url).status_code,200)
            self.assertIsNone(produire.call_args.kwargs['complement'])

    def test_resume_bd_entree_droits_et_retour_conserve(self):
        from . import suivi
        call_command('autoriser_chrs7',self.u.username,stdout=StringIO())
        self.u=get_user_model().objects.get(pk=self.u.pk);self.client.force_login(self.u)
        menage=suivi.creer_menage(self.u,'Ménage fictif',[self.p],date(2026,1,1))
        a=suivi.ouvrir(self.u,menage,[self.p],date(2026,1,1))
        self.identite(date(2026,1,1),**valeurs())
        self.identite(date(2026,2,1),**valeurs(nationalites=['Nationalité fictive B']))
        self.rel()
        page=self.client.get(reverse('dossiers:prise',args=['menage',menage.pk,a.pk]))
        self.assertContains(page,'Compléments et historique');self.assertContains(page,'Consulter et mettre à jour')
        resume=self.client.get(reverse('suivi:resume',args=[a.pk]))
        self.assertContains(resume,'Nationalité fictive A');self.assertNotContains(resume,'Nationalité fictive B')
        self.assertContains(resume,'Parent déclaré de')
        d={'depuis_nature':'menage','depuis_pk':menage.pk,'depuis_prise':a.pk,'q':'Recherche fictive','page':'2','date':'2026-01-02'}
        page=self.client.get(reverse('dossiers:relations_personnelles',args=[self.p.pk]),d)
        self.assertIn(reverse('dossiers:prise',args=['menage',menage.pk,a.pk]),page.context['retour'])
        self.assertIn('Recherche+fictive',page.context['retour']);self.assertIn('page=2',page.context['retour'])
        self.u.user_permissions.remove(Permission.objects.get(codename='view_relationpersonnelle'))
        page=self.client.get(reverse('dossiers:prise',args=['menage',menage.pk,a.pk]))
        self.assertNotContains(page,'Liens personnels :')


class ConcurrenceEtCopieRelationsTests(TransactionTestCase):
    def preparer(self):
        self.u=get_user_model().objects.create_user('paire-concurrente')
        call_command('autoriser_solenne',self.u.username,stdout=StringIO())
        self.u.user_permissions.add(Permission.objects.get(codename='view_personne'))
        self.u=get_user_model().objects.get(pk=self.u.pk)
        self.p=Personne.objects.create(designation='Parent fictif',cree_par=self.u)
        self.q=Personne.objects.create(designation='Enfant fictif',cree_par=self.u)

    def test_deux_dossiers_opposes_une_seule_relation(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections,connections,OperationalError
        self.preparer();depart=Barrier(2);tokens=[bd6.jeton(self.p),bd6.jeton(self.q)]
        def ecrire(i):
            close_old_connections()
            try:
                acteur=get_user_model().objects.get(pk=self.u.pk);acteur.get_all_permissions()
                p=Personne.objects.get(pk=self.p.pk);q=Personne.objects.get(pk=self.q.pk)
                p,q=(p,q) if i==0 else (q,p);depart.wait(timeout=10)
                try:
                    liens.enregistrer(acteur,p,q,date(2026,1,1),None,'parent' if i==0 else 'enfant','','Fictif',tokens[i])
                    return True
                except (ValidationError,OperationalError):return False
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:r=list(pool.map(ecrire,range(2)))
        self.assertEqual(sum(r),1,r);self.assertEqual(RelationPersonnelle.objects.count(),1)
        self.assertEqual(RevisionRelationPersonnelle.objects.count(),1)

    def test_copie_restauree_identite_multiple_et_annulation(self):
        import sqlite3
        from contextlib import closing
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.db import connection
        from pas_communs.paquets import creer_sauvegarde
        from pas_a_pas_accompagnement import paquets
        if connection.vendor!='sqlite':self.skipTest('Copie locale SQLite uniquement.')
        self.preparer()
        ci.renseigner(self.u,self.p,date(2026,1,1),'Fictif',bd6.jeton(self.p),**valeurs(nationalites=['Fictive A','Fictive B']))
        x=liens.enregistrer(self.u,self.p,self.q,date(2026,1,1),None,'parent','','Fictif',bd6.jeton(self.p))
        liens.annuler(self.u,self.p,x,'Mauvais homonyme fictif',bd6.jeton(self.p))
        with TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir();(source/'secret-key').write_text('cle-fictive-relations')
            with closing(sqlite3.connect(source/paquets.PROFIL.base)) as copie:connection.connection.backup(copie)
            archive=root/'copie.zip';creer_sauvegarde(source,archive,profil=paquets.PROFIL)
            preparation=paquets.verifier(archive,root,'preparation');destination=root/'restauree';paquets.installer_copie(preparation,destination)
            with closing(sqlite3.connect(destination/paquets.PROFIL.base)) as db:
                import json
                self.assertEqual(json.loads(db.execute('SELECT nationalites FROM personnes_complementidentite').fetchone()[0]),['Fictive A','Fictive B'])
                self.assertEqual(db.execute('SELECT motif_annulation FROM personnes_relationpersonnelle').fetchone(),('Mauvais homonyme fictif',))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM personnes_revisionrelationpersonnelle').fetchone(),(2,))
