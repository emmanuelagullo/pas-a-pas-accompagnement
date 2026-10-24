from datetime import date,time
from decimal import Decimal as D
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError,PermissionDenied
from django.core.management import call_command
from django.test import TestCase,TransactionTestCase,Client,override_settings
from django.urls import reverse
from django.utils import timezone
from . import models as m,appels115 as s,bd6,suivi,transmissions as t,releve,exploration as e


def autoriser(u):
    call_command('autoriser_chrs7',u.username,stdout=StringIO());call_command('autoriser_solenne',u.username,stdout=StringIO())
    for p in ('transmission','notepartagee','actionrelais'):u.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes',codename__in=['view_'+p,'add_'+p,'change_'+p]))
    return get_user_model().objects.get(pk=u.pk)


class MetaETests(TestCase):
    def setUp(self):
        self.u=autoriser(get_user_model().objects.create_user('recette-e-fictive'))
        self.p=m.Personne.objects.create(designation='Personne fictive E',cree_par=self.u)
        self.m=suivi.creer_menage(self.u,'Ménage fictif E',[self.p],date(2026,1,1));self.a=suivi.ouvrir(self.u,self.m,[self.p],date(2026,1,1))
        self.client.force_login(self.u)
    def donnees(self,**kw):
        d={c:m.VersionAppel115._meta.get_field(c).get_default() for c in s.CHAMPS}
        d.update(date=date(2026,1,5),heure=time(23,59,59),type_appelant='inconnu',motif_principal='Hébergement fictif',details='Appel fictif',etat_reponse='inconnue',demandes_secondaires=['Repas fictif','Transport fictif'],reponses=[],source='Appel fictif écouté');d.update(kw);return d
    def creer(self,**kw):return s.ecrire(self.u,s.creation(),[],action='saisie',**self.donnees(**kw))
    def config(self,**kw):
        d=dict(population='appels',debut=date(2026,1,1),fin=date(2026,2,1),reference=date(2026,1,31),mesure='objets',axe='total',croisement='',classes='',filtre1='',operation1='egal',valeur1='',filtre2='',operation2='egal',valeur2='');d.update(kw);return d
    def test_anonyme_ne_cree_pas_de_personne_menage_prise_ou_sejour(self):
        avant=(m.Personne.objects.count(),m.Menage.objects.count(),m.Accompagnement.objects.count())
        a=self.creer();self.assertFalse(a.versions.first().beneficiaires.exists());self.assertFalse(m.Sejour.objects.exists());self.assertEqual(avant,(m.Personne.objects.count(),m.Menage.objects.count(),m.Accompagnement.objects.count()))
        self.assertEqual(a.versions.first().heure,time(23,59,59))
    def test_identification_ulterieure_versions_et_appels_repetes(self):
        a=self.creer();token=s.jeton(a)
        s.ecrire(self.u,token,[self.p],appel=a,action='suite',motif='Identification ultérieure fictive',**self.donnees(type_appelant='personne',appelant_personne=self.p))
        self.assertEqual(a.versions.count(),2);self.assertFalse(a.versions.get(version=1).beneficiaires.exists());self.assertTrue(a.versions.first().beneficiaires.filter(pk=self.p.pk).exists())
        self.creer();self.assertEqual(m.Appel115.objects.count(),2)
        with self.assertRaises(ValidationError):s.ecrire(self.u,s.jeton(a),[self.p],appel=a,action='suite',motif='Fictif',**self.donnees(date=date(2026,1,6)))
        with self.assertRaises(ValidationError):s.ecrire(self.u,token,[],appel=a,action='correction',motif='Fictif',**self.donnees())
    def test_zero_effectifs_inconnus_listes_tiers_et_reponses(self):
        a=self.creer(adultes_declares=0,enfants_declares=None);self.assertEqual(a.versions.first().adultes_declares,0)
        for kw in [dict(date=date(2099,1,1)),dict(source=''),dict(demandes_secondaires=['Repas','repas']),dict(reponses=['Conseil fictif']),dict(type_appelant='inconnu',appelant_personne=self.p),dict(adultes_declares=-1)]:
            with self.assertRaises(ValidationError):self.creer(**kw)
        a=self.creer(type_appelant='tiers',appelant_libre='Proche fictif',etat_reponse='apportee',reponses=['Conseil fictif','Orientation fictive'])
        self.assertEqual(len(a.versions.first().reponses),2)
    def test_liens_explicitement_controles_pas_admission(self):
        a=self.creer();v=a.versions.first()
        with self.assertRaises(ValidationError):s.lier(self.u,a,s.jeton(a),'Fictif',accompagnement=self.a)
        s.ecrire(self.u,s.jeton(a),[self.p],appel=a,action='suite',motif='Identité fictive confirmée',**self.donnees())
        l=s.lier(self.u,a,s.jeton(a),'Prise existante fictive',accompagnement=self.a);self.assertFalse(m.Sejour.objects.exists())
        with self.assertRaises(ValidationError):s.ecrire(self.u,s.jeton(a),[],appel=a,action='correction',motif='Fictif',**self.donnees())
        with self.assertRaises(ValidationError):s.annuler(self.u,a,s.jeton(a),'Fictif')
        s.delier(self.u,a,l,s.jeton(a),'Lien attribué par erreur fictive');s.annuler(self.u,a,s.jeton(a),'Appel de test en double fictif');self.assertEqual(a.revisions.count(),1)
    def test_journal_atomique_et_creation_rejouee(self):
        token=s.creation();a=s.ecrire(self.u,token,[],action='saisie',**self.donnees())
        with self.assertRaises(ValidationError):s.ecrire(self.u,token,[],action='saisie',**self.donnees())
        with patch.object(m.VersionAppel115,'save',side_effect=RuntimeError('Stockage fictif indisponible')):
            with self.assertRaises(RuntimeError):s.ecrire(self.u,s.jeton(a),[],appel=a,action='correction',motif='Fictif',**self.donnees())
        self.assertEqual(a.versions.count(),1)
    def test_http_saisie_fiche_correction_lien_journal(self):
        nouveau=reverse('dossiers:appel115_nouveau');page=self.client.get(nouveau);self.assertEqual(page.status_code,200)
        d={**self.donnees(),'attendu':page.context['form'].initial['attendu'],'action':'saisie'}
        for c in ('appelant_personne','appelant_intervenant','appelant_organisme','menage','orientation','adultes_declares','enfants_declares','grossesses_declarees'):d[c]=''
        d.update(demandes_secondaires='Repas fictif\nTransport fictif',reponses='',date='2026-01-05',heure='23:59:59')
        r=self.client.post(nouveau,d);self.assertEqual(r.status_code,302,r.content.decode());self.assertContains(self.client.get(r.url),'23:59:59')
        a=m.Appel115.objects.get();self.assertContains(self.client.get(reverse('dossiers:appel115_modifier',args=[a.pk])),'correction')
        self.assertEqual(self.client.get(reverse('dossiers:appel115_lier',args=[a.pk])).status_code,200)
        r=self.client.get(reverse('dossiers:appels115'),{'debut':'2026-01-01','fin':'2026-02-01','heure_min':'23','heure_max':'24'});self.assertEqual(len(r.context['page_obj']),1)
    def test_lecture_appel_sous_droits_des_cibles_et_csrf(self):
        a=self.creer();s.ecrire(self.u,s.jeton(a),[self.p],appel=a,action='suite',motif='Fictif',**self.donnees())
        self.u.user_permissions.remove(Permission.objects.get(codename='view_personne'));u=get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):s.lire(u,a)
        c=Client(enforce_csrf_checks=True);c.force_login(self.u);self.assertEqual(c.post(reverse('dossiers:appel115_nouveau'),{}).status_code,403)
    def test_corrections_date_contribution_histoire_et_annulation(self):
        x=t.transmettre(self.u,'Texte fictif',date(2026,1,5));ancien=t.jeton(x)
        t.rectifier(self.u,x,'Texte fictif','Date saisie incorrectement',etat_attendu=ancien,date_fait=date(2026,1,4))
        x.refresh_from_db();self.assertEqual(x.revisions.get().ancienne_date,date(2026,1,5));self.assertEqual(releve.date_de(x),date(2026,1,4))
        with self.assertRaises(ValidationError):t.annuler(self.u,x,ancien,'Fictif')
        t.annuler(self.u,x,t.jeton(x),'Mauvais cahier fictif');self.assertEqual(len(releve.contributions(self.u)),0);self.assertEqual(len(releve.contributions(self.u,annules=True)),1)
        with self.assertRaises(ValidationError):t.rectifier(self.u,x,'Autre texte','Fictif',etat_attendu=t.jeton(x))
    def test_note_prestation_et_recherche_sans_droit_cible(self):
        from . import repas
        r=repas.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,2,1),'dejeuner')
        x=t.noter(self.u,'Note de repas fictive',accord_repas=r,date_fait=date(2026,1,5))
        self.assertEqual(self.client.get(reverse('suivi:notes',args=['accord_repas',r.pk])).status_code,200)
        self.u.user_permissions.remove(Permission.objects.get(codename='view_accordrepas'));u=get_user_model().objects.get(pk=self.u.pk)
        self.assertEqual(releve.contributions(u,notes=True),[])
    def test_actions_explicitement_liees_corrigees_closes_rouvertes(self):
        a=self.creer();x=releve.creer_action(self.u,'Rappeler fictivement',date(2026,1,8),appel=a);ancien=bd6.jeton(x)
        releve.changer_action(self.u,x,ancien,'Échéance incorrecte fictive',libelle=x.libelle,echeance=date(2026,1,9))
        with self.assertRaises(ValidationError):releve.terminer(self.u,x,ancien)
        releve.terminer(self.u,x,bd6.jeton(x));self.assertIsNotNone(x.terminee_le)
        releve.changer_action(self.u,x,bd6.jeton(x),'Clôture fictive incorrecte',reouvrir=True);self.assertIsNone(x.terminee_le);self.assertEqual(x.revisions.count(),4)
    def test_exploration_multivaleurs_total_non_additif_et_heures(self):
        self.creer(etat_reponse='apportee',reponses=['Conseil fictif','Orientation fictive'])
        rows,total,xs=e.calculer(self.u,self.config(axe='secondaire',croisement='reponse'));self.assertEqual(len(rows),4);self.assertEqual(total,{'objets':1});self.assertEqual(sum(x['valeur'] for x in rows),4)
        rows,total,xs=e.calculer(self.u,self.config(axe='heure',classes='Nuit | 22 | 24'));self.assertEqual(rows[0]['axe'],'Nuit')
    def test_exploration_declarations_inconnues_et_zero_separes(self):
        self.creer(adultes_declares=None);rows,total,_=e.calculer(self.u,self.config(mesure='adultes_declares'));self.assertIsNone(total['adultes_declares'])
        self.creer(adultes_declares=0);rows,total,_=e.calculer(self.u,self.config(mesure='adultes_declares'));self.assertEqual(total['adultes_declares'],0)
    def test_exploration_age_exact_frontieres_et_classes_sans_chevauchement(self):
        self.p.precision_naissance='exacte';self.p.date_naissance=date(2008,1,31);self.p.save()
        rows,totaux,_=e.calculer(self.u,self.config(population='personnes',axe='age',classes='Mineur | 0 | 18\nMajeur | 18 |'));self.assertEqual(rows[0]['axe'],'Majeur')
        with self.assertRaises(ValidationError):e.classes('A|0|18\nB|17|20')
        self.p.precision_naissance='annee_estimee';self.p.date_naissance=None;self.p.annee_naissance=2008;self.p.save()
        rows,_,_=e.calculer(self.u,self.config(population='personnes',axe='age'));self.assertEqual(rows[0]['axe'],e.INCONNU)
    def test_exploration_situation_datee_et_permissions(self):
        from . import famille
        famille.renseigner(self.u,self.p,date(2026,1,1),'Fictif',bd6.jeton(self.p),situation_familiale='Célibataire',rapports_parentaux='',fratrie='',enfants_a_charge=0,enfants_non_a_charge=None,grossesse=None)
        rows,_,_=e.calculer(self.u,self.config(population='personnes',axe='famille.situation_familiale'));self.assertEqual(rows[0]['axe'],'Célibataire')
        self.u.user_permissions.remove(Permission.objects.get(codename='view_declarationfamiliale'));u=get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):e.calculer(u,self.config(population='personnes',axe='famille.situation_familiale'))
    def test_modeles_parametres_prives_export_et_recalcul(self):
        a=self.creer();params={k:str(v) for k,v in self.config().items()};params.update(nom='Mes appels fictifs')
        r=self.client.post(reverse('dossiers:explorer'),params);self.assertEqual(r.status_code,302,r.content.decode());modele=m.ModeleRapport.objects.get();self.assertNotIn('resultats',modele.parametres)
        self.creer();r=self.client.get(r.url);self.assertEqual(r.context['totaux'],{'objets':2})
        csv=self.client.get(reverse('dossiers:explorer'),{**params,'format':'csv'});self.assertEqual(csv.status_code,200);self.assertIn('Population',csv.content.decode())
        autre=get_user_model().objects.create_user('autre-fictif');autre=autoriser(autre);self.client.force_login(autre);self.assertEqual(self.client.get(reverse('dossiers:explorer'),{'modele':modele.pk}).status_code,404)
    def _verifier_pdf_appel_et_exploration(self,pwa):
        a=self.creer()
        with override_settings(MODE_PWA=pwa):
            r=self.client.get(reverse('dossiers:appel115_pdf',args=[a.pk]));self.assertEqual(r.status_code,200);self.assertTrue(r.content.startswith(b'%PDF-'));self.assertIn('no-store',r['Cache-Control'])
            r=self.client.get(reverse('dossiers:explorer'),{**{k:str(v) for k,v in self.config().items()},'format':'pdf'});self.assertEqual(r.status_code,200);self.assertTrue(r.content.startswith(b'%PDF-'))
    def test_pdf_appel_et_exploration_natif(self):self._verifier_pdf_appel_et_exploration(False)
    def test_pdf_appel_et_exploration_pwa(self):
        import importlib.util
        if importlib.util.find_spec('fpdf') is None:self.skipTest('Dépendance facultative fpdf2 du profil PWA absente.')
        self._verifier_pdf_appel_et_exploration(True)

    def test_montants_units_devises_et_sous_ensembles_non_additifs(self):
        from . import dossier_complet as dc
        for monnaie,montant in [('EUR',D('10')),('CHF',D('20'))]:
            dc.enregistrer(self.u,'ressources',self.p,date(2026,1,1),None,'Fictif',bd6.jeton(self.p),etat='detail',libelle='Revenu fictif',organisme=None,montant=montant,devise=monnaie,periodicite='mensuelle')
        rows,totaux,_=e.calculer(self.u,self.config(population='ressources',mesure='quantite'))
        self.assertEqual(totaux,{'EUR / mensuelle':D('10'),'CHF / mensuelle':D('20')})
        rows,totaux,_=e.calculer(self.u,self.config(population='ressources',mesure='maximum'));self.assertEqual(totaux['EUR / mensuelle'],10)
    def test_filtres_personnels_sur_la_meme_personne_du_menage(self):
        from . import famille
        p2=m.Personne.objects.create(designation='Autre personne fictive E',cree_par=self.u,precision_naissance='exacte',date_naissance=date(2000,1,1));suivi.ajouter_appartenance(self.u,self.m,p2,date(2026,1,1))
        for p,statut in [(self.p,'Situation A'),(p2,'Situation B')]:famille.renseigner(self.u,p,date(2026,1,1),'Fictif',bd6.jeton(p),situation_familiale=statut,rapports_parentaux='',fratrie='',enfants_a_charge=None,enfants_non_a_charge=None,grossesse=None)
        rows,total,_=e.calculer(self.u,self.config(population='menages',mesure='personnes',axe='famille.situation_familiale'))
        self.assertEqual({r['axe']:r['valeur'] for r in rows},{'Situation A':1,'Situation B':1});self.assertEqual(total['personnes'],2)
        rows,total,_=e.calculer(self.u,self.config(population='menages',filtre1='famille.situation_familiale',valeur1='Situation A',filtre2='age',operation2='gte',valeur2='18'))
        self.assertEqual(total['objets'],0)
    def test_annuler_une_action_n_est_pas_la_realiser(self):
        a=self.creer();x=releve.creer_action(self.u,'Action fictive erronée',None,appel=a)
        releve.changer_action(self.u,x,bd6.jeton(x),'Mauvais appel fictif',annuler=True)
        self.assertIsNone(x.terminee_le);self.assertIsNotNone(x.annule_le)
        s.annuler(self.u,a,s.jeton(a),'Appel fictif en double')
    def test_retour_prise_et_date_suggeres_depuis_contexte_signe(self):
        from . import dossier
        request=self.client.get(reverse('dossiers:prise',args=['personne',self.p.pk,self.a.pk]))
        contexte=request.context['contexte_dossier']
        page=self.client.get(reverse('dossiers:appel115_nouveau'),{'personne':self.p.pk,'contexte_dossier':contexte,'date_service':'2026-01-08'})
        self.assertEqual(page.context['form'].initial['date'],date(2026,1,8));self.assertIn(str(self.a.pk),page.context['retour'])
    def test_filtres_supplementaires_et_classes_du_croisement(self):
        self.creer(adultes_declares=1,enfants_declares=2)
        conf=self.config(axe='heure',croisement='enfants_declares',classes='Soir|22|24',classes_croisement='Petit groupe|0|3',filtres=3,filtre3='motif',operation3='un_de',valeur3='Hébergement fictif; Autre')
        rows,total,_=e.calculer(self.u,conf);self.assertEqual(rows[0]['axe'],'Soir');self.assertEqual(rows[0]['croisement'],'Petit groupe');self.assertEqual(total['objets'],1)

    def test_toutes_populations_et_quantites_financieres(self):
        from . import hebergement,repas,aides,financements,parcours,dossier_complet
        from .tests_parcours import valeurs as valeurs_parcours
        h=hebergement.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,2,1))
        sejour=hebergement.admettre(self.u,h,[self.p],date(2026,1,1));hebergement.sortir(self.u,sejour,date(2026,1,4))
        r=repas.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,2,1),'dejeuner');repas.distribuer(self.u,r,self.p,date(2026,1,5),2)
        type_aide=aides.cataloguer(self.u,aides.jeton_catalogue(),'Fictif',nature='transport',libelle='Titre fictif E',unite='titre',fractionnable=False,precision='',actif=True)
        a=aides.accorder(self.u,self.a,type_aide,[self.p],bd6.jeton(self.a),debut=date(2026,1,1),fin=date(2026,2,1),quantite=D('5'),prestataire=None,financeur=None,valeur_bon=None,devise='EUR',source='Fictif')
        aides.remettre(self.u,a,[self.p],date(2026,1,5),D('2'),'Fictif',bd6.jeton(a))
        parcours.creer(self.u,'demandes',self.p,[self.p],date(2026,1,1),'Fictif',bd6.jeton(self.p),**valeurs_parcours('demandes'))
        org=m.Partenaire.objects.create(libelle='Financeur fictif E',cree_par=self.u)
        financements.enregistrer(self.u,a,financements.jeton(a),'Fictif','definition',
            [dict(phase='autorise',date=date(2026,1,5),libelle='Titre fictif E',unite='titre',categorie='',quantite=D('2'),prix=D('3'),tarif=None,justification='Décision fictive')],
            [dict(phase='autorise',financeur=org,budget='Mobilité fictive',montant=D('6'),reference='FICTIF')],
            emetteur=None,mentions='',debut=date(2026,1,1),fin=date(2026,2,1),devise='EUR',prestataire=None,prescripteur=None,facturation=None,signataire=None,reference='',source='Fictif')
        dossier_complet.enregistrer(self.u,'dettes',self.p,date(2026,1,1),None,'Fictif',bd6.jeton(self.p),etat='detail',nature='detail',creancier='Créancier fictif',organisme=None,reference='',montant=D('20'),devise='EUR',mensualite=None)
        for code in ('personnes','menages','prises','demandes','sejours','repas','aides','couts','imputations','dettes'):
            rows,total,lignes=e.calculer(self.u,self.config(population=code));self.assertTrue(lignes,code)
        rows,total,_=e.calculer(self.u,self.config(population='couts',mesure='quantite'));self.assertEqual(total,{'EUR / autorise':D('6')})
        rows,total,_=e.calculer(self.u,self.config(population='sejours',mesure='quantite'));self.assertEqual(total['personne-nuit de séjour (absences non déduites)'],3)
        x=self.creer();jour=timezone.localdate(x.enregistre_le)
        rows,total,_=e.calculer(self.u,self.config(filtre1='date_saisie',operation1='depuis',valeur1=jour.isoformat()));self.assertEqual(total['objets'],1)

    def test_delier_demande_annulee_et_refuser_action_sur_appel_annule(self):
        from . import parcours
        from .tests_parcours import valeurs
        a=self.creer();s.ecrire(self.u,s.jeton(a),[self.p],appel=a,action='suite',motif='Fictif',**self.donnees())
        demande=parcours.creer(self.u,'demandes',self.p,[self.p],date(2026,1,1),'Fictif',bd6.jeton(self.p),**valeurs('demandes'))
        lien=s.lier(self.u,a,s.jeton(a),'Fictif',demande=demande)
        parcours.annuler(self.u,'demandes',demande,'Demande fictive erronée',bd6.jeton(demande))
        s.delier(self.u,a,lien,s.jeton(a),'Lien vers demande erronée annulé explicitement')
        s.annuler(self.u,a,s.jeton(a),'Fictif')
        with self.assertRaises(ValidationError):releve.creer_action(self.u,'Action fictive',None,appel=a)
        page=self.client.post(reverse('suivi:actions_relais')+'?appel='+str(a.pk),{'libelle':'Action fictive','echeance':''})
        self.assertContains(page,'Cet appel est annulé')


class MetaETransactions(TransactionTestCase):
    setUp=MetaETests.setUp
    donnees=MetaETests.donnees
    creer=MetaETests.creer
    def test_deux_corrections_concurrentes_une_seule_version(self):
        import threading
        from django.db import close_old_connections,OperationalError
        a=self.creer();token=s.jeton(a);barriere=threading.Barrier(2);resultats=[];erreurs=[]
        def travail():
            close_old_connections()
            try:
                u=get_user_model().objects.get(pk=self.u.pk);appel=m.Appel115.objects.get(pk=a.pk);u.get_all_permissions();barriere.wait(timeout=10)
                try:s.ecrire(u,token,[],appel=appel,action='correction',motif='Correction fictive concurrente',**self.donnees());resultats.append(True)
                except (ValidationError,OperationalError):resultats.append(False)
            except Exception as exc:erreurs.append(exc)
            finally:close_old_connections()
        ts=[threading.Thread(target=travail) for _ in range(2)]
        for t_ in ts:t_.start()
        for t_ in ts:t_.join(20)
        self.assertFalse(any(t_.is_alive() for t_ in ts));self.assertFalse(erreurs,erreurs);self.assertEqual(sum(resultats),1,resultats);self.assertEqual(a.versions.count(),2)
    def test_copie_appels_versions_actions_et_dates(self):
        from contextlib import closing
        import sqlite3,tempfile,json
        from pathlib import Path
        from django.db import connection
        if connection.vendor!='sqlite':self.skipTest('Recette SQLite.')
        a=self.creer();s.ecrire(self.u,s.jeton(a),[],appel=a,action='correction',motif='Heure fictive retrouvée',**self.donnees(heure=time(12,1)))
        x=releve.creer_action(self.u,'Relais fictif',None,appel=a);releve.changer_action(self.u,x,bd6.jeton(x),'Erreur fictive',annuler=True)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'copie.sqlite3'
            with closing(sqlite3.connect(path)) as db,db:connection.connection.backup(db)
            with closing(sqlite3.connect(path)) as db,db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM personnes_versionappel115').fetchone()[0],2)
                self.assertEqual(db.execute('SELECT motif_annulation,terminee_le FROM personnes_actionrelais').fetchone(),('Erreur fictive',None))
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
    def test_migration_conserve_anciennes_contributions_sans_date_inventee(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        old=[('personnes','0032_financements_et_documents')];ex=MigrationExecutor(connection);latest=ex.loader.graph.leaf_nodes()
        u=get_user_model().objects.create_user('ancienne-releve-fictive')
        try:
            ex.migrate(old);apps=ex.loader.project_state(old).apps
            pk=apps.get_model('personnes','Transmission').objects.create(contenu='Ancienne relève fictive',auteur_id=u.pk).pk
        finally:MigrationExecutor(connection).migrate(latest)
        x=m.Transmission.objects.get(pk=pk);self.assertIsNone(x.date_fait);self.assertEqual(x.contenu,'Ancienne relève fictive');self.assertFalse(m.Appel115.objects.exists());self.assertFalse(get_user_model().objects.get(pk=u.pk).user_permissions.exists())
