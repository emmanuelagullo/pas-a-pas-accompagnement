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
from django.test import TestCase,TransactionTestCase,Client,override_settings
from django.urls import reverse
from . import models as m,financements as s,bd6,suivi,hebergement,repas


def autoriser(u):
    call_command('autoriser_chrs7',u.username,stdout=StringIO());call_command('autoriser_solenne',u.username,stdout=StringIO())
    return get_user_model().objects.get(pk=u.pk)


class MetaDTests(TestCase):
    def setUp(self):
        self.u=autoriser(get_user_model().objects.create_user('financement-fictif'))
        self.p=m.Personne.objects.create(designation='Personne fictive D',cree_par=self.u)
        self.m=suivi.creer_menage(self.u,'Ménage fictif D',[self.p],date(2026,1,1))
        self.a=suivi.ouvrir(self.u,self.m,[self.p],date(2026,1,1))
        self.accord=hebergement.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,2,1))
        self.org=m.Partenaire.objects.create(libelle='Organisme fictif D',cree_par=self.u)
        self.client.force_login(self.u)
    def tarif(self,**kw):
        d=dict(debut=date(2026,1,1),fin=None,libelle='Chambre fictive',unite='chambre-nuit',categorie='',montant=D('25.1250'),devise='EUR',prestataire=self.org,actif=True,source='Convention fictive');d.update(kw)
        return s.definir_tarif(self.u,s.creation_tarif(),'Définition fictive',**d)
    def ligne(self,**kw):
        d=dict(phase='autorise',date=date(2026,1,5),libelle='Chambre fictive',unite='chambre-nuit',categorie='',quantite=D('2'),prix=D('25.1250'),tarif=None,justification='Deux chambres-nuits autorisées par décision fictive');d.update(kw);return d
    def imputation(self,**kw):
        d=dict(phase='autorise',financeur=self.org,budget='Budget fictif',montant=D('30'),reference='FICTIF-1');d.update(kw);return d
    def enregistrer(self,**kw):
        d=dict(attendu=s.jeton(self.accord),motif='Définition fictive',action='definition',lignes=[self.ligne()],imputations=[self.imputation()],emetteur=None,mentions='',debut=date(2026,1,1),fin=date(2026,2,1),devise='EUR',prestataire=self.org,prescripteur=None,facturation=self.org,signataire=None,reference='FICTIF',source='Convention fictive');d.update(kw)
        return s.enregistrer(self.u,self.accord,**d)
    def nouvelle(self,**kw):
        v=s.financement(self.accord).versions.first();d={c:getattr(v,c) for c in s.ENTETE}
        d.update(action='correction',motif='Correction fictive');d.update(kw);return self.enregistrer(**d)
    def emettre(self,**kw):
        d=dict(attendu=s.jeton(self.accord),modele='engagement',phase='autorise',date=date(2026,1,6));d.update(kw)
        return s.emettre(self.u,self.accord,**d)
    def test_calcul_decimal_arrondi_par_ligne_et_phases_distinctes(self):
        f=self.enregistrer(lignes=[self.ligne(prix=D('.0025'),quantite=D('2')),self.ligne(phase='prevu',quantite=D('4'))],imputations=[])
        v=f.versions.first();self.assertEqual(s.totaux(v),{'prevu':D('100.50'),'autorise':D('.01'),'realise':0})
        self.assertFalse(m.Sejour.objects.exists());self.assertEqual(self.a.fin,None)
    def test_imputations_multiples_reliquat_et_depassement_refuse(self):
        f=self.enregistrer(imputations=[self.imputation(),self.imputation(budget='Autre budget fictif',montant=D('10'))]);v=f.versions.first()
        self.assertEqual(s.detail_totaux(v)[1]['reste'],D('10.25'))
        with self.assertRaises(ValidationError):self.nouvelle(imputations=[self.imputation(montant=D('50.26'))])
        self.assertEqual(f.versions.count(),1)
    def test_tarifs_dated_et_correction_ne_reecrivent_pas_calculs(self):
        t=self.tarif();v=t.versions.first();f=self.enregistrer(lignes=[self.ligne(tarif=v)])
        d={c:getattr(v,c) for c in s.TARIF};d.update(debut=date(2026,1,10),montant=D('30'))
        s.definir_tarif(self.u,bd6.jeton(t),'Nouveau tarif fictif',action='changement',tarif=t,**d)
        self.assertEqual(s.applicable(t,date(2026,1,5)).pk,v.pk);self.assertEqual(s.applicable(t,date(2026,1,10)).montant,30)
        self.assertEqual(f.versions.first().lignes.get().prix,D('25.1250'))
        with self.assertRaises(ValidationError):self.nouvelle(lignes=[self.ligne(tarif=v,date=date(2026,1,11))])
        d.update(debut=date(2026,1,1),montant=D('20'))
        s.definir_tarif(self.u,bd6.jeton(t),'Prix initial mal saisi',action='correction',tarif=t,**d)
        self.assertEqual(f.versions.first().lignes.get().montant,D('50.25'))
        self.assertEqual(s.applicable(t,date(2026,1,11)).montant,30)
        self.nouvelle(lignes=[self.ligne(tarif=v,quantite=D('3'))])
        self.assertEqual(f.versions.first().lignes.get().prix,D('25.1250'))
    def test_tarif_devise_unite_categorie_et_prix_non_surcharges(self):
        t=self.tarif();v=t.versions.first()
        for kw in [dict(prix=D('5')),dict(unite='personne-nuit'),dict(categorie='adulte'),dict(devise='CHF')]:
            with self.assertRaises(ValidationError):
                self.enregistrer(devise=kw.pop('devise','EUR'),lignes=[self.ligne(tarif=v,**kw)])
        self.assertFalse(m.FinancementPrestation.objects.exists())
    def test_zero_explicite_et_negatifs_ou_inconnus_refuses(self):
        f=self.enregistrer(lignes=[self.ligne(prix=D('0'))],imputations=[])
        self.assertEqual(f.versions.first().lignes.get().montant,0)
        for kw in [dict(quantite=D('-1')),dict(prix=D('-1')),dict(quantite=None)]:
            with self.assertRaises(ValidationError):self.nouvelle(lignes=[self.ligne(**kw)],imputations=[])
        self.assertEqual(f.versions.count(),1)
    def test_dates_sources_et_periode_parent(self):
        for kw in [dict(debut=date(2025,12,1)),dict(fin=None),dict(fin=date(2026,3,1)),dict(source=''),dict(motif=''),dict(lignes=[]),dict(lignes=[self.ligne(date=date(2026,2,1))]),dict(lignes=[self.ligne(phase='realise',date=date(2099,1,1))])]:
            with self.assertRaises(ValidationError):self.enregistrer(**kw)
        self.assertFalse(m.FinancementPrestation.objects.exists())
    def test_cas_rejeu_et_rollbacks(self):
        token=s.jeton(self.accord);f=self.enregistrer(attendu=token)
        with self.assertRaises(ValidationError):self.nouvelle(attendu=token)
        with patch.object(m.LigneCout,'save',side_effect=RuntimeError('Stockage fictif indisponible')):
            with self.assertRaises(RuntimeError):self.nouvelle()
        self.assertEqual(f.versions.count(),1)
        self.nouvelle();self.assertEqual(f.versions.count(),2)
    def test_document_fige_coordonnees_calcul_et_statut_annulation(self):
        from . import partenaires
        partenaire=partenaires.creer(self.u,date(2026,1,1),'Source fictive',partenaires.jeton_creation(),nom='Payeur fictif',rue='Rue initiale fictive',code_postal='00100',ville='Ville fictive',pays='',telephone='',courriel='',fax='',informations='')
        self.enregistrer(facturation=partenaire);doc=self.emettre();photo=doc.contenu;sha=doc.empreinte
        self.nouvelle(lignes=[self.ligne(prix=D('99'))]);partenaire.fiches.update(rue='Nouvelle adresse fictive')
        doc.refresh_from_db();self.assertEqual(doc.contenu,photo);self.assertEqual(doc.empreinte,sha);self.assertIn('Rue initiale fictive',' '.join(photo['lignes']));self.assertNotIn('Nouvelle adresse',' '.join(photo['lignes']))
        s.annuler_document(self.u,self.accord,doc,s.jeton(self.accord),'Erreur fictive de montant')
        doc.refresh_from_db();self.assertEqual(doc.contenu,photo)
        nouveau=self.emettre(remplace=doc);self.assertNotEqual(doc.numero,nouveau.numero);self.assertEqual(nouveau.remplace,doc)
        with self.assertRaises(ValidationError):self.emettre(remplace=doc)
    def test_emission_phases_document_etranger_et_rejeu(self):
        self.enregistrer();token=s.jeton(self.accord);doc=self.emettre(attendu=token)
        for kw in [dict(attendu=token),dict(phase='prevu'),dict(modele='inconnu'),dict(date=date(2099,1,1)),dict(remplace=doc)]:
            with self.assertRaises(ValidationError):self.emettre(**kw)
        a=hebergement.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,2,1))
        with self.assertRaises(ValidationError):s.annuler_document(self.u,a,doc,s.jeton(a),'Fictif')
    def test_droits_explicitement_attribues_sans_suppression(self):
        self.assertFalse(self.u.is_staff);self.assertFalse(self.u.has_perm('personnes.delete_financementprestation'))
        self.u.user_permissions.remove(Permission.objects.get(codename='add_versionfinancement'));u=get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):s.enregistrer(u,self.accord,s.jeton(self.accord),'Fictif','definition',[],[])
        self.client.force_login(u);self.assertEqual(self.client.get(reverse('dossiers:financement_calcul',args=['hebergement',self.accord.pk])).status_code,403)
    def test_http_fiche_versions_tarifs_documents_et_csv(self):
        f=self.enregistrer();doc=self.emettre()
        for name,args,texte in [('financement',['hebergement',self.accord.pk],'50,25'),('financement_calcul',['hebergement',self.accord.pk],'Ajouter une composante'),('financement_emission',['hebergement',self.accord.pk],'Émettre'),('document_financement',[doc.pk],doc.numero),('tarifs',[],'Tarifs datés')]:
            response=self.client.get(reverse('dossiers:'+name,args=args));self.assertContains(response,texte);self.assertIn('no-store',response['Cache-Control'])
        self.nouvelle(lignes=[self.ligne(prix=D('30'))])
        rapport=reverse('dossiers:rapport_financements');params=dict(debut='2026-01-01',fin='2026-02-01',phase='autorise',mode='couts')
        page=self.client.get(rapport,params);self.assertEqual(page.context['totaux'],{'EUR':D('60')});self.assertEqual(len(page.context['lignes']),1)
        rows=list(csv.DictReader(StringIO(self.client.get(rapport,{**params,'format':'csv'}).content.decode()),delimiter=';'));self.assertEqual(rows[0]['montant'],'60.00')
        page=self.client.get(rapport,{**params,'mode':'imputations','financeur':self.org.pk});self.assertEqual(page.context['totaux'],{'EUR':D('30')})
        self.assertFalse(self.client.get(rapport,{**params,'financeur':self.org.pk}).context['form'].is_valid())
        self.assertEqual(len(self.client.get(rapport,{**params,'q':'Personne fictive D','reference':'FICTIF'}).context['lignes']),1)
        self.assertEqual(len(self.client.get(rapport,{**params,'reference':'AUTRE'}).context['lignes']),0)
        self.assertEqual(self.client.get(reverse('dossiers:financement',args=['hebergement',self.accord.pk]),{'version':'pas-un-entier'}).status_code,404)
    def _pdf(self,navigateur):
        self.enregistrer();doc=self.emettre()
        with override_settings(MODE_PWA=navigateur):
            r=self.client.get(reverse('dossiers:document_financement',args=[doc.pk]),{'format':'pdf'});self.assertEqual(r.status_code,200);self.assertTrue(r.content.startswith(b'%PDF-'));self.assertIn('no-store',r['Cache-Control'])
    def test_pdf_natif(self):self._pdf(False)
    def test_pdf_pwa(self):
        import importlib.util
        if not importlib.util.find_spec('fpdf'):self.skipTest('Dépendance facultative PWA fpdf2 absente.')
        self._pdf(True)
    def test_formulaires_typage_et_csrf(self):
        from .forms_financements import LigneForm
        f=LigneForm();self.assertEqual(f.fields['prix'].widget.attrs['inputmode'],'decimal');self.assertEqual(f.fields['date'].widget.attrs.get('type',f.fields['date'].widget.input_type),'date')
        c=Client(enforce_csrf_checks=True);c.force_login(self.u)
        self.assertEqual(c.post(reverse('dossiers:financement_calcul',args=['hebergement',self.accord.pk]),{}).status_code,403)
    def test_tarif_creation_rejouee_et_perime(self):
        token=s.creation_tarif();t=self.tarif();v=t.versions.first();d={c:getattr(v,c) for c in s.TARIF}
        s.definir_tarif(self.u,token,'Fictif',**d)
        with self.assertRaises(ValidationError):s.definir_tarif(self.u,token,'Rejeu fictif',**d)
        token=bd6.jeton(t);s.definir_tarif(self.u,token,'Fictif',tarif=t,action='correction',**d)
        with self.assertRaises(ValidationError):s.definir_tarif(self.u,token,'Fictif',tarif=t,action='correction',**d)
    def test_repas_et_aides_financables_sans_nouvelle_realisation(self):
        r=repas.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,2,1),'dejeuner');self.accord=r
        f=self.enregistrer();self.assertEqual(f.nature,'repas');self.assertFalse(r.realisations.exists())
        from .tests_meta_c import MetaCTests
        self.type=MetaCTests.type_creer(self);self.a.refresh_from_db()
        from . import aides
        a=aides.accorder(self.u,self.a,self.type,[self.p],bd6.jeton(self.a),debut=date(2026,1,1),fin=date(2026,2,1),quantite=D('5'),prestataire=None,financeur=None,valeur_bon=None,devise='EUR',source='Fictif');self.accord=a;f=self.enregistrer();self.assertEqual(f.nature,'aide');self.assertFalse(a.remises.exists())
    def donnees_post(self):
        return {'attendu':s.jeton(self.accord),'debut':'2026-01-01','fin':'2026-02-01','devise':'EUR','action':'definition','motif':'Définition fictive','source':'Source fictive','lignes-TOTAL_FORMS':'2','lignes-INITIAL_FORMS':'0','imputations-TOTAL_FORMS':'1','imputations-INITIAL_FORMS':'0',
            'lignes-0-phase':'autorise','lignes-0-date':'2026-01-05','lignes-0-libelle':'Chambre fictive','lignes-0-unite':'chambre-nuit','lignes-0-quantite':'2','lignes-0-prix':'25,1250','lignes-0-justification':'Décision fictive'}
    def test_http_enregistrement_complet_et_retour_sans_js(self):
        url=reverse('dossiers:financement_calcul',args=['hebergement',self.accord.pk]);d=self.donnees_post()
        r=self.client.post(url,d);self.assertEqual(r.status_code,302,r.content.decode())
        f=s.financement(self.accord);self.assertEqual(f.versions.first().lignes.get().montant,D('50.25'))
        doc=self.client.post(reverse('dossiers:financement_emission',args=['hebergement',self.accord.pk]),{'attendu':s.jeton(self.accord),'modele':'engagement','phase':'autorise','date':'2026-01-06'})
        self.assertEqual(doc.status_code,302);self.assertContains(self.client.get(doc.url),'PAP-')
    def test_http_ajout_ligne_et_reprise_volontaire_tarif(self):
        t=self.tarif();v=t.versions.first();url=reverse('dossiers:financement_calcul',args=['hebergement',self.accord.pk]);d=self.donnees_post()
        d.update(commande='tarifs',**{'lignes-0-tarif':str(v.pk),'lignes-0-prix':'','lignes-0-libelle':''})
        r=self.client.post(url,d);self.assertEqual(r.status_code,200);self.assertEqual(r.context['lignes'].forms[0]['prix'].value(),'25.1250');self.assertFalse(m.FinancementPrestation.objects.exists())
        d.update(commande='ligne');r=self.client.post(url,d);self.assertEqual(len(r.context['lignes'].forms),3)
        d.update(commande='tarifs',**{'lignes-TOTAL_FORMS':'invalide'});self.assertEqual(self.client.post(url,d).status_code,200)
    def test_fin_tarif_ne_ressuscite_pas_version_corrigee(self):
        t=self.tarif();v=t.versions.first();d={c:getattr(v,c) for c in s.TARIF};d['fin']=date(2026,1,10)
        s.definir_tarif(self.u,bd6.jeton(t),'Fin corrigée fictive',action='correction',tarif=t,**d)
        self.assertIsNone(s.applicable(t,date(2026,1,10)))
    def test_propositions_faits_collectifs_sans_multiplieur_ni_creation(self):
        from . import aides
        from .tests_meta_c import MetaCTests
        self.type=MetaCTests.type_creer(self)
        a=aides.accorder(self.u,self.a,self.type,[self.p],bd6.jeton(self.a),debut=date(2026,1,1),fin=date(2026,2,1),quantite=D('5'),prestataire=None,financeur=None,valeur_bon=None,devise='EUR',source='Fictif')
        aides.remettre(self.u,a,[self.p],date(2026,1,5),D('2'),'Remise fictive',bd6.jeton(a))
        ls=s.quantites_documentees(self.u,a,date(2026,1,1),date(2026,2,1));self.assertEqual(ls[0]['quantite'],2);self.assertIsNone(ls[0]['prix']);self.assertFalse(m.FinancementPrestation.objects.exists())
        sejour=hebergement.admettre(self.u,self.accord,[self.p],date(2026,1,1));hebergement.sortir(self.u,sejour,date(2026,1,5))
        ls=s.quantites_documentees(self.u,self.accord,date(2026,1,1),date(2026,2,1));self.assertEqual(ls[0]['quantite'],4);self.assertIn('Absences non déduites',ls[0]['justification'])
    def test_anciens_documents_illisibles_sans_droit_et_integrite(self):
        self.enregistrer();doc=self.emettre();u=get_user_model().objects.create_user('lecture-interdite-fictive');self.client.force_login(u)
        self.assertEqual(self.client.get(reverse('dossiers:document_financement',args=[doc.pk])).status_code,403)
        self.client.force_login(self.u)
        m.DocumentFinancement.objects.filter(pk=doc.pk).update(contenu={'titre':'Fictif altéré','lignes':[]})
        from .pdf_financements import produire
        doc.refresh_from_db()
        with self.assertRaises(ValidationError):produire(doc,navigateur=True)
    def test_devises_separees_et_csv_texte_non_interprete(self):
        self.enregistrer(lignes=[self.ligne(libelle='=FICTIF')]);a=self.accord
        self.accord=hebergement.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,2,1));self.enregistrer(devise='CHF',imputations=[])
        params=dict(debut='2026-01-01',fin='2026-02-01',phase='autorise',mode='couts');route=reverse('dossiers:rapport_financements')
        page=self.client.get(route,params);self.assertEqual(page.context['totaux'],{'EUR':D('50.25'),'CHF':D('50.25')})
        self.assertIn("'=FICTIF",self.client.get(route,{**params,'format':'csv'}).content.decode())
    def test_pdf_annule_et_erreur_caracteres_privee(self):
        self.enregistrer();doc=self.emettre();s.annuler_document(self.u,self.accord,doc,s.jeton(self.accord),'Erreur fictive')
        self.assertContains(self.client.get(reverse('dossiers:document_financement',args=[doc.pk])),'Document annulé')
        with patch('personnes.pdf_financements.produire',side_effect=ValueError('Diagnostic interne fictif')):
            r=self.client.get(reverse('dossiers:document_financement',args=[doc.pk]),{'format':'pdf'});self.assertEqual(r.status_code,422);self.assertNotIn('Diagnostic',r.content.decode());self.assertIn('no-store',r['Cache-Control'])


class MetaDTransactions(TransactionTestCase):
    setUp=MetaDTests.setUp
    ligne=MetaDTests.ligne
    imputation=MetaDTests.imputation
    enregistrer=MetaDTests.enregistrer
    emettre=MetaDTests.emettre
    def test_emission_concurrente_un_seul_numero_et_aucune_double_confirmation(self):
        import threading
        from django.db import close_old_connections,connections,OperationalError
        from time import sleep
        self.enregistrer();token=s.jeton(self.accord);barriere=threading.Barrier(2);resultats=[];erreurs=[];refus=[]
        revision=s.financement(self.accord).revision_sociale
        def travail():
            close_old_connections()
            try:
                u=get_user_model().objects.get(pk=self.u.pk);a=m.AccordHebergement.objects.get(pk=self.accord.pk);u.get_all_permissions();barriere.wait(timeout=10)
                # Le cache partagé SQLite des tests peut refuser les DEUX
                # transactions. Rejouer seulement ce verrou transitoire après
                # rollback, avec le même jeton : le CAS doit toujours départager.
                for tentative in range(6):
                    try:
                        s.emettre(u,a,token,'engagement','autorise',date(2026,1,6))
                        resultats.append(True);break
                    except ValidationError as erreur:
                        refus.append(str(erreur));resultats.append(False);break
                    except OperationalError as erreur:
                        if connections['default'].vendor!='sqlite' or 'locked' not in str(erreur).lower() or tentative==5:raise
                        sleep(.01*(tentative+1))
            except Exception as e:erreurs.append(e)
            finally:connections.close_all()
        ts=[threading.Thread(target=travail) for _ in range(2)]
        for t in ts:t.start()
        for t in ts:t.join(20)
        self.assertFalse(any(t.is_alive() for t in ts));self.assertFalse(erreurs,erreurs);self.assertEqual(sum(resultats),1,resultats);self.assertEqual(m.DocumentFinancement.objects.count(),1)
        self.assertEqual(len(refus),1,refus)
        self.assertEqual(s.financement(self.accord).revision_sociale,revision+1)
    def test_emission_concurrente_rejoue_verrou_sqlite_sans_rafraichir_confirmation(self):
        import threading
        from django.db import connection,OperationalError
        if connection.vendor!='sqlite':self.skipTest('Verrou transitoire SQLite.')
        local=threading.local();emettre=s.emettre
        def premier_verrou(*args,**kwargs):
            if not getattr(local,'tente',False):
                local.tente=True
                raise OperationalError('database table is locked: personnes_menage')
            return emettre(*args,**kwargs)
        with patch.object(s,'emettre',side_effect=premier_verrou):
            self.test_emission_concurrente_un_seul_numero_et_aucune_double_confirmation()
    def test_copie_sqlite_conserve_versions_document_et_annulation(self):
        import sqlite3,tempfile,json
        from pathlib import Path
        from django.db import connection
        if connection.vendor!='sqlite':self.skipTest('Recette SQLite.')
        self.enregistrer();doc=self.emettre();s.annuler_document(self.u,self.accord,doc,s.jeton(self.accord),'Correction fictive')
        with tempfile.TemporaryDirectory() as tmp:
            with closing(sqlite3.connect(Path(tmp)/'copie.sqlite3')) as db, db:connection.connection.backup(db)
            with closing(sqlite3.connect(Path(tmp)/'copie.sqlite3')) as db, db:
                contenu,sha=db.execute('SELECT contenu, empreinte FROM personnes_documentfinancement').fetchone();self.assertEqual(s.empreinte(json.loads(contenu)),sha)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM personnes_versionfinancement').fetchone()[0],1)
                self.assertEqual(db.execute('SELECT motif FROM personnes_annulationdocument').fetchone()[0],'Correction fictive')
            with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
    def test_migration_sans_financement_ni_droits_inventes(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        ex=MigrationExecutor(connection);latest=ex.loader.graph.leaf_nodes();old=[('personnes','0031_correction_continuite')]
        avant=m.AccordHebergement.objects.count()
        try:
            ex.migrate(old)
            apps=ex.loader.project_state(old).apps
            self.assertEqual(apps.get_model('personnes','AccordHebergement').objects.count(),avant)
        finally:MigrationExecutor(connection).migrate(latest)
        self.assertEqual(m.AccordHebergement.objects.count(),avant);self.assertFalse(m.FinancementPrestation.objects.exists());self.assertFalse(m.TarifPrestation.objects.exists())
