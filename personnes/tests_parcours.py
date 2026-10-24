"""Recettes métier du méta-lot B : parcours complets, conflits et exploitation."""
from contextlib import closing
import csv
from datetime import date
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from . import models as m, parcours as s, bd6, ouverture_prise, textes_riches as tr


def valeurs(code,**kw):
    r=s.RUBRIQUES[code]
    d={c:r.version._meta.get_field(c).get_default() for c in r.champs}
    d.update({'demandes':{'etat':'attente','motif_demande':'Accueil fictif','demandeur':'personne'},
        'orientations':{'etat':'proposee','destination':'Service fictif','motif_orientation':'Besoin fictif'},
        'objectifs':{'etat':'encours','theme':'Logement fictif','titre':'Objectif fictif','horizon':'court'},
        'suivi':{'etat':'actif','raison':'Ouverture de suivi fictive'}}[code])
    d.update(kw);return d


class ParcoursTests(TestCase):
    def setUp(self):
        self.u=get_user_model().objects.create_user('parcours-fictif')
        call_command('autoriser_chrs7',self.u.username,stdout=StringIO());call_command('autoriser_solenne',self.u.username,stdout=StringIO())
        self.u=get_user_model().objects.get(pk=self.u.pk)
        self.p=m.Personne.objects.create(designation='Personne fictive parcours',cree_par=self.u)
        self.autre=m.Personne.objects.create(designation='Autre personne fictive',cree_par=self.u)
        self.client.force_login(self.u)

    def creer(self,code='demandes',jour=date(2026,1,1),**kw):
        return s.creer(self.u,code,self.p,[self.p],jour,'Entretien fictif',bd6.jeton(self.p),**valeurs(code,**kw))

    def changer(self,code,e,jour=date(2026,1,5),**kw):
        v=e.versions.first();d={c:getattr(v,c) for c in s.RUBRIQUES[code].champs};d.update(kw)
        return s.enregistrer(self.u,code,e,jour,'Nouvel entretien fictif',bd6.jeton(e),**d)

    def ouvrir(self,e,debut=date(2026,1,10),**kw):
        return ouverture_prise.ouvrir(self.u,self.p,[self.p],debut,None,ouverture_prise.jeton(self.p),
            creer_menage=True,libelle_menage='Ménage fictif parcours',demande=e,attendu_demande=bd6.jeton(e),**kw)

    def test_demande_refusee_sans_fausse_admission(self):
        e=self.creer();self.changer('demandes',e,etat='refusee',motif_decision='Pas de place fictive')
        self.assertFalse(m.Accompagnement.objects.exists());self.assertFalse(m.Sejour.objects.exists())
        self.assertEqual(s.a_date('demandes',date(2026,1,2)).get().etat,'attente')
        self.assertEqual(s.a_date('demandes',date(2026,1,6)).get().etat,'refusee')
        self.assertEqual(e.revisions.count(),2)

    def test_acceptation_ouverture_atomique_sans_arrivee_et_non_rejeu(self):
        e=self.creer();self.changer('demandes',e,etat='acceptee')
        a=self.ouvrir(e);e.refresh_from_db()
        self.assertEqual(e.accompagnement_id,a.pk);self.assertFalse(m.Sejour.objects.exists());self.assertFalse(m.AccordHebergement.objects.exists())
        self.assertEqual(e.revisions.first().action,'liaison')
        with self.assertRaises(ValidationError):self.ouvrir(e)
        self.assertEqual(m.Accompagnement.objects.count(),1);self.assertEqual(m.Menage.objects.count(),1)

    def test_demande_non_acceptee_refuse_ouverture_et_annule_tout(self):
        e=self.creer()
        with self.assertRaises(ValidationError):self.ouvrir(e)
        self.assertFalse(m.Accompagnement.objects.exists());self.assertFalse(m.Menage.objects.exists())
        self.assertFalse(m.EvenementSuivi.objects.exists())

    def test_liaison_correction_conserve_prise_et_cibles(self):
        e=self.creer(etat='acceptee');a=self.ouvrir(e)
        with self.assertRaises(ValidationError):s.annuler(self.u,'demandes',e,'Confusion fictive',bd6.jeton(e))
        s.lier(self.u,e,a,bd6.jeton(e),'Erreur de liaison fictive',retirer=True)
        e.refresh_from_db();self.assertIsNone(e.accompagnement_id);self.assertTrue(m.Accompagnement.objects.filter(pk=a.pk).exists())
        s.annuler(self.u,'demandes',e,'Mauvais dossier fictif',bd6.jeton(e));e.refresh_from_db();self.assertIsNotNone(e.annule_le)
        self.assertFalse(s.a_date('demandes',date(2026,1,20)).exists())

    def test_liaison_refuse_autres_beneficiaires_et_decision_apres_admission(self):
        from . import suivi
        e=self.creer();self.changer('demandes',e,date(2026,1,15),etat='acceptee')
        with self.assertRaises(ValidationError):self.ouvrir(e,date(2026,1,10))
        menage=suivi.creer_menage(self.u,'Ménage autre fictif',[self.autre],date(2026,1,1))
        a=suivi.ouvrir(self.u,menage,[self.autre],date(2026,1,20))
        with self.assertRaises(ValidationError):s.lier(self.u,e,a,bd6.jeton(e),'Tentative fictive')
        self.assertFalse(m.DemandeAccueil.objects.filter(accompagnement__isnull=False).exists())

    def test_toutes_chronologies_correction_insertion_et_annulation(self):
        for code in s.RUBRIQUES:
            with self.subTest(code=code):
                e=self.creer(code)
                self.changer(code,e,date(2026,1,10))
                d=valeurs(code)
                s.enregistrer(self.u,code,e,date(2026,1,5),'Information retrouvée fictive',bd6.jeton(e),motif='Oubli fictif',**d)
                x=e.versions.get(debut=date(2026,1,5));self.assertEqual(x.fin,date(2026,1,10))
                s.enregistrer(self.u,code,e,date(2026,1,6),'Source corrigée fictive',bd6.jeton(e),correction=x.pk,motif='Erreur fictive',**d)
                x.refresh_from_db();self.assertEqual(x.debut,date(2026,1,6))
                with self.assertRaises(ValidationError):s.enregistrer(self.u,code,e,date(2026,1,20),'Source fictive',bd6.jeton(e),correction=x.pk,motif='Traverse fictive',**d)
                s.annuler(self.u,code,e,'Erreur de cible fictive',bd6.jeton(e));self.assertEqual(e.versions.count(),3)
                journal=e.revisions.first();self.assertEqual(journal.avant[0]['annulation'],'');self.assertEqual(journal.apres[0]['annulation'],'Erreur de cible fictive')
                self.assertEqual(journal.avant[0]['beneficiaires'][0]['id'],str(self.p.pk))

    def test_objectif_longitudinal_riche_au_dela_cloture_et_reprise(self):
        e=self.creer(etat='acceptee');a=self.ouvrir(e)
        doc={'version':1,'doc':{'type':'doc','content':[{'type':'paragraph','content':[{'type':'text','text':'Progression fictive','marks':[{'type':'bold'}]}]}]}}
        o=s.creer(self.u,'objectifs',self.p,[self.p],date(2026,1,10),'Fictif',bd6.jeton(self.p),accompagnement=a,**valeurs('objectifs',texte=tr.ValeurTexte('Progression fictive',doc)))
        bd6.clore_prise(self.u,a,date(2026,1,15),bd6.jeton(a))
        self.changer('objectifs',o,date(2026,2,1),etat='atteint',texte='Démarche fictive aboutie')
        self.assertEqual(o.versions.first().etat,'atteint');self.assertEqual(o.versions.last().texte_document,doc)
        page=self.client.get(reverse('dossiers:parcours_element',args=['objectifs',o.pk]));self.assertContains(page,'Démarche fictive aboutie');self.assertContains(page,'Progression fictive')

    def test_plusieurs_orientations_et_resultats_sans_cloture(self):
        e=self.creer(etat='acceptee');a=self.ouvrir(e)
        os=[]
        for dest in ('Service fictif A','Service fictif B'):
            os.append(s.creer(self.u,'orientations',self.p,[self.p],date(2026,1,10),'Fictif',bd6.jeton(self.p),accompagnement=a,demande=e,**valeurs('orientations',destination=dest)))
        self.changer('orientations',os[0],date(2026,1,12),etat='realisee',resultat='Rendez-vous fictif effectué')
        self.changer('orientations',os[1],date(2026,1,13),etat='refusee',resultat='Proposition fictive refusée')
        a.refresh_from_db();self.assertIsNone(a.fin);self.assertEqual(m.OrientationParcours.objects.count(),2)

    def test_suivi_termine_ne_bloque_pas_nouvel_accueil(self):
        e=self.creer('suivi');self.changer('suivi',e,etat='termine',raison='Fin de suivi fictive')
        d=self.creer(etat='acceptee');a=self.ouvrir(d)
        self.assertTrue(a.pk);self.changer('suivi',e,date(2026,2,1),etat='actif',raison='Nouvel accueil fictif')
        self.assertEqual(e.versions.count(),3)
        with self.assertRaises(ValidationError):self.creer('suivi')

    def test_validation_sources_futur_rollback_journal_et_tokens(self):
        e=self.creer();old=bd6.jeton(e)
        self.changer('demandes',e,etat='acceptee')
        with self.assertRaises(ValidationError):s.enregistrer(self.u,'demandes',e,date(2026,1,6),'Fictif',old,**valeurs('demandes'))
        with self.assertRaises(ValidationError):self.changer('demandes',e,date(2099,1,1))
        with patch.object(m.RevisionDemande.objects,'create',side_effect=RuntimeError('Journal fictif indisponible')):
            with self.assertRaises(RuntimeError):self.changer('demandes',e,date(2026,1,7),etat='refusee',motif_decision='Fictif')
        self.assertEqual(e.versions.count(),2);self.assertEqual(e.versions.first().etat,'acceptee')
        e2=self.creer()
        with self.assertRaises(ValidationError):s.enregistrer(self.u,'demandes',e2,date(2026,1,1),'Fictif',bd6.jeton(e2),correction=e.versions.first().pk,motif='Fictif',**valeurs('demandes'))

    def test_http_formulaires_creation_et_retours(self):
        for code in s.RUBRIQUES:
            with self.subTest(code=code):
                url=reverse('dossiers:parcours_nouveau',args=['personne',self.p.pk,code])+'?q=Fictif&mode=personnes&page=2'
                page=self.client.get(url);self.assertEqual(page.status_code,200)
                d={k:('' if v is None else v) for k,v in valeurs(code).items()};d.update(debut='2026-01-01',source='Entretien fictif',attendu=page.context['form'].initial['attendu'],beneficiaires=[str(self.p.pk)])
                rep=self.client.post(url,d);self.assertEqual(rep.status_code,302,rep.content);self.assertIn('page=2',rep.url)
                self.assertEqual(self.client.get(rep.url).status_code,200)
                e=s.RUBRIQUES[code].racine.objects.get();self.assertEqual(self.client.get(reverse('dossiers:parcours_element',args=[code,e.pk])).status_code,200)
                impression=self.client.get(reverse('dossiers:parcours_element',args=[code,e.pk]),{'edition':'impression'})
                self.assertEqual(impression.status_code,200);self.assertContains(impression,'Données déclarées à la date consultée')

    def test_rapports_cohortes_demandes_delais_csv_et_filtres(self):
        e=self.creer(etat='acceptee',activite='chrs',groupe_demande='Personne seule déclarée',dernier_hebergement_duree='Quelques mois déclarés');self.ouvrir(e)
        refusee=self.creer();self.changer('demandes',refusee,etat='refusee',motif_decision='Refus fictif')
        url=reverse('dossiers:rapport_parcours');params={'rubrique':'demandes','date':'2026-01-20','admission':'oui','activite':'chrs'}
        rep=self.client.get(url,params);self.assertEqual(rep.status_code,200);self.assertEqual(rep.context['nombre'],1);self.assertEqual(rep.context['delais'],[9])
        rows=list(csv.DictReader(StringIO(self.client.get(url,{**params,'format':'csv'}).content.decode()),delimiter=';'))
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['delai_jours'],'9');self.assertEqual(rows[0]['groupe_demande'],'Personne seule déclarée');self.assertEqual(rows[0]['dernier_hebergement_duree'],'Quelques mois déclarés')
        self.assertEqual(self.client.get(url,{**params,'date':'2026-01-02'}).context['nombre'],0)
        self.assertEqual(self.client.get(url,{'rubrique':'demandes','date':'2026-01-20','etat':'refusee'}).context['nombre'],1)
        for code in ('objectifs','orientations','suivi'):
            self.creer(code);r=self.client.get(url,{'rubrique':code,'date':'2026-01-20'});self.assertEqual(r.status_code,200);self.assertEqual(r.context['nombre'],1)

    def test_droits_serveur_csrf_et_annulation_distincte(self):
        e=self.creer()
        u=get_user_model().objects.create_user('lecture-parcours-fictive');u.user_permissions.set(self.u.user_permissions.exclude(codename__startswith='change_'))
        # Le contrôle serveur ne dépend pas des boutons.
        u.user_permissions.remove(Permission.objects.get(codename='view_versiondemande'))
        c=Client();c.force_login(u)
        self.assertEqual(c.get(reverse('dossiers:parcours_element',args=['demandes',e.pk])).status_code,403)
        self.assertEqual(c.get(reverse('dossiers:rapport_parcours'),{'rubrique':'demandes'}).status_code,403)
        self.u.user_permissions.remove(Permission.objects.get(codename='add_demandeaccueil'));self.u=get_user_model().objects.get(pk=self.u.pk)
        s.annuler(self.u,'demandes',e,'Erreur fictive',bd6.jeton(e))
        c=Client(enforce_csrf_checks=True);c.force_login(self.u)
        self.assertEqual(c.post(reverse('dossiers:parcours_nouveau',args=['personne',self.p.pk,'objectifs']),{}).status_code,403)

    def test_http_admission_depuis_demande_et_rejet_perime_atomique(self):
        e=self.creer(etat='acceptee')
        url=reverse('dossiers:nouvelle_prise',args=['personne',self.p.pk])+'?demande='+str(e.pk)+'&q=fictif&page=2'
        page=self.client.get(url);self.assertEqual(page.status_code,200)
        d={'debut':'2026-01-10','fin_prevue':'','beneficiaires':[str(self.p.pk)],'rattachement':'nouveau','libelle_menage':'Ménage fictif HTTP',
            'attendu':page.context['form'].initial['attendu'],'attendu_demande':page.context['form'].fields['attendu_demande'].initial}
        self.changer('demandes',e,etat='refusee',motif_decision='Décision fictive modifiée')
        rep=self.client.post(url,d);self.assertEqual(rep.status_code,409);self.assertFalse(m.Accompagnement.objects.exists());self.assertFalse(m.Menage.objects.exists())
        self.changer('demandes',e,date(2026,1,6),etat='acceptee')
        page=self.client.get(url);d['attendu']=page.context['form'].initial['attendu'];d['attendu_demande']=page.context['form'].fields['attendu_demande'].initial
        rep=self.client.post(url,d);self.assertEqual(rep.status_code,302,rep.content);self.assertIn('page=2',rep.url)
        self.assertContains(self.client.get(rep.url),'Consulter la demande et sa décision')

    def test_menage_beneficiaires_et_retour_individuel_sur_demarche_commune(self):
        from . import suivi
        menage=suivi.creer_menage(self.u,'Ménage fictif commun',[self.p,self.autre],date(2026,1,1))
        e=s.creer(self.u,'demandes',menage,[self.p,self.autre],date(2026,1,1),'Fictif',bd6.jeton(menage),**valeurs('demandes',demandeur='menage'))
        self.assertEqual(e.beneficiaires.count(),2);self.assertFalse(m.Accompagnement.objects.exists())
        url=reverse('dossiers:parcours',args=['personne',self.p.pk])
        page=self.client.get(url,{'rubrique':'demandes','q':'nom fictif','page':'2'});self.assertContains(page,'Ménage fictif commun')
        element=reverse('dossiers:parcours_element',args=['demandes',e.pk])
        page=self.client.get(element,{'retour_nature':'personne','retour_pk':str(self.p.pk),'q':'nom fictif','page':'2'})
        self.assertIn('/personne/'+str(self.p.pk)+'/parcours/',page.context['retour']);self.assertIn('page=2',page.context['retour'])
        self.u.user_permissions.remove(Permission.objects.get(codename='view_menage'));self.u=get_user_model().objects.get(pk=self.u.pk);self.client.force_login(self.u)
        self.assertNotContains(self.client.get(url,{'rubrique':'demandes'}),'Ménage fictif commun')
        self.assertEqual(self.client.get(element).status_code,403)

    def test_rapport_anciennes_informations_activite_et_motifs_exacts(self):
        from . import informations_suivi as infos
        e=self.creer(etat='acceptee');a=self.ouvrir(e)
        d={c:'' for c in infos.CHAMPS};d.update(activite='chrs',motif_entree='Motif fictif exact',provenance='Ville fictive')
        v=infos.enregistrer(self.u,a,infos.jeton(a,None),'Fictif',**d)
        d['activite']='urgence';infos.enregistrer(self.u,a,infos.jeton(a,v),'Changement fictif',**d)
        url=reverse('dossiers:rapport_parcours');params={'rubrique':'prises','date':'2026-01-20','activite':'urgence','motif_entree':'Motif fictif exact'}
        page=self.client.get(url,params);self.assertEqual(page.status_code,200);self.assertEqual(page.context['nombre'],1)
        rows=list(csv.DictReader(StringIO(self.client.get(url,{**params,'format':'csv'}).content.decode()),delimiter=';'))
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['activite'],'urgence')
        self.assertEqual(self.client.get(url,{**params,'activite':'chrs'}).context['nombre'],0)
        self.assertEqual(self.client.get(url,{**params,'motif_entree':'Motif fictif'}).context['nombre'],0)
        self.assertEqual(a.informations.count(),2)
        bd6.clore_prise(self.u,a,date(2026,1,15),bd6.jeton(a))
        rows=list(csv.DictReader(StringIO(self.client.get(url,{**params,'format':'csv','sortie_depuis':'2026-01-14'}).content.decode()),delimiter=';'))
        self.assertEqual(rows[0]['fin_exclue'],'2026-01-15');self.assertEqual(rows[0]['date_effet'],'');self.assertTrue(rows[0]['saisie_le'])
        self.assertEqual(self.client.get(url,{**params,'sortie_depuis':'2026-01-16'}).context['nombre'],0)

    def test_pas_de_fuite_du_contexte_prise_sans_droits(self):
        e=self.creer(etat='acceptee');a=self.ouvrir(e)
        o=s.creer(self.u,'objectifs',self.p,[self.p],date(2026,1,10),'Fictif',bd6.jeton(self.p),accompagnement=a,**valeurs('objectifs'))
        self.u.user_permissions.remove(Permission.objects.get(codename='view_accompagnement'));self.u=get_user_model().objects.get(pk=self.u.pk);self.client.force_login(self.u)
        page=self.client.get(reverse('dossiers:parcours_element',args=['objectifs',o.pk]));self.assertEqual(page.status_code,200);self.assertNotContains(page,'Ménage fictif parcours')
        report=self.client.get(reverse('dossiers:rapport_parcours'),{'rubrique':'demandes','date':'2026-01-20'})
        self.assertEqual(report.context['delais'],[]);self.assertNotIn('admission',report.context['form'].fields)


class ParcoursTransactionsTests(TransactionTestCase):
    def setUp(self):
        self.u=get_user_model().objects.create_user('parcours-transactions-fictif')
        call_command('autoriser_chrs7',self.u.username,stdout=StringIO());call_command('autoriser_solenne',self.u.username,stdout=StringIO())
        self.u=get_user_model().objects.get(pk=self.u.pk);self.p=m.Personne.objects.create(designation='Fictif transactions',cree_par=self.u)

    def test_concurrence_deux_decisions_un_seul_changement(self):
        import threading
        from django.db import close_old_connections, OperationalError
        e=s.creer(self.u,'demandes',self.p,[self.p],date(2026,1,1),'Fictif',bd6.jeton(self.p),**valeurs('demandes'))
        token=bd6.jeton(e);barriere=threading.Barrier(2);resultats=[];erreurs=[]
        def travail():
            close_old_connections()
            try:
                u=get_user_model().objects.get(pk=self.u.pk);x=m.DemandeAccueil.objects.get(pk=e.pk)
                u.get_all_permissions();barriere.wait(timeout=10)
                try:s.enregistrer(u,'demandes',x,date(2026,1,5),'Fictif',token,**valeurs('demandes',etat='acceptee'));resultats.append(True)
                except (ValidationError,OperationalError):resultats.append(False)
            except Exception as exc:erreurs.append(exc)
            finally:close_old_connections()
        ts=[threading.Thread(target=travail) for _ in range(2)]
        for t in ts:t.start()
        for t in ts:t.join(20)
        self.assertFalse(any(t.is_alive() for t in ts));self.assertFalse(erreurs,erreurs)
        self.assertEqual(sum(resultats),1,resultats);self.assertEqual(e.versions.count(),2);self.assertEqual(e.revisions.count(),2)

    def test_copie_restauree_conserve_versions_liaisons_beneficiaires_et_documents(self):
        import sqlite3,tempfile,json
        from pathlib import Path
        from django.db import connection
        if connection.vendor!='sqlite':self.skipTest('Recette de copie SQLite.')
        e=s.creer(self.u,'demandes',self.p,[self.p],date(2026,1,1),'Fictif',bd6.jeton(self.p),**valeurs('demandes',etat='acceptee'))
        a=ouverture_prise.ouvrir(self.u,self.p,[self.p],date(2026,1,5),None,ouverture_prise.jeton(self.p),creer_menage=True,libelle_menage='Ménage fictif sauvegardé',demande=e,attendu_demande=bd6.jeton(e))
        doc={'version':1,'doc':{'type':'doc','content':[{'type':'paragraph','content':[{'type':'text','text':'Texte fictif conservé'}]}]}}
        o=s.creer(self.u,'objectifs',self.p,[self.p],date(2026,1,5),'Fictif',bd6.jeton(self.p),accompagnement=a,**valeurs('objectifs',texte=tr.ValeurTexte('Texte fictif conservé',doc)))
        s.annuler(self.u,'objectifs',o,'Erreur fictive sauvegardée',bd6.jeton(o))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'copie.sqlite3'
            with closing(sqlite3.connect(p)) as db, db:connection.connection.backup(db)
            with closing(sqlite3.connect(p)) as db, db:
                self.assertEqual(db.execute('SELECT accompagnement_id FROM personnes_demandeaccueil').fetchone()[0],a.pk.hex)
                self.assertEqual(json.loads(db.execute('SELECT texte_document FROM personnes_versionobjectif').fetchone()[0]),doc)
                self.assertEqual(db.execute('SELECT motif_annulation FROM personnes_objectifparcours').fetchone()[0],'Erreur fictive sauvegardée')
                self.assertEqual(db.execute('SELECT COUNT(*) FROM personnes_demandeaccueil_beneficiaires').fetchone()[0],1)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM personnes_revisiondemande').fetchone()[0],2)
            with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')

    def test_migration_preserve_recits_et_ne_cree_ni_demandes_ni_droits(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        if connection.vendor!='sqlite':self.skipTest('Recette locale SQLite.')
        uid=get_user_model().objects.create_user('migration-b-fictive').pk;executor=MigrationExecutor(connection);latest=executor.loader.graph.leaf_nodes();old=[('personnes','0027_durees_declarees')]
        try:
            executor.migrate(old);apps=executor.loader.project_state(old).apps
            M=apps.get_model('personnes','Menage');A=apps.get_model('personnes','Accompagnement');I=apps.get_model('personnes','InformationsAccompagnement')
            menage=M.objects.create(libelle='Ancien ménage fictif',cree_par_id=uid);a=A.objects.create(menage=menage,debut=date(2026,1,1),cree_par_id=uid)
            i=I.objects.create(accompagnement=a,version=1,auteur_id=uid,motif='Ancien récit fictif',objectifs_courts='Projet ancien conservé sans découpage',provenance='Ancienne provenance fictive')
            pk=i.pk
        finally:MigrationExecutor(connection).migrate(latest)
        i=m.InformationsAccompagnement.objects.get(pk=pk);self.assertEqual(i.objectifs_courts,'Projet ancien conservé sans découpage');self.assertEqual(i.activite,'')
        for r in s.RUBRIQUES.values():self.assertFalse(r.racine.objects.exists())
        self.assertFalse(get_user_model().objects.get(pk=uid).user_permissions.filter(codename='add_demandeaccueil').exists())
