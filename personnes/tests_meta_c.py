from contextlib import closing
from datetime import date
from decimal import Decimal as D
from io import StringIO
from unittest.mock import patch
import csv
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError,PermissionDenied
from django.core.management import call_command
from django.test import TestCase,TransactionTestCase,Client
from django.urls import reverse
from . import models as m,bd6,aides as s,suivi,hebergement as h,statistiques,continuite_hebergement as ch,correction_repas,repas


def autoriser(u):
    call_command('autoriser_chrs7',u.username,stdout=StringIO());call_command('autoriser_solenne',u.username,stdout=StringIO())
    return get_user_model().objects.get(pk=u.pk)


class MetaCTests(TestCase):
    def setUp(self):
        self.u=autoriser(get_user_model().objects.create_user('meta-c-fictif'))
        self.p=m.Personne.objects.create(designation='Personne fictive C',cree_par=self.u)
        self.p2=m.Personne.objects.create(designation='Autre personne fictive C',cree_par=self.u)
        self.m=suivi.creer_menage(self.u,'Ménage fictif C',[self.p,self.p2],date(2026,1,1))
        self.a=suivi.ouvrir(self.u,self.m,[self.p,self.p2],date(2026,1,1))
        self.type=self.type_creer()
        self.client.force_login(self.u)
    def type_creer(self,**kw):
        d=dict(nature='transport',libelle='Carte fictive de trois voyages',unite='carte',fractionnable=False,precision='Titre, sans preuve de voyage',actif=True);d.update(kw)
        return s.cataloguer(self.u,s.jeton_catalogue(),'Définition fictive',**d)
    def accorder(self,**kw):
        d=dict(debut=date(2026,1,1),fin=date(2026,2,1),quantite=D('5'),prestataire=None,financeur=None,valeur_bon=None,devise='EUR',source='Décision fictive');d.update(kw)
        return s.accorder(self.u,self.a,self.type,[self.p,self.p2],bd6.jeton(self.a),**d)
    def remettre(self,a,**kw):
        d=dict(beneficiaires=[self.p,self.p2],date=date(2026,1,5),quantite=D('2'),source='Remise fictive',attendu=bd6.jeton(a));d.update(kw)
        return s.remettre(self.u,a,**d)
    def test_autoriser_n_est_pas_remettre_et_quantite_collective_unique(self):
        a=self.accorder();self.assertFalse(a.remises.exists());self.remettre(a)
        self.assertEqual(s.total(a),2);self.assertEqual(a.remises.get().beneficiaires.count(),2)
        self.assertEqual(a.unite,'carte');self.assertFalse(m.Sejour.objects.exists())
        with self.assertRaises(ValidationError):self.remettre(a,quantite=D('4'))
        self.assertEqual(a.remises.count(),1)
    def test_fractions_unites_inconnus_et_zero_faciale(self):
        a=self.accorder(quantite=None)
        with self.assertRaises(ValidationError):self.remettre(a,quantite=D('0.5'))
        self.type=self.type_creer(nature='produits',unite='kg',fractionnable=True)
        a=self.accorder();self.remettre(a,quantite=D('0.001'));self.assertEqual(s.total(a),D('0.001'))
        from .presentation_dossier_complet import valeur
        self.assertEqual(valeur(m.RemiseAide._meta.get_field('quantite'),D('0.001')),'0,001')
        self.type=self.type_creer(nature='bon_alimentaire',unite='bon')
        a=self.accorder(valeur_bon=D('0'));self.assertEqual(a.valeur_bon,0)
        with self.assertRaises(ValidationError):self.accorder(quantite=0)
    def test_catalogue_ne_reecrit_pas_unite_accord_et_rejeu_refuse(self):
        a=self.accorder();token=s.jeton_catalogue();d={c:getattr(self.type,c) for c in s.CATALOGUE}
        x=s.cataloguer(self.u,token,'Création fictive',**d)
        with self.assertRaises(ValidationError):s.cataloguer(self.u,token,'Rejeu fictif',**d)
        d['unite']='titre';s.cataloguer(self.u,bd6.jeton(self.type),'Unité précisée',objet=self.type,**d)
        a.refresh_from_db();self.assertEqual(a.unite,'carte')
        self.assertEqual(self.accorder().unite,'titre')
    def test_correction_remise_annulation_et_usage_distinct(self):
        a=self.accorder();self.remettre(a);r=a.remises.get()
        s.constater(self.u,a,r.pk,date(2026,1,6),D('0'),'Non-utilisation déclarée fictive',bd6.jeton(a))
        self.assertEqual(s.total(a),2);self.assertEqual(r.usages.first().quantite,0)
        s.constater(self.u,a,r.pk,date(2026,1,8),D('1'),'Retour fictif',bd6.jeton(a),motif='Utilisation partielle déclarée')
        self.remettre(a,correction=r.pk,quantite=D('1'),motif='Quantité saisie erronée')
        self.assertEqual(s.total(a),1);self.assertEqual(r.usages.count(),2)
        with self.assertRaises(ValidationError):self.remettre(a,correction=r.pk,quantite=D('0.5'),motif='Fictif')
        s.annuler(self.u,a,bd6.jeton(a),'Erreur fictive de remise',remise=r.pk)
        self.assertEqual(s.total(a),0);self.assertEqual(r.usages.count(),2)
        with self.assertRaises(ValidationError):s.annuler(self.u,a,bd6.jeton(a),'Erreur fictive')
    def test_dates_cibles_source_et_cloture_parent(self):
        a=self.accorder()
        for kw in [dict(date=date(2099,1,1)),dict(date=date(2026,2,1)),dict(source=''),dict(beneficiaires=[])]:
            with self.assertRaises(ValidationError):self.remettre(a,**kw)
        self.remettre(a)
        with self.assertRaises(ValidationError):bd6.clore_prise(self.u,self.a,date(2026,1,5),bd6.jeton(self.a))
        bd6.clore_prise(self.u,self.a,date(2026,1,6),bd6.jeton(self.a))
        with self.assertRaises(ValidationError):self.remettre(a,date=date(2026,1,6))
    def test_correction_et_prolongation_autorisation_preservent_remises(self):
        a=self.accorder();self.remettre(a);d={c:getattr(a,c) for c in s.CHAMPS};d['fin']=date(2026,3,1)
        s.modifier(self.u,a,bd6.jeton(a),'Prolongation fictive',prolongation=True,**d)
        d['fin']=date(2026,1,4)
        with self.assertRaises(ValidationError):s.modifier(self.u,a,bd6.jeton(a),'Correction fictive',**d)
        a.refresh_from_db();self.assertEqual(a.fin,date(2026,3,1));d['fin']=date(2026,2,15)
        s.modifier(self.u,a,bd6.jeton(a),'Prévision trop tardive fictive',**d);self.assertEqual(a.fin,date(2026,2,15))
    def test_tokens_et_journal_atomique(self):
        a=self.accorder();ancien=bd6.jeton(a);self.remettre(a)
        with self.assertRaises(ValidationError):self.remettre(a,attendu=ancien)
        with patch.object(m.RevisionAide.objects,'create',side_effect=RuntimeError('Journal fictif indisponible')):
            with self.assertRaises(RuntimeError):self.remettre(a,quantite=D('1'))
        self.assertEqual(a.remises.count(),1);self.assertEqual(s.total(a),2)
    def test_http_accord_remise_rapport_et_impression(self):
        url=reverse('dossiers:aide_accorder',args=[self.a.pk,'transport']);page=self.client.get(url);self.assertEqual(page.status_code,200)
        d={'type_aide':str(self.type.pk),'beneficiaires':[str(self.p.pk),str(self.p2.pk)],'debut':'2026-01-01','fin':'2026-02-01','quantite':'5','devise':'EUR','source':'Décision fictive','attendu':page.context['form'].initial['attendu']}
        rep=self.client.post(url,d);self.assertEqual(rep.status_code,302,rep.content);a=m.AccordAide.objects.get()
        self.assertContains(self.client.get(rep.url),'réellement remis')
        url=reverse('dossiers:aide_remettre',args=[a.pk]);page=self.client.get(url)
        d={'beneficiaires':[str(self.p.pk)],'date':'2026-01-05','quantite':'2','source':'Remise fictive','attendu':page.context['form'].initial['attendu']}
        self.assertEqual(self.client.post(url,d).status_code,302)
        self.assertEqual(self.client.get(reverse('dossiers:aide',args=[a.pk]),{'edition':'impression'}).status_code,200)
        url=reverse('dossiers:rapport_aides');params={'debut':'2026-01-01','fin':'2026-02-01','mode':'remises','nature':'transport'}
        page=self.client.get(url,params);self.assertEqual(page.status_code,200);self.assertEqual(page.context['nombre'],1)
        rows=list(csv.DictReader(StringIO(self.client.get(url,{**params,'format':'csv'}).content.decode()),delimiter=';'))
        self.assertEqual(rows[0]['quantite'],'2.000');self.assertEqual(rows[0]['unite'],'carte')
        page=self.client.get(reverse('dossiers:prise',args=['menage',self.m.pk,self.a.pk]));self.assertContains(page,'Carte fictive de trois voyages')
    def test_droits_csrf_et_annulation_separee(self):
        a=self.accorder();self.u.user_permissions.remove(Permission.objects.get(codename='add_remiseaide'));u=get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):s.remettre(u,a,[self.p],date(2026,1,5),D(1),'Fictif',bd6.jeton(a))
        s.annuler(u,a,bd6.jeton(a),'Accord erroné fictif');self.assertTrue(a.annule_le)
        c=Client(enforce_csrf_checks=True);c.force_login(self.u)
        self.assertEqual(c.post(reverse('dossiers:aide_accorder',args=[self.a.pk,'transport']),{}).status_code,403)
        self.u.user_permissions.remove(Permission.objects.get(codename='view_revisionaide'));self.client.force_login(get_user_model().objects.get(pk=self.u.pk))
        self.assertEqual(self.client.get(reverse('dossiers:rapport_aides')).status_code,403)
    def test_accueil_de_jour_ne_cree_pas_zero_nuit(self):
        self.type=self.type_creer(nature='accueil_jour',libelle='Accueil fictif',unite='passage');a=self.accorder();self.remettre(a,quantite=D('1'))
        self.assertFalse(m.Sejour.objects.exists());self.assertEqual(statistiques.bilan(date(2026,1,1),date(2026,2,1))['nuitees_theoriques'],0)
    def test_continuite_collective_preserve_compteurs_et_permet_depart_partiel(self):
        accord=h.accorder(self.u,self.a,[self.p,self.p2],date(2026,1,1),date(2026,2,1))
        sejour=h.admettre(self.u,accord,[self.p,self.p2],date(2026,1,1));lieu=h.creer_lieu(self.u,'Chambre fictive')
        h.ajouter_periode(self.u,sejour,date(2026,1,1),None,lieu=lieu)
        avant=statistiques.bilan(date(2026,1,1),date(2026,1,12))
        ch.individualiser(self.u,sejour,date(2026,1,5),'Continuité fictive',ch.jeton(sejour))
        apres=statistiques.bilan(date(2026,1,1),date(2026,1,12));self.assertEqual(avant,apres)
        self.assertEqual(sejour.continuations.count(),2);self.assertEqual(m.ContinuiteSejour.objects.count(),1)
        self.assertEqual(statistiques.exploration_affectations(date(2026,1,1),date(2026,1,12))[0]['nuitees'],22)
        enfant=sejour.continuations.get(beneficiaires=self.p)
        h.ajouter_periode(self.u,enfant,date(2026,1,6),date(2026,1,7),absence=True)
        h.sortir(self.u,enfant,date(2026,1,8))
        bilan=statistiques.bilan(date(2026,1,1),date(2026,1,12));self.assertEqual(bilan['nuitees_theoriques'],18);self.assertEqual(bilan['sorties'],0)
        autre=sejour.continuations.get(beneficiaires=self.p2);h.sortir(self.u,autre,date(2026,1,10))
        self.assertEqual(statistiques.bilan(date(2026,1,1),date(2026,1,12))['sorties'],1)
    def test_corriger_date_de_continuite_atomiquement_sans_changer_nuits(self):
        a=h.accorder(self.u,self.a,[self.p,self.p2],date(2026,1,1),None)
        x=h.admettre(self.u,a,[self.p,self.p2],date(2026,1,1));lieu=h.creer_lieu(self.u,'Lieu fictif de continuité')
        h.ajouter_periode(self.u,x,date(2026,1,2),None,lieu=lieu)
        ch.individualiser(self.u,x,date(2026,1,5),'Fictif',ch.jeton(x))
        avant=statistiques.bilan(date(2026,1,1),date(2026,1,12))
        ch.corriger_coupure(self.u,x,date(2026,1,4),'Date de continuité mal saisie',ch.jeton_coupure(x))
        self.assertEqual(statistiques.bilan(date(2026,1,1),date(2026,1,12)),avant)
        x.refresh_from_db();self.assertEqual(x.fin,date(2026,1,4));self.assertTrue(all(s.debut==date(2026,1,4) for s in x.continuations.all()))
        enfant=x.continuations.first();h.ajouter_periode(self.u,enfant,date(2026,1,6),None,absence=True)
        with self.assertRaises(ValidationError):ch.corriger_coupure(self.u,x,date(2026,1,7),'Traversée fictive',ch.jeton_coupure(x))
        x.refresh_from_db();self.assertEqual(x.fin,date(2026,1,4));self.assertEqual(x.individualisation.revisions.count(),1)

    def test_continuite_perimee_et_rollback(self):
        a=h.accorder(self.u,self.a,[self.p,self.p2],date(2026,1,1),None);x=h.admettre(self.u,a,[self.p,self.p2],date(2026,1,1));token=ch.jeton(x)
        h.ajouter_periode(self.u,x,date(2026,1,2),None,absence=True)
        with self.assertRaises(ValidationError):ch.individualiser(self.u,x,date(2026,1,5),'Fictif',token)
        with patch.object(m.ContinuiteSejour.objects,'create',side_effect=RuntimeError('Fictif')):
            with self.assertRaises(RuntimeError):ch.individualiser(self.u,x,date(2026,1,5),'Fictif',ch.jeton(x))
        x.refresh_from_db();self.assertIsNone(x.fin);self.assertEqual(x.continuations.count(),0);self.assertIsNone(x.absences.get().fin)
    def test_repas_correction_motivee_pas_categorie_deduite(self):
        a=repas.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,2,1),'dejeuner')
        r=repas.distribuer(self.u,a,self.p,date(2026,1,3),2);token=correction_repas.jeton(r)
        correction_repas.corriger(self.u,r,1,'Adulte déclaré fictif','Erreur fictive',token)
        r.refresh_from_db();self.assertEqual(r.quantite,1);self.assertEqual(r.revisions.count(),1)
        with self.assertRaises(ValidationError):correction_repas.corriger(self.u,r,3,'','Fictif',token)
        page=self.client.get(reverse('suivi:accord_repas',args=[a.pk]));self.assertContains(page,'Adulte déclaré fictif')
        url=reverse('dossiers:rapport_aides');params={'nature':'repas','mode':'remises','debut':'2026-01-01','fin':'2026-02-01','categorie':'Adulte déclaré fictif'}
        self.assertEqual(self.client.get(url,params).context['nombre'],1)

    def test_repas_non_quotidiens_et_union_de_jours(self):
        a=repas.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,1,15),'dejeuner',jours_semaine=[0,2])
        self.assertEqual(bd6.nombre_jours([a],date(2026,1,15)),4)
        with self.assertRaises(ValidationError):repas.distribuer(self.u,a,self.p,date(2026,1,6),1)
        repas.distribuer(self.u,a,self.p,date(2026,1,5),1)
        page=self.client.get(reverse('suivi:jour'),{'date':'2026-01-06'});self.assertNotContains(page,'name="form-0-quantite"')
        a.jours_semaine=[0,0]
        with self.assertRaises(ValidationError):a.full_clean()

    def test_rapport_repas_autorises_non_quotidiens_et_prestataire(self):
        a=repas.accorder(self.u,self.a,[self.p,self.p2],date(2026,1,1),date(2026,1,15),'dejeuner','Prestataire fictif',jours_semaine=[0,2])
        p={'nature':'repas','mode':'accords','debut':'2026-01-01','fin':'2026-01-15','prestataire_repas':'Prestataire fictif','service_repas':'dejeuner'}
        page=self.client.get(reverse('dossiers:rapport_aides'),p)
        self.assertEqual(page.status_code,200);self.assertEqual(page.context['nombre'],1);self.assertEqual(page.context['totaux'][0][1],8)
        self.assertEqual(self.client.get(reverse('dossiers:rapport_aides'),{**p,'prestataire_repas':'Autre fictif'}).context['nombre'],0)

    def test_hierarchie_de_lieux_correction_et_boucle(self):
        parent=h.creer_lieu(self.u,'Établissement fictif',niveau='etablissement')
        enfant=h.creer_lieu(self.u,'Chambre fictive',parent=parent,niveau='chambre')
        self.assertEqual(str(enfant),'Établissement fictif / Chambre fictive')
        d={c:getattr(enfant,c) for c in ('libelle','parent','niveau','partenaire','organisme')};d['libelle']='Chambre fictive corrigée'
        h.corriger_lieu(self.u,enfant,bd6.jeton(enfant),'Erreur de libellé fictive',**d)
        self.assertEqual(enfant.revisions.count(),2)
        d={c:getattr(parent,c) for c in ('libelle','parent','niveau','partenaire','organisme')};d['parent']=enfant
        with self.assertRaises(ValidationError):h.corriger_lieu(self.u,parent,bd6.jeton(parent),'Boucle fictive',**d)
        self.assertEqual(self.client.get(reverse('dossiers:lieux_c')).status_code,200)

    def test_travail_du_jour_conserve_date_et_retour_apres_remise(self):
        a=self.accorder();url=reverse('dossiers:aide_remettre',args=[a.pk])+'?retour=jour&date_service=2026-01-05'
        page=self.client.get(url);self.assertEqual(page.context['form'].initial['date'],date(2026,1,5))
        d={'beneficiaires':[str(self.p.pk)],'date':'2026-01-05','quantite':'1','source':'Fictif','attendu':page.context['form'].initial['attendu']}
        rep=self.client.post(url,d);self.assertEqual(rep.status_code,302);self.assertIn('date=2026-01-05',rep.url)

    def test_detail_hebergement_individuel_csv_et_dates(self):
        accord=h.accorder(self.u,self.a,[self.p,self.p2],date(2026,1,1),None)
        x=h.admettre(self.u,accord,[self.p,self.p2],date(2026,1,1));ch.individualiser(self.u,x,date(2026,1,5),'Fictif',ch.jeton(x))
        url=reverse('dossiers:rapport_hebergement_individuel');p={'debut':'2026-01-01','fin':'2026-01-10'}
        page=self.client.get(url,p);self.assertEqual(page.status_code,200);self.assertEqual(sum(v['nuits'] for v in page.context['lignes']),18)
        rows=list(csv.DictReader(StringIO(self.client.get(url,{**p,'format':'csv'}).content.decode()),delimiter=';'))
        self.assertEqual(len(rows),4);self.assertEqual({v['episode_initial'] for v in rows},{str(x.pk)})

    def test_service_repas_correction(self):
        from . import accords
        from django.test import override_settings
        a=repas.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,2,1),'dejeuner')
        repas.distribuer(self.u,a,self.p,date(2026,1,5),1)
        with self.assertRaises(ValidationError):correction_repas.corriger_service(self.u,a,[1],'','Fictif',accords.jeton(a))
        correction_repas.corriger_service(self.u,a,[0,2],'Prestataire fictif','Jours mal renseignés',accords.jeton(a))
        self.assertEqual(a.revisions_service.count(),1)
        self.assertEqual(self.client.get(reverse('dossiers:corriger_service_repas',args=[a.pk])).status_code,200)
    def _verifier_pdf(self,navigateur):
        from django.test import override_settings
        aide=self.accorder();self.remettre(aide)
        with override_settings(MODE_PWA=navigateur):
            pdf=self.client.get(reverse('dossiers:aide_pdf',args=[aide.pk]))
            self.assertEqual(pdf.status_code,200);self.assertTrue(pdf.content.startswith(b'%PDF-'));self.assertIn('no-store',pdf['Cache-Control'])

    def test_pdf_natif(self):self._verifier_pdf(False)

    def test_pdf_pwa(self):
        import importlib.util
        if importlib.util.find_spec('fpdf') is None:self.skipTest('Dépendance facultative fpdf2 du profil PWA absente.')
        self._verifier_pdf(True)


class MetaCTransactions(TransactionTestCase):
    setUp=MetaCTests.setUp
    type_creer=MetaCTests.type_creer
    accorder=MetaCTests.accorder
    remettre=MetaCTests.remettre

    def test_concurrence_deux_remises_ne_depassent_pas_autorisation(self):
        import threading
        from django.db import close_old_connections,OperationalError
        a=self.accorder(quantite=D('1'));token=bd6.jeton(a);barriere=threading.Barrier(2);resultats=[];erreurs=[]
        def travail():
            close_old_connections()
            try:
                u=get_user_model().objects.get(pk=self.u.pk);x=m.AccordAide.objects.get(pk=a.pk);p=m.Personne.objects.get(pk=self.p.pk)
                u.get_all_permissions();barriere.wait(timeout=10)
                try:s.remettre(u,x,[p],date(2026,1,5),D('1'),'Fictif',token);resultats.append(True)
                except (ValidationError,OperationalError):resultats.append(False)
            except Exception as exc:erreurs.append(exc)
            finally:close_old_connections()
        ts=[threading.Thread(target=travail) for _ in range(2)]
        for t in ts:t.start()
        for t in ts:t.join(20)
        self.assertFalse(any(t.is_alive() for t in ts));self.assertFalse(erreurs,erreurs);self.assertEqual(sum(resultats),1,resultats)
        self.assertEqual(s.total(a),1);self.assertEqual(a.revisions.count(),2)

    def test_copie_restauree_conserve_quantites_sources_et_journaux(self):
        import sqlite3,tempfile,json
        from pathlib import Path
        from django.db import connection
        if connection.vendor!='sqlite':self.skipTest('Recette SQLite.')
        self.type=self.type_creer(nature='produits',unite='kg',fractionnable=True)
        a=self.accorder();self.remettre(a,quantite=D('2.750'));r=a.remises.get()
        s.constater(self.u,a,r.pk,date(2026,1,6),D('0'),'Fictif',bd6.jeton(a))
        s.annuler(self.u,a,bd6.jeton(a),'Erreur fictive',remise=r.pk)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'copie.sqlite3'
            with closing(sqlite3.connect(path)) as db, db:connection.connection.backup(db)
            with closing(sqlite3.connect(path)) as db, db:
                self.assertEqual(D(str(db.execute('SELECT quantite FROM personnes_remiseaide').fetchone()[0])),D('2.750'))
                self.assertEqual(db.execute('SELECT unite FROM personnes_accordaide').fetchone()[0],'kg')
                self.assertEqual(db.execute('SELECT motif_annulation FROM personnes_remiseaide').fetchone()[0],'Erreur fictive')
                self.assertEqual(db.execute('SELECT COUNT(*) FROM personnes_revisionaide').fetchone()[0],4)
            with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')

    def test_migration_conserve_repas_anciens_sans_types_inventes(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        if connection.vendor!='sqlite':self.skipTest('Recette locale SQLite.')
        uid=get_user_model().objects.create_user('migration-c-fictive').pk
        ex=MigrationExecutor(connection);latest=ex.loader.graph.leaf_nodes();old=[('personnes','0028_parcours_demandes_objectifs')]
        try:
            ex.migrate(old);apps=ex.loader.project_state(old).apps
            P=apps.get_model('personnes','Personne');M=apps.get_model('personnes','Menage');A=apps.get_model('personnes','Accompagnement');R=apps.get_model('personnes','AccordRepas');Distri=apps.get_model('personnes','RepasDistribue')
            p=P.objects.create(designation='Ancienne personne fictive',cree_par_id=uid);menage=M.objects.create(libelle='Ancien ménage fictif',cree_par_id=uid)
            a=A.objects.create(menage=menage,debut=date(2026,1,1),cree_par_id=uid);r=R.objects.create(accompagnement=a,debut=date(2026,1,1),service='dejeuner',cree_par_id=uid)
            x=Distri.objects.create(accord=r,beneficiaire=p,date=date(2026,1,5),quantite=2,cree_par_id=uid);pk=x.pk
        finally:MigrationExecutor(connection).migrate(latest)
        x=m.RepasDistribue.objects.get(pk=pk);self.assertEqual(x.quantite,2);self.assertEqual(x.categorie_declaree,'');self.assertEqual(x.accord.jours_semaine,[])
        self.assertFalse(m.TypeAide.objects.exists());self.assertFalse(m.ContinuiteSejour.objects.exists())
        self.assertFalse(get_user_model().objects.get(pk=uid).user_permissions.exists())
