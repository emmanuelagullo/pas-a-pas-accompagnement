from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
import csv,json
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError,PermissionDenied
from django.core.management import call_command
from django.test import TestCase,TransactionTestCase,Client
from django.urls import reverse
from . import dossier_complet as s,bd6,models as m


def valeurs(code,**kw):
    r=s.RUBRIQUES[code]
    d={c:r.modele._meta.get_field(c).get_default() for c in r.champs}
    d.update(etat='detail')
    d.update({'evolutions':dict(libelle='Évolution fictive déclarée'), 'territoires':dict(type_territoire='agglomeration',territoire='Territoire fictif'), 'antecedents':dict(libelle='Passage institutionnel fictif de recette'), 'besoins':dict(categorie='mobilite',libelle='Besoin fictif'),
        'ressources':dict(libelle='Salaire fictif',montant=Decimal('800.50'),periodicite='mensuelle'),
        'dettes':dict(creancier='Créancier fictif',montant=Decimal('1000.25')),
        'pieces':dict(type_document='Pièce fictive',reference='DOC-FICTIF'),
        'couvertures':dict(libelle='Couverture fictive',regime='Régime fictif'),
        'protections':dict(mesure='Mesure fictive',domaine='biens')}[code]);d.update(kw)
    return d


def administration(**kw):
    d={c:m.SituationAdministrative._meta.get_field(c).get_default() for c in s.ADMIN_CHAMPS}
    d.update(numero_ss='000 FICTIF SS',numero_caf='000 FICTIF CAF',qualification='Qualification fictive')
    d.update(kw);return d


class DossierCompletTests(TestCase):
    def setUp(self):
        self.u=get_user_model().objects.create_user('dossier-complet-fictif')
        call_command('autoriser_chrs7',self.u.username,stdout=StringIO());call_command('autoriser_solenne',self.u.username,stdout=StringIO());call_command('autoriser_bd6',self.u.username,stdout=StringIO())
        self.u=get_user_model().objects.get(pk=self.u.pk);self.client.force_login(self.u)
        self.p=m.Personne.objects.create(designation='Personne fictive',cree_par=self.u)
        self.q=m.Personne.objects.create(designation='Autre personne fictive',cree_par=self.u)

    def ajouter(self,code,**kw):
        v=dict(debut=date(2026,1,1),fin=None,source='Entretien fictif',attendu=bd6.jeton(self.p));v.update(kw)
        return s.enregistrer(self.u,code,self.p,**v)

    def test_toutes_rubriques_changement_correction_fin_annulation(self):
        for code,r in s.RUBRIQUES.items():
            with self.subTest(code=code):
                v=valeurs(code);x=self.ajouter(code,**v);ancien=bd6.jeton(self.p)
                nouveau=valeurs(code)
                nouveau[r.libelle]='Libellé changé fictif'
                y=self.ajouter(code,debut=date(2026,2,1),remplace=x.pk,**nouveau)
                x.refresh_from_db();self.assertEqual(x.fin,date(2026,2,1))
                with self.assertRaises(ValidationError):self.ajouter(code,attendu=ancien,**v)
                self.ajouter(code,debut=y.debut,fin=date(2026,3,1),correction=y.pk,cloture=True,motif='Fin réelle fictive',**nouveau)
                self.ajouter(code,debut=y.debut,fin=date(2026,2,20),correction=y.pk,motif='Erreur de fin fictive',**nouveau)
                s.annuler(self.u,code,self.p,y,'Mauvaise déclaration fictive',bd6.jeton(self.p))
                self.assertFalse(s.a_date(code,[self.p],date(2026,2,10)).exists())
                self.assertEqual(list(r.journal.objects.values_list('action',flat=True))[:4],['annulation','correction','cloture','changement'])

    def test_montants_types_et_total_non_double_compte(self):
        a=self.ajouter('ressources',**valeurs('ressources',montant=Decimal('0')))
        self.ajouter('ressources',**valeurs('ressources',libelle='Autre revenu fictif',montant=None))
        self.ajouter('ressources',**valeurs('ressources',libelle='Revenu annuel fictif',montant=Decimal('100'),periodicite='annuelle'))
        self.ajouter('ressources',**valeurs('ressources',libelle='Revenu étranger fictif',montant=Decimal('10'),devise='USD'))
        self.assertEqual(s.totaux('ressources',s.a_date('ressources',[self.p],date(2026,1,2))),[('EUR','mensuelles connues',Decimal('0.00')),('USD','mensuelles connues',Decimal('10.00'))])
        self.ajouter('dettes',**valeurs('dettes',montant=Decimal('100')))
        self.ajouter('dettes',**valeurs('dettes',nature='total',creancier='',montant=Decimal('200')))
        self.assertEqual(s.totaux('dettes',s.a_date('dettes',[self.p],date(2026,1,2))),[('EUR','détails connus',Decimal('100')),('EUR','total déclaré',Decimal('200'))])
        for code in ('ressources','dettes'):
            with self.assertRaises(ValidationError):self.ajouter(code,**valeurs(code,montant=Decimal('-1')))
        self.assertEqual(m.Appartenance.objects.count(),0);self.assertEqual(m.Accompagnement.objects.count(),0)

    def test_absence_globale_explicitement_confirmee_et_rollback(self):
        x=self.ajouter('ressources',**valeurs('ressources'))
        y=self.ajouter('ressources',**valeurs('ressources',libelle='Allocation fictive'))
        v=valeurs('ressources',etat='aucun',libelle='',montant=None,periodicite='')
        with self.assertRaises(ValidationError):self.ajouter('ressources',debut=date(2026,2,1),**v)
        n=self.ajouter('ressources',debut=date(2026,2,1),remplacer_ensemble=True,**v)
        x.refresh_from_db();y.refresh_from_db();self.assertEqual(x.fin,date(2026,2,1));self.assertEqual(y.fin,x.fin)
        self.assertEqual(s.a_date('ressources',[self.p],date(2026,1,31)).count(),2)
        self.assertEqual(s.a_date('ressources',[self.p],date(2026,2,1)).get(),n)
        self.assertEqual(len(m.RevisionRessourcePersonnelle.objects.first().avant),2)
        with self.assertRaises(ValidationError):self.ajouter('ressources',debut=date(2026,3,1),**valeurs('ressources'))

    def test_dates_futures_periodes_et_rollback_du_journal(self):
        for code,r in s.RUBRIQUES.items():
            with self.subTest(code=code):
                with self.assertRaises(ValidationError):self.ajouter(code,debut=date(9999,1,1),**valeurs(code))
                with self.assertRaises(ValidationError):self.ajouter(code,fin=date(2025,12,1),**valeurs(code))
                with patch.object(r.journal.objects,'create',side_effect=RuntimeError('Fictif')):
                    with self.assertRaises(RuntimeError):self.ajouter(code,**valeurs(code))
                self.assertFalse(r.modele.objects.exists())

    def test_administration_dates_precises_identifiants_et_correction(self):
        v=administration(sans_emploi_depuis=date(2025,2,1),precision_sans_emploi='estimee',droit_sejour='Déclaré fictif',echeance_sejour=date(2027,1,1))
        x=s.administration(self.u,self.p,date(2026,1,1),'Fictif',bd6.jeton(self.p),**v)
        y=s.administration(self.u,self.p,date(2026,3,1),'Fictif',bd6.jeton(self.p),**administration(numero_caf='001 NOUVEAU FICTIF'))
        s.administration(self.u,self.p,date(2026,2,1),'Fictif',bd6.jeton(self.p),correction=y.pk,motif='Date erronée fictive',**administration(numero_caf='001 NOUVEAU FICTIF'))
        self.assertEqual(s.administration_a_date([self.p],date(2026,1,31)).get(),x)
        self.assertEqual(m.RevisionSituationAdministrative.objects.last().apres[0]['sans_emploi_depuis'],'2025-02-01')
        self.assertEqual(m.RevisionSituationAdministrative.objects.last().apres[0]['numero_ss'],'000 FICTIF SS')
        for v in (administration(sans_emploi_depuis=date(2025,1,1)),administration(sans_domicile_depuis=date(2027,1,1),precision_sans_domicile='exacte')):
            with self.assertRaises(ValidationError):s.administration(self.u,self.p,date(2026,4,1),'Fictif',bd6.jeton(self.p),**v)

    def test_representants_distincts_et_echeances_sans_effet_automatique(self):
        x=self.ajouter('protections',**valeurs('protections',representant_personne=self.q,echeance_prevue=date(2026,1,2)))
        self.assertEqual(s.a_date('protections',[self.p],date(2026,2,1)).get(),x)
        with self.assertRaises(ValidationError):self.ajouter('protections',**valeurs('protections',representant_personne=self.p))
        with self.assertRaises(ValidationError):self.ajouter('protections',**valeurs('protections',date_decision=date(9999,1,1)))
        self.assertFalse(m.RelationPersonnelle.objects.exists());self.assertFalse(m.ContactMenage.objects.exists())

    def test_http_tous_formulaires_et_valeurs_francaises(self):
        for code,r in s.RUBRIQUES.items():
            with self.subTest(code=code):
                url=reverse('dossiers:fait_a_nouveau',args=[self.p.pk,code]);page=self.client.get(url)
                self.assertEqual(page.status_code,200)
                d=valeurs(code);d.update(debut='2026-01-01',fin='',source='Fictif',attendu=page.context['form'].initial['attendu'])
                d={k:('' if v is None else v) for k,v in d.items()}
                if code in ('ressources','dettes'):d['montant']='1234,50'
                rpost=self.client.post(url,d);self.assertEqual(rpost.status_code,302,rpost.content)
                if code in ('ressources','dettes'):self.assertEqual(r.modele.objects.get().montant,Decimal('1234.50'))
                self.assertEqual(self.client.get(rpost.url).status_code,200)

    def test_rapports_csv_filtres_droits_et_unites(self):
        self.ajouter('ressources',**valeurs('ressources'))
        self.ajouter('ressources',**valeurs('ressources',libelle='Autre revenu fictif',montant=None))
        url=reverse('dossiers:rapport_a');params={'date':'2026-01-02','rubrique':'ressources','montant_min':'800','devise':'eur'}
        page=self.client.get(url,params);self.assertEqual(page.status_code,200);self.assertEqual(page.context['nombre'],1)
        rows=list(csv.DictReader(StringIO(self.client.get(url,{**params,'format':'csv'}).content.decode()),delimiter=';'))
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['montant'],'800.50');self.assertEqual(rows[0]['devise'],'EUR')
        s.administration(self.u,self.p,date(2026,1,1),'Fictif',bd6.jeton(self.p),**administration())
        csv1=self.client.get(url,{'rubrique':'administration','date':'2026-01-02','format':'csv'}).content.decode()
        self.assertNotIn('FICTIF SS',csv1)
        csv2=self.client.get(url,{'rubrique':'administration','date':'2026-01-02','format':'csv','identifiants':'on'}).content.decode()
        self.assertIn('FICTIF SS',csv2)
        self.u.user_permissions.remove(Permission.objects.get(codename='view_ressourcepersonnelle'))
        self.assertEqual(self.client.get(reverse('dossiers:fait_a_nouveau',args=[self.p.pk,'ressources'])).status_code,403)
        self.assertEqual(self.client.get(url,params).status_code,403)

    def test_csrf_saisie_perimee_cible_etrangere_et_droits_separes(self):
        url=reverse('dossiers:fait_a_nouveau',args=[self.p.pk,'pieces']);f=self.client.get(url).context['form']
        d={k:('' if v is None else v) for k,v in valeurs('pieces').items()};d.update(debut='2026-01-01',fin='',source='Fictif',attendu=f.initial['attendu'])
        c=Client(enforce_csrf_checks=True);c.force_login(self.u);self.assertEqual(c.post(url,d).status_code,403)
        self.assertEqual(self.client.post(url,d).status_code,302)
        self.assertEqual(self.client.post(url,d).status_code,409)
        x=m.PieceAdministrative.objects.get()
        with self.assertRaises(ValidationError):s.enregistrer(self.u,'pieces',self.q,x.debut,None,'Fictif',bd6.jeton(self.q),correction=x.pk,motif='Fictif',**valeurs('pieces'))
        self.u.user_permissions.remove(Permission.objects.get(codename='add_pieceadministrative'))
        self.u=get_user_model().objects.get(pk=self.u.pk)
        s.annuler(self.u,'pieces',self.p,x,'Mauvaise saisie fictive',bd6.jeton(self.p))
        self.assertFalse(s.a_date('pieces',[self.p],date(2026,1,2)).exists())

    def test_dossier_bd_projection_sans_double_saisie_et_retours(self):
        from . import suivi
        menage=suivi.creer_menage(self.u,'Ménage fictif',[self.p],date(2026,1,1))
        a=suivi.ouvrir(self.u,menage,[self.p],date(2026,1,1))
        bd6.renseigner(self.u,self.p,'ressources','inconnu',date(2026,1,1),'Ancienne déclaration fictive',bd6.jeton(self.p))
        self.ajouter('ressources',**valeurs('ressources'))
        entree=bd6.etat(self.u,[self.p],date(2026,1,2))[0]
        ligne=next(v for v in entree['lignes'] if v['dimension']=='ressources')
        self.assertEqual(ligne['texte'],'Ressources déclarées');self.assertIsNotNone(ligne['projection'])
        self.assertEqual(m.SituationPersonnelle.objects.get().valeur,'inconnu')
        url=reverse('dossiers:prise',args=['menage',menage.pk,a.pk]);page=self.client.get(url)
        self.assertContains(page,'Ressources');self.assertContains(page,'Dettes');self.assertContains(page,'Administration et droits')
        page=self.client.get(reverse('dossiers:fiche_a',args=[self.p.pk,'economique']),{'depuis_nature':'menage','depuis_pk':menage.pk,'depuis_prise':a.pk,'q':'Recherche fictive','page':'2','date':'2026-01-02'})
        self.assertIn(url,page.context['retour']);self.assertIn('Recherche+fictive',page.context['retour'])
        self.u.user_permissions.remove(Permission.objects.get(codename='view_ressourcepersonnelle'))
        self.u=get_user_model().objects.get(pk=self.u.pk)
        ligne=next(v for v in bd6.etat(self.u,[self.p],date(2026,1,2))[0]['lignes'] if v['dimension']=='ressources')
        self.assertIsNone(ligne['projection']);self.assertEqual(ligne['texte'],'Non renseigné')

    def test_formulaire_absence_demande_confirmation_et_propositions(self):
        from . import propositions
        x=self.ajouter('ressources',**valeurs('ressources'))
        url=reverse('dossiers:fait_a_absence',args=[self.p.pk,'ressources']);page=self.client.get(url)
        d=dict(debut='2026-02-01',fin='',etat='aucun',source='Fictif',attendu=page.context['form'].initial['attendu'])
        self.assertEqual(self.client.post(url,d).status_code,200)
        self.assertIsNone(m.RessourcePersonnelle.objects.get(pk=x.pk).fin)
        d['remplacer_ensemble']='on'
        self.assertEqual(self.client.post(url,d).status_code,302)
        self.assertEqual(s.a_date('ressources',[self.p],date(2026,2,1)).get().etat,'aucun')
        propositions.enregistrer(self.u,'nature_ressource','Nature proposée fictive',True,'Préparation fictive')
        self.assertContains(self.client.get(reverse('dossiers:fait_a_nouveau',args=[self.p.pk,'ressources'])),'<option value="Nature proposée fictive">')

    def test_changement_invalide_et_noop_decimal(self):
        x=self.ajouter('ressources',**valeurs('ressources'))
        self.ajouter('ressources',**valeurs('ressources',libelle='Autre poste fictif'))
        with self.assertRaisesMessage(ValidationError,'Aucune modification'):self.ajouter('ressources',correction=x.pk,motif='Fictif',**valeurs('ressources',montant=Decimal('800.5')))
        with self.assertRaises(ValidationError):self.ajouter('ressources',debut=date(2026,2,1),remplace=x.pk,**valeurs('ressources',libelle='Autre poste fictif'))
        x.refresh_from_db();self.assertIsNone(x.fin)
        self.assertEqual(m.RessourcePersonnelle.objects.count(),2)

    def test_recherche_interdite_n_expose_pas_le_repertoire(self):
        self.u.user_permissions.set(Permission.objects.filter(codename__in=['view_personne','view_pieceadministrative','view_revisionpieceadministrative']))
        response=self.client.get(reverse('dossiers:rapport_a'),{'rubrique':'protections'})
        self.assertEqual(response.status_code,403)
        response=self.client.get(reverse('dossiers:rapport_a'),{'rubrique':'pieces'})
        self.assertEqual(response.status_code,200);self.assertNotContains(response,'name="organisme"')

    def test_couvertures_contacts_dates_et_representants_distincts(self):
        from . import partenaires,intervenants
        from .tests_partenaires import valeurs as organisation
        from .tests_interventions import valeurs as professionnel
        org=partenaires.creer(self.u,date(2026,1,1),'Fictif',partenaires.jeton_creation(),**organisation())
        pro=intervenants.creer(self.u,date(2026,1,1),'Fictif',intervenants.jeton_creation(),**professionnel(telephone='+00 ANCIEN fictif'))
        contact=intervenants.creer(self.u,date(2026,1,1),'Fictif',intervenants.jeton_creation(),**professionnel(nom='Contact fictif distinct'))
        intervenants.renseigner(self.u,pro,date(2026,2,1),'Fictif',bd6.jeton(pro),**professionnel(telephone='+00 NOUVEAU fictif'))
        x=self.ajouter('protections',**valeurs('protections',representant_intervenant=pro,interlocuteur=contact))
        page=self.client.get(reverse('dossiers:fiche_a',args=[self.p.pk,'droits']),{'date':'2026-01-02','rubrique':'protections'})
        self.assertContains(page,'ANCIEN fictif');self.assertNotContains(page,'NOUVEAU fictif');self.assertContains(page,'Contact fictif distinct')
        self.assertEqual(page.context['parametres_fiche']['rubrique'],'protections')
        with self.assertRaises(ValidationError):self.ajouter('protections',**valeurs('protections',representant_intervenant=pro,organisme=org))
        self.assertEqual(m.ProtectionJuridique.objects.count(),1)

    def test_prevision_n_expire_pas_et_lignes_absentes_ne_sont_pas_zeros(self):
        x=self.ajouter('pieces',**valeurs('pieces',echeance_prevue=date(2026,1,2)))
        response=self.client.get(reverse('dossiers:fiche_a',args=[self.p.pk,'droits']),{'date':'2026-03-01','rubrique':'pieces'})
        self.assertContains(response,'Échéance annoncée atteinte ou passée');self.assertEqual(len(response.context['blocs'][0]['actifs']),1)
        rapport=self.client.get(reverse('dossiers:rapport_a'),{'rubrique':'pieces','date':'2026-03-01','echeance_avant':'2026-02-01'})
        self.assertEqual(rapport.context['nombre'],1)
        self.assertNotContains(rapport,'Autre personne fictive')


class ConcurrenceDossierCompletTests(TransactionTestCase):
    def preparer(self):
        self.u=get_user_model().objects.create_user('dossier-concurrent-fictif')
        call_command('autoriser_solenne',self.u.username,stdout=StringIO())
        self.u.user_permissions.add(Permission.objects.get(codename='view_personne'))
        self.u=get_user_model().objects.get(pk=self.u.pk)
        self.p=m.Personne.objects.create(designation='Personne fictive de copie',cree_par=self.u)

    def test_deux_saisies_un_seul_poste_et_journal(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections,connections,OperationalError
        self.preparer();jeton=bd6.jeton(self.p);depart=Barrier(2)
        def ecrire(_):
            close_old_connections()
            try:
                u=get_user_model().objects.get(pk=self.u.pk);u.get_all_permissions();p=m.Personne.objects.get(pk=self.p.pk)
                depart.wait(timeout=10)
                try:
                    s.enregistrer(u,'ressources',p,date(2026,1,1),None,'Fictif',jeton,**valeurs('ressources'))
                    return True
                except (ValidationError,OperationalError):return False
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:r=list(pool.map(ecrire,range(2)))
        self.assertEqual(sum(r),1,r);self.assertEqual(m.RessourcePersonnelle.objects.count(),1);self.assertEqual(m.RevisionRessourcePersonnelle.objects.count(),1)

    def test_copie_restauree_conserve_montants_dates_et_annulations(self):
        import sqlite3
        from contextlib import closing
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.db import connection
        from pas_communs.paquets import creer_sauvegarde
        from pas_a_pas_accompagnement import paquets
        if connection.vendor!='sqlite':self.skipTest('Copie locale SQLite uniquement.')
        self.preparer()
        for code,r in s.RUBRIQUES.items():
            x=s.enregistrer(self.u,code,self.p,date(2026,1,1),None,'Fictif',bd6.jeton(self.p),**valeurs(code))
            s.annuler(self.u,code,self.p,x,'Erreur fictive de test',bd6.jeton(self.p))
        s.administration(self.u,self.p,date(2026,1,1),'Fictif',bd6.jeton(self.p),**administration(sans_emploi_duree_declaree='Six mois déclarés'))
        with TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir();(source/'secret-key').write_text('cle-fictive-dossier-complet')
            with closing(sqlite3.connect(source/paquets.PROFIL.base)) as copie:connection.connection.backup(copie)
            archive=root/'copie.zip';creer_sauvegarde(source,archive,profil=paquets.PROFIL)
            preparation=paquets.verifier(archive,root,'preparation');destination=root/'restauree';paquets.installer_copie(preparation,destination)
            with closing(sqlite3.connect(destination/paquets.PROFIL.base)) as db:
                self.assertEqual(Decimal(str(db.execute('SELECT montant FROM personnes_ressourcepersonnelle').fetchone()[0])),Decimal('800.5'))
                self.assertEqual(db.execute('SELECT numero_ss,sans_emploi_duree_declaree FROM personnes_situationadministrative').fetchone(),('000 FICTIF SS','Six mois déclarés'))
                for r in s.RUBRIQUES.values():
                    self.assertEqual(db.execute('SELECT motif_annulation FROM '+r.modele._meta.db_table).fetchone(),('Erreur fictive de test',))
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM '+r.journal._meta.db_table).fetchone(),(2,))

    def test_migration_conserve_l_existant_sans_inventer_declarations(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        if connection.vendor!='sqlite':self.skipTest('Recette locale de migration SQLite.')
        u=get_user_model().objects.create_user('migration-a-fictive')
        executor=MigrationExecutor(connection);cibles=executor.loader.graph.leaf_nodes()
        ancienne=[('personnes','0024_identite_et_relations')]
        try:
            executor.migrate(ancienne)
            apps=executor.loader.project_state(ancienne).apps
            P=apps.get_model('personnes','Personne');C=apps.get_model('personnes','ComplementIdentite')
            p=P.objects.create(designation='Identité ancienne fictive',cree_par_id=u.pk,precision_naissance='annee',annee_naissance=1980)
            C.objects.create(personne_id=p.pk,debut=date(2026,1,1),source='Ancienne déclaration fictive',nationalites=['Nationalité fictive conservée'],auteur_id=u.pk)
            pk=p.pk
        finally:
            MigrationExecutor(connection).migrate(cibles)
        self.assertEqual(m.Personne.objects.get(pk=pk).annee_naissance,1980)
        self.assertEqual(m.ComplementIdentite.objects.get(personne_id=pk).nationalites,['Nationalité fictive conservée'])
        self.assertFalse(m.SituationAdministrative.objects.exists())
        for r in s.RUBRIQUES.values():self.assertFalse(r.modele.objects.exists())
        self.assertFalse(get_user_model().objects.get(pk=u.pk).user_permissions.exists())
