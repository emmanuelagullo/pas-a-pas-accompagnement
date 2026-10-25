"""Comparaisons métier de consolidation : âges, bornes, déclarations et croisements."""
import csv
from datetime import date
from io import StringIO
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from . import models as m, suivi, hebergement, repas, famille, bd6, exploration as e
from .mesures_exploration import ventiler_nuitees


class ConsolidationStatistiques(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u = get_user_model().objects.create_user('consolidation-fictive')
        call_command('autoriser_chrs7', cls.u.username, stdout=StringIO())
        call_command('autoriser_solenne', cls.u.username, stdout=StringIO())
        cls.adulte = m.Personne.objects.create(designation='Adulte fictif F', precision_naissance='exacte', date_naissance=date(1980,1,1), cree_par=cls.u)
        cls.anniversaire = m.Personne.objects.create(designation='Anniversaire fictif F', precision_naissance='exacte', date_naissance=date(2008,1,3), cree_par=cls.u)
        cls.inconnu = m.Personne.objects.create(designation='Âge inconnu fictif F', cree_par=cls.u)
        cls.ps = [cls.adulte,cls.anniversaire,cls.inconnu]
        cls.menage = suivi.creer_menage(cls.u,'Ménage fictif F',cls.ps,date(2025,1,1))
        cls.prise = suivi.ouvrir(cls.u,cls.menage,cls.ps,date(2025,1,1))
        cls.accord = m.AccordHebergement.objects.create(accompagnement=cls.prise,debut=date(2026,1,1),fin=date(2026,1,5),cree_par=cls.u)
        cls.accord.beneficiaires.set(cls.ps)
        cls.sejour = m.Sejour.objects.create(accord=cls.accord,debut=date(2026,1,1),fin=date(2026,1,5),cree_par=cls.u)
        cls.sejour.beneficiaires.set(cls.ps)
        cls.ar = m.AccordRepas.objects.create(accompagnement=cls.prise,debut=date(2026,1,1),fin=date(2026,1,5),service='dejeuner',cree_par=cls.u)
        cls.ar.beneficiaires.set(cls.ps)
        for p,a,b,g in [(cls.adulte,2,1,False),(cls.anniversaire,0,None,True)]:
            famille.renseigner(cls.u,p,date(2026,1,1),'Déclaration fictive',bd6.jeton(p),situation_familiale='Déclarée',rapports_parentaux='',fratrie='',enfants_a_charge=a,enfants_non_a_charge=b,grossesse=g)

    def config(self,**kw):
        d=dict(population='sejours',debut=date(2026,1,1),fin=date(2026,1,5),reference=date(2026,1,31),mesure='objets',axe='total',croisement='',classes='',filtre1='',operation1='egal',valeur1='',filtre2='',operation2='egal',valeur2='')
        return {**d,**kw}

    def total(self,**kw):
        rows,total,lignes=e.calculer(self.u,self.config(**kw))
        return next(iter(total.values())) if total else None

    def test_nuitees_anniversaire_reconciliation_et_age_inconnu(self):
        self.assertEqual(self.total(mesure='quantite'),12)
        self.assertEqual(self.total(mesure='nuitees_adultes'),6)
        self.assertEqual(self.total(mesure='nuitees_enfants'),2)
        self.assertEqual(self.total(mesure='nuitees_age_inconnu'),4)
        self.assertEqual(self.total(population='personnes',mesure='adultes_connus'),2)
        self.assertEqual(self.total(population='personnes',mesure='enfants_connus'),0)
        self.assertEqual(self.total(population='personnes',mesure='ages_inconnus'),1)

    def test_nuitees_filtrees_par_personne_pas_effectif_collectif(self):
        self.assertEqual(self.total(mesure='nuitees_adultes',filtre1='age',operation1='egal',valeur1='18'),2)
        self.assertEqual(self.total(mesure='nuitees_enfants',filtre1='age',operation1='egal',valeur1='18'),2)

    def test_naissance_estimee_future_et_29_fevrier(self):
        p=m.Personne(precision_naissance='exacte',date_naissance=date(2008,2,29))
        self.assertEqual(ventiler_nuitees(p,date(2026,2,28),date(2026,3,2)),(1,1,0))
        p.precision_naissance='estimee'
        self.assertEqual(ventiler_nuitees(p,date(2026,2,28),date(2026,3,2)),(0,0,2))
        p.precision_naissance='exacte';p.date_naissance=date(2026,1,3)
        self.assertEqual(ventiler_nuitees(p,date(2026,1,1),date(2026,1,5)),(0,2,2))

    def test_periode_coupee_integralite_et_sortie_a_la_borne(self):
        self.assertEqual(self.total(debut=date(2026,1,3),fin=date(2026,1,4),mesure='quantite'),3)
        self.assertEqual(self.total(debut=date(2026,1,3),fin=date(2026,1,4),mesure='quantite',portion='integrale'),12)
        self.assertEqual(self.total(debut=date(2026,1,5),fin=date(2026,1,6),mouvement='sorties'),1)
        self.assertEqual(self.total(debut=date(2026,1,5),fin=date(2026,1,6)),0)
        self.assertEqual(self.total(mouvement='sorties'),0) # fin exclue du rapport
        self.assertEqual(self.total(mouvement='entrees'),1)

    def test_integralite_ouverte_refusee_sauf_selection_sorties(self):
        s=m.Sejour.objects.create(accord=self.accord,debut=date(2026,1,2),cree_par=self.u);s.beneficiaires.set([self.adulte])
        with self.assertRaises(ValidationError):self.total(portion='integrale',mesure='quantite')
        self.assertEqual(self.total(portion='integrale',mouvement='sorties',fin=date(2026,1,6),mesure='quantite'),12)

    def test_accords_repas_et_hebergement_ne_sont_pas_des_faits(self):
        self.assertEqual(self.total(population='accords_repas'),1)
        self.assertEqual(self.total(population='accords_hebergement'),1)
        self.assertEqual(self.total(population='repas'),0)
        with self.assertRaises(ValidationError):self.total(population='accords_repas',mesure='quantite')
        self.assertEqual(self.total(population='accords_repas',mouvement='sorties',debut=date(2026,1,5),fin=date(2026,1,6)),1)

    def test_declarations_familiales_inconnues_zero_et_declarants_distincts(self):
        a=suivi.ouvrir(self.u,self.menage,self.ps,date(2025,2,1))
        self.assertEqual(self.total(population='prises',mesure='enfants_charge_declares'),2)
        self.assertEqual(self.total(population='prises',mesure='enfants_non_charge_declares'),1)
        self.assertEqual(self.total(population='prises',mesure='enfants_famille_declares'),3)
        self.assertEqual(self.total(population='prises',mesure='grossesses_famille_declarees'),1)
        self.assertIsNone(self.total(population='personnes',mesure='enfants_non_charge_declares',filtre1='age',operation1='egal',valeur1='18'))
        self.assertEqual(self.total(population='personnes',mesure='enfants_charge_declares',filtre1='age',operation1='egal',valeur1='18'),0)

    def test_droits_declarations_revalides_pour_mesure(self):
        self.u.user_permissions.remove(Permission.objects.get(codename='view_declarationfamiliale'))
        self.u=get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):self.total(mesure='enfants_charge_declares')

    def test_sept_axes_et_classes_sur_le_meme_beneficiaire(self):
        rows,total,_=e.calculer(self.u,self.config(mesure='personnes',axe='jour_semaine',croisement='age',axe3='famille.grossesse',axe4='famille.enfants_a_charge',axe5='mois',axe6='etat',axe7='duree',classes7='Court|0|5\nLong|5|'))
        self.assertEqual(total,{'personnes':3})
        for r in rows:
            if r['croisement']=='18':self.assertEqual(r['niveaux'][:2],['Oui','0'])
            self.assertEqual(r['niveaux'][-1],'Court')
            self.assertEqual(r['axe'],'Jeudi')

    def test_html_csv_et_modele_plusieurs_mesures_niveaux(self):
        self.client.force_login(self.u)
        params={k:str(v) for k,v in self.config(population='personnes',mesure='personnes',niveaux=3,axe3='precision_naissance',nombre_mesures=3,mesure2='adultes_connus',mesure3='ages_inconnus').items()}
        r=self.client.get(reverse('dossiers:explorer'),params);self.assertEqual(r.status_code,200)
        self.assertFalse(r.context['form'].errors,r.context['form'].errors)
        self.assertContains(r,'Personnes majeures distinctes')
        r=self.client.get(reverse('dossiers:explorer'),{**params,'format':'csv'})
        rows=list(csv.reader(StringIO(r.content.decode()),delimiter=';'))
        self.assertTrue(all(len(row)==len(rows[0]) for row in rows))
        self.assertIn('Niveau 3',rows[0])
        r=self.client.post(reverse('dossiers:explorer'),{**params,'nom':'Mesures fictives F'});self.assertEqual(r.status_code,302)
        r=self.client.get(r.url);self.assertFalse(r.context['form'].errors,r.context['form'].errors)
        self.assertEqual(len(r.context['totaux']),3)

    def test_ajout_progressif_bornes_et_erreurs_visibles(self):
        self.client.force_login(self.u)
        r=self.client.get(reverse('dossiers:explorer'),{'ajouter_niveau':'1','ajouter_mesure':'1'})
        self.assertIn('axe3',r.context['form'].fields);self.assertIn('mesure2',r.context['form'].fields)
        r=self.client.get(reverse('dossiers:explorer'),{'niveaux':'8'})
        self.assertIn('niveaux',r.context['form'].errors)
        self.assertContains(r,'<details open>',html=False)
        with self.assertRaises(ValidationError):self.total(population='personnes',mesure='nuitees_enfants')


class PiecesDossierTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u=get_user_model().objects.create_user('documents-fictifs')
        call_command('autoriser_chrs7',cls.u.username,stdout=StringIO())
        call_command('autoriser_solenne',cls.u.username,stdout=StringIO())
        cls.p=m.Personne.objects.create(designation='Dossier documentaire fictif',cree_par=cls.u)

    def ajouter(self,cible=None,**kw):
        from . import pieces_dossier as s
        from django.core.files.uploadedfile import SimpleUploadedFile
        cible=cible or self.p
        data=dict(titre='Document fictif',date_document=None,source='Recette fictive',fichier=SimpleUploadedFile('pièce-fictive.txt',b'Contenu fictif\x00\xff'))
        data.update(kw)
        return s.ajouter(self.u,cible,bd6.jeton(cible),**data)

    def test_versions_metadata_octets_et_annulation_conserves(self):
        from . import pieces_dossier as s
        piece=self.ajouter();v1=piece.versions.first()
        self.ajouter(piece=piece,fichier=None,titre='Titre corrigé fictif',motif='Correction fictive')
        self.assertEqual(piece.versions.count(),2)
        self.assertEqual(s.octets(self.u,piece.versions.first()),s.octets(self.u,v1))
        s.annuler(self.u,piece,bd6.jeton(self.p),'Document associé par erreur')
        piece.refresh_from_db();self.assertIsNotNone(piece.annule_le)
        self.assertEqual(s.octets(self.u,v1),b'Contenu fictif\x00\xff')
        with self.assertRaises(ValidationError):self.ajouter(piece=piece,motif='Fictif')
        self.assertEqual(piece.versions.count(),2)

    def test_perime_mauvaise_cible_et_droits_pas_de_version_partielle(self):
        from . import pieces_dossier as s
        from django.core.files.uploadedfile import SimpleUploadedFile
        piece=self.ajouter();ancien=bd6.jeton(self.p)
        self.ajouter(piece=piece,fichier=None,motif='Correction fictive')
        with self.assertRaises(ValidationError):s.ajouter(self.u,self.p,ancien,piece=piece,titre='Périmé',date_document=None,source='Fictif',motif='Fictif',fichier=None)
        autre=m.Personne.objects.create(designation='Autre fictif',cree_par=self.u)
        with self.assertRaises(ValidationError):self.ajouter(cible=autre,piece=piece,motif='Fictif')
        self.assertEqual(piece.versions.count(),2)
        self.u.user_permissions.remove(Permission.objects.get(codename='view_versionpiecedossier'))
        self.u=get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):s.octets(self.u,piece.versions.first())

    def test_fichier_vide_trop_gros_date_future_et_cible_sql(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.db import transaction,IntegrityError
        from django.utils import timezone
        from datetime import timedelta
        for fichier in [SimpleUploadedFile('vide.txt',b''),SimpleUploadedFile('gros.txt',b'x'*(5*1024*1024+1))]:
            with self.assertRaises(ValidationError):self.ajouter(fichier=fichier)
        with self.assertRaises(ValidationError):self.ajouter(date_document=timezone.localdate()+timedelta(days=1))
        self.assertFalse(m.PieceDossier.objects.exists())
        with self.assertRaises(IntegrityError),transaction.atomic():m.PieceDossier.objects.create(auteur=self.u)

    def test_telechargement_prive_natif_et_pwa_sans_execution(self):
        from django.test import override_settings
        piece=self.ajouter();v=piece.versions.first();url=reverse('dossiers:piece_telecharger',args=[v.pk])
        self.assertEqual(self.client.get(url).status_code,302)
        self.client.force_login(self.u)
        for pwa in (False,True):
            with override_settings(MODE_PWA=pwa):
                r=self.client.get(url);self.assertEqual(r.status_code,200);self.assertEqual(r.content,b'Contenu fictif\x00\xff')
                self.assertIn('attachment',r['Content-Disposition']);self.assertIn('no-store',r['Cache-Control']);self.assertEqual(r['X-Content-Type-Options'],'nosniff')
        m.VersionPieceDossier.objects.filter(pk=v.pk).update(contenu='Fichier fictif altéré'.encode())
        self.assertEqual(self.client.get(url).status_code,422)

    def test_saisie_correction_historique_multipart_et_retour_bd(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.u)
        url=reverse('dossiers:pieces',args=['personne',self.p.pk])
        r=self.client.get(url);self.assertEqual(r.status_code,200);self.assertContains(r,'multipart/form-data')
        data=dict(attendu=bd6.jeton(self.p),titre='Pièce fictive',date_document='',source='Recette',fichier=SimpleUploadedFile('fictif.txt',b'Fictif'))
        r=self.client.post(url,data);self.assertEqual(r.status_code,302)
        piece=m.PieceDossier.objects.get()
        r=self.client.get(r.url);self.assertContains(r,'Versions conservées');self.assertFalse(r.context['form'].fields['fichier'].required)
        r=self.client.post(url+'?piece='+str(piece.pk),dict(attendu=bd6.jeton(self.p),titre='Pièce corrigée',date_document='',source='Recette',motif='Correction du titre'))
        self.assertEqual(r.status_code,302);self.assertEqual(piece.versions.count(),2)
        r=self.client.post(url+'?piece='+str(piece.pk)+'&action=annuler',dict(attendu=bd6.jeton(self.p),motif='Fictif'))
        self.assertEqual(r.status_code,302)
        r=self.client.get(url);self.assertContains(r,'annulé')

    def test_les_trois_cibles_et_leurs_droits(self):
        from . import pieces_dossier as s
        menage=suivi.creer_menage(self.u,'Ménage documentaire fictif',[self.p],date(2026,1,1))
        prise=suivi.ouvrir(self.u,menage,[self.p],date(2026,1,1))
        for cible in (self.p,menage,prise):
            piece=self.ajouter(cible=cible);self.assertEqual(piece.cible,cible)
        self.u.user_permissions.remove(Permission.objects.get(codename='view_menage'))
        self.u=get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):s.droit(self.u,prise)


class PropositionsRepasTests(TestCase):
    def test_seuils_tarifaires_distincts_majorite_et_naissance_imprecise(self):
        p=m.Personne(precision_naissance='exacte',date_naissance=date(2013,1,2))
        self.assertEqual(repas.proposer_categorie(p,date(2026,1,1)),'jeune')
        self.assertEqual(repas.proposer_categorie(p,date(2026,1,2)),'adulte')
        self.assertEqual(repas.proposer_categorie(p,date(2026,1,2),age_jeune=17),'jeune')
        p.precision_naissance='annee';self.assertIsNone(repas.proposer_categorie(p,date(2026,1,2)))
        with self.assertRaises(ValidationError):repas.proposer_categorie(p,date(2026,1,2),age_jeune=1,age_bas_age=2)

    def test_proposition_ne_distribue_pas_et_confirmation_explicite(self):
        u=get_user_model().objects.create_user('repas-suggestion-fictive')
        call_command('autoriser_chrs7',u.username,stdout=StringIO())
        p=m.Personne.objects.create(designation='Personne fictive',precision_naissance='exacte',date_naissance=date(2013,1,2),cree_par=u)
        menage=suivi.creer_menage(u,'Ménage fictif',[p],date(2026,1,1));a=suivi.ouvrir(u,menage,[p],date(2026,1,1))
        accord=repas.accorder(u,a,[p],date(2026,1,1),date(2026,2,1),'dejeuner')
        self.client.force_login(u)
        url=reverse('suivi:distribuer_repas',args=[accord.pk])
        data=dict(beneficiaire=p.pk,date='2026-01-02',quantite='1',age_jeune='12',age_bas_age='2',action='proposer_categorie')
        r=self.client.post(url,data);self.assertEqual(r.status_code,200);self.assertFalse(m.RepasDistribue.objects.exists())
        self.assertContains(r,'Catégorie proposée : adulte')
        data.pop('action');data['categorie_declaree']='jeune'
        r=self.client.post(url,data);self.assertEqual(r.status_code,302)
        self.assertEqual(m.RepasDistribue.objects.get().categorie_declaree,'jeune')


class ConsolidationEchangesEtBesoins(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u=get_user_model().objects.create_user('consolidation-echanges-fictifs')
        call_command('autoriser_chrs7',cls.u.username,stdout=StringIO())
        call_command('autoriser_solenne',cls.u.username,stdout=StringIO())
        cls.p=m.Personne.objects.create(designation='Besoin fictif',cree_par=cls.u)

    def test_besoin_date_correction_changement_annulation_et_recherche(self):
        from . import dossier_complet as dc
        d=dict(etat='detail',categorie='mobilite',libelle='Accès fictif sans escalier',adaptation='Demande pratique fictive')
        x=dc.enregistrer(self.u,'besoins',self.p,date(2026,1,1),None,'Entretien fictif',bd6.jeton(self.p),**d)
        dc.enregistrer(self.u,'besoins',self.p,date(2026,1,1),None,'Source rectifiée',bd6.jeton(self.p),correction=x.pk,motif='Correction fictive',**d)
        y=dc.enregistrer(self.u,'besoins',self.p,date(2026,1,3),None,'Évolution fictive',bd6.jeton(self.p),remplace=x.pk,**{**d,'adaptation':'Nouvelle adaptation fictive'})
        self.assertEqual(dc.a_date('besoins',[self.p],date(2026,1,2)).get().pk,x.pk)
        self.assertEqual(dc.a_date('besoins',[self.p],date(2026,1,4)).get().pk,y.pk)
        self.client.force_login(self.u)
        r=self.client.get(reverse('dossiers:rapport_a'),dict(rubrique='besoins',date='2026-01-02',texte='sans escalier',format='csv'))
        self.assertEqual(r.status_code,200);self.assertIn('Accès fictif sans escalier',r.content.decode())
        dc.annuler(self.u,'besoins',self.p,y,'Erreur fictive',bd6.jeton(self.p))
        self.assertEqual(m.RevisionBesoinAccueil.objects.count(),4)
        self.assertNotIn('besoins.adaptation',e.disponibles(self.u))
        self.u.user_permissions.remove(Permission.objects.get(codename='view_besoinaccueil'))
        self.u=get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):dc.exiger_lecture(self.u,'besoins')

    def test_modele_json_parametres_seulement_prive_et_revalide(self):
        from . import modeles_echange as s
        import json
        params=dict(schema=1,exploration=True,population='personnes',debut='2026-01-01',fin='2026-02-01',reference='2026-01-31',mesure='personnes',axe='total',croisement='',classes='',filtre1='',operation1='egal',valeur1='',filtre2='',operation2='egal',valeur2='')
        original=m.ModeleRapport.objects.create(auteur=self.u,nom='Modèle fictif échangeable',parametres=params)
        contenu=s.exporter(self.u,original);x=s.importer(self.u,contenu)
        self.assertNotEqual(x.pk,original.pk);self.assertNotIn('resultats',x.parametres)
        d=json.loads(contenu);d['parametres']['axe']='chemin.sql_interdit'
        with self.assertRaises(ValidationError):s.importer(self.u,json.dumps(d).encode())
        autre=get_user_model().objects.create_user('autre-fictif-echange')
        with self.assertRaises(PermissionDenied):s.exporter(autre,original)
        self.client.force_login(self.u)
        self.assertEqual(self.client.get(reverse('dossiers:explorer_exporter_modele',args=[original.pk])).status_code,200)
        from django.core.files.uploadedfile import SimpleUploadedFile
        r=self.client.post(reverse('dossiers:explorer_importer_modele'),{'fichier':SimpleUploadedFile('modele.json',contenu)})
        self.assertEqual(r.status_code,302)
        self.assertEqual(self.client.get(r.url).status_code,200)

    def test_propositions_import_atomique_sans_ecrasement_ni_droits(self):
        from . import propositions as s
        import json
        a=s.enregistrer(self.u,'ville','Ville fictive',True,'Création fictive')
        d=json.loads(s.exporter(self.u));d['propositions'][0]['active']=False
        d['propositions'].append(dict(champ='code_postal',valeur='00100',active=True))
        self.assertEqual(s.importer(self.u,json.dumps(d).encode(),'Import fictif'),(1,1))
        a.refresh_from_db();self.assertTrue(a.active)
        self.assertTrue(m.PropositionSaisie.objects.filter(champ='code_postal',valeur='00100').exists())
        avant=m.PropositionSaisie.objects.count()
        d['propositions']=[dict(champ='ville',valeur='Ville ajout fictif',active=True),dict(champ='champ_inexistant',valeur='Erreur fictive',active=True)]
        with self.assertRaises(ValidationError):s.importer(self.u,json.dumps(d).encode(),'Fictif')
        self.assertEqual(m.PropositionSaisie.objects.count(),avant)
        self.assertFalse(m.PropositionSaisie.objects.filter(valeur='Ville ajout fictif').exists())

    def test_reference_personnelle_a_la_date_du_fait_distincte_de_la_saisie(self):
        from . import famille
        p=self.p
        for jour,etat in [(date(2026,1,1),'Situation A fictive'),(date(2026,1,3),'Situation B fictive')]:
            famille.renseigner(self.u,p,jour,'Entretien',bd6.jeton(p),situation_familiale=etat,rapports_parentaux='',fratrie='',enfants_a_charge=None,enfants_non_a_charge=None,grossesse=None)
        # Les appels restent deux événements, même si leur situation est lue
        # à deux références différentes : pas de duplication de dossier.
        from . import appels115 as s
        for jour in (date(2026,1,2),date(2026,1,4)):
            vals={c:m.VersionAppel115._meta.get_field(c).get_default() for c in s.CHAMPS};vals.update(date=jour,type_appelant='inconnu',motif_principal='Fictif',source='Entretien')
            s.ecrire(self.u,s.creation(),[p],action='saisie',**vals)
        config=dict(population='appels',debut=date(2026,1,1),fin=date(2026,2,1),reference=date(2026,1,31),reference_mode='fait',mesure='objets',axe='famille.situation_familiale',croisement='',classes='',filtre1='',operation1='egal',valeur1='',filtre2='',operation2='egal',valeur2='')
        rows,totaux,_=e.calculer(self.u,config);self.assertEqual({r['axe']:r['valeur'] for r in rows},{'Situation A fictive':1,'Situation B fictive':1})
        config['reference_mode']='commune';rows,_,_=e.calculer(self.u,config);self.assertEqual(rows[0]['valeur'],2)


class ContratVingtEtUneQuantites(TestCase):
    setUpTestData=classmethod(ConsolidationStatistiques.setUpTestData.__func__)
    config=ConsolidationStatistiques.config
    total=ConsolidationStatistiques.total
    # Le vecteur représente les 21 destinations métier, pas la reproduction
    # des anciens indices erronés ni des maxima familiaux de Solenne.
    def test_21_destinations_et_ecarts_anciens_explicitement_corriges(self):
        from . import financements as f,appels115
        from decimal import Decimal
        for p,n,categorie in [(self.adulte,2,'adulte'),(self.anniversaire,3,'jeune'),(self.inconnu,4,'bas âge')]:
            repas.distribuer(self.u,self.ar,p,date(2026,1,2),n,categorie_declaree=categorie)
        vals={c:m.VersionAppel115._meta.get_field(c).get_default() for c in appels115.CHAMPS};vals.update(date=date(2026,1,2),type_appelant='inconnu',motif_principal='Fictif',source='Appel fictif')
        appels115.ecrire(self.u,appels115.creation(),[],action='saisie',**vals)
        lignes=[dict(phase='autorise',date=date(2026,1,2),libelle='Composante fictive',unite='unité',categorie='',quantite=Decimal('1'),prix=prix,tarif=None,justification='Montant fictif déclaré') for prix in (Decimal('10'),Decimal('12.50'))]
        f.enregistrer(self.u,self.accord,attendu=f.jeton(self.accord),motif='Calcul fictif',action='definition',lignes=lignes,imputations=[],emetteur=None,mentions='',debut=date(2026,1,1),fin=date(2026,1,5),devise='EUR',prestataire=None,prescripteur=None,facturation=None,signataire=None,reference='FICTIF-F',source='Recette fictive')
        def q(code,mesure='objets',**kw):return self.total(population=code,mesure=mesure,**kw)
        def repas_categorie(valeur):return q('repas','quantite',filtre1='etat',operation1='egal',valeur1=valeur)
        obtenu=[q('prises'),q('sejours')+q('accords_repas'),q('sejours'),q('accords_repas'),q('appels'),q('sejours','quantite'),q('sejours','nuitees_adultes'),q('sejours','nuitees_enfants'),q('repas','quantite'),repas_categorie('adulte'),repas_categorie('jeune'),repas_categorie('bas âge'),q('couts','quantite'),q('prises','menages'),q('prises','personnes'),q('prises','adultes_connus'),q('prises','enfants_connus'),q('prises','enfants_famille_declares'),q('prises','enfants_charge_declares'),q('prises','enfants_non_charge_declares'),q('prises','grossesses_famille_declarees')]
        self.assertEqual(obtenu,[1,2,1,1,1,12,6,2,9,2,3,4,Decimal('22.50'),1,3,2,0,3,2,1,1])
        self.assertEqual(q('sejours','nuitees_age_inconnu'),4)


from django.test import TransactionTestCase


class ConsolidationTransactions(TransactionTestCase):
    def setUp(self):
        self.u=get_user_model().objects.create_user('transaction-document-fictive')
        call_command('autoriser_chrs7',self.u.username,stdout=StringIO())
        call_command('autoriser_solenne',self.u.username,stdout=StringIO())
        self.p=m.Personne.objects.create(designation='Copie documentaire fictive',cree_par=self.u)

    def creer(self):
        from . import pieces_dossier as s
        from django.core.files.uploadedfile import SimpleUploadedFile
        return s.ajouter(self.u,self.p,bd6.jeton(self.p),titre='Document fictif',date_document=None,source='Recette fictive',fichier=SimpleUploadedFile('fictif.txt',b'Version fictive initiale\x00'))

    def test_deux_confirmations_une_seule_version(self):
        import threading
        from django.db import connections,OperationalError
        from . import pieces_dossier as s
        piece=self.creer();token=bd6.jeton(self.p);barriere=threading.Barrier(2);resultats=[];erreurs=[]
        def ecrire():
            try:
                u=get_user_model().objects.get(pk=self.u.pk);p=m.Personne.objects.get(pk=self.p.pk);x=m.PieceDossier.objects.get(pk=piece.pk)
                barriere.wait(timeout=10)
                try:s.ajouter(u,p,token,titre='Correction fictive',date_document=None,source='Recette',fichier=None,piece=x,motif='Correction fictive');resultats.append(True)
                except (ValidationError,OperationalError):resultats.append(False)
            except BaseException as erreur:erreurs.append(repr(erreur))
            finally:connections.close_all()
        ts=[threading.Thread(target=ecrire) for _ in range(2)]
        for t in ts:t.start()
        for t in ts:t.join(timeout=20)
        self.assertFalse(any(t.is_alive() for t in ts));self.assertFalse(erreurs,erreurs)
        self.assertEqual(sum(resultats),1);self.assertEqual(piece.versions.count(),2)

    def test_copie_conserve_octets_versions_et_annulation_sans_handle_ouvert(self):
        from . import pieces_dossier as s
        from django.db import connection
        from contextlib import closing
        import sqlite3,tempfile
        from pathlib import Path
        if connection.vendor!='sqlite':self.skipTest('Recette spécifique SQLite.')
        piece=self.creer();s.ajouter(self.u,self.p,bd6.jeton(self.p),piece=piece,titre='Titre corrigé fictif',date_document=None,source='Recette',fichier=None,motif='Correction fictive')
        s.annuler(self.u,piece,bd6.jeton(self.p),'Erreur fictive')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'copie.sqlite3'
            with closing(sqlite3.connect(path)) as copie,copie:connection.connection.backup(copie)
            with closing(sqlite3.connect(path)) as copie,copie:
                self.assertEqual(copie.execute('SELECT contenu FROM personnes_versionpiecedossier ORDER BY version').fetchall(),[(b'Version fictive initiale\x00',)]*2)
                self.assertEqual(copie.execute('SELECT motif_annulation FROM personnes_piecedossier').fetchone()[0],'Erreur fictive')
                self.assertEqual(copie.execute('PRAGMA foreign_key_check').fetchall(),[])
            with self.assertRaises(sqlite3.ProgrammingError):copie.execute('SELECT 1')


class ConsolidationAxesHistoriques(TestCase):
    setUpTestData=classmethod(ConsolidationStatistiques.setUpTestData.__func__)
    config=ConsolidationStatistiques.config
    total=ConsolidationStatistiques.total

    def test_lieux_de_sejour_repartissent_les_nuitees_sans_nouvelle_admission(self):
        lieu1=m.LieuHebergement.objects.create(libelle='Lieu fictif A',cree_par=self.u)
        lieu2=m.LieuHebergement.objects.create(libelle='Lieu fictif B',cree_par=self.u)
        m.Affectation.objects.create(sejour=self.sejour,lieu=lieu1,debut=date(2026,1,1),fin=date(2026,1,3))
        m.Affectation.objects.create(sejour=self.sejour,lieu=lieu2,debut=date(2026,1,3),fin=date(2026,1,5))
        rows,totaux,_=e.calculer(self.u,self.config(population='affectations',mesure='quantite',axe='lieu'))
        self.assertEqual({r['axe']:r['valeur'] for r in rows},{'Lieu fictif A':6,'Lieu fictif B':6})
        self.assertEqual(self.total(),1)
        self.assertEqual(self.total(population='affectations',mesure='nuitees_adultes'),6)
        self.assertEqual(self.total(population='affectations',mesure='nuitees_enfants'),2)
        self.assertEqual(self.total(population='affectations',mesure='nuitees_age_inconnu'),4)

    def test_missions_attachees_a_la_bonne_prise_pas_a_la_seule_personne(self):
        autre=suivi.ouvrir(self.u,self.menage,[self.adulte],date(2025,2,1))
        for prise,libelle in [(self.prise,'Professionnel fictif A'),(autre,'Professionnel fictif B')]:
            i=m.Intervenant.objects.create(libelle=libelle,cree_par=self.u)
            m.AffectationIntervenant.objects.create(accompagnement=prise,debut=date(2026,1,1),role='referent',intervenant=i,source='Recette fictive',auteur=self.u)
        rows,_,_=e.calculer(self.u,self.config(axe='mission.professionnel'))
        self.assertEqual([r['axe'] for r in rows],['Professionnel fictif A'])
        self.u.user_permissions.remove(Permission.objects.get(codename='view_affectationintervenant'))
        self.u=get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):self.total(axe='mission.professionnel')

    def test_objectifs_dates_pour_les_beneficiaires_et_leurs_droits(self):
        objectif=m.ObjectifParcours.objects.create(personne=self.adulte,cree_par=self.u);objectif.beneficiaires.set([self.adulte])
        m.VersionObjectif.objects.create(element=objectif,debut=date(2026,1,1),fin=date(2026,1,3),etat='encours',theme='Logement fictif',titre='Objectif fictif',horizon='long',source='Recette',auteur=self.u)
        m.VersionObjectif.objects.create(element=objectif,debut=date(2026,1,3),etat='atteint',theme='Logement fictif',titre='Objectif fictif',horizon='long',source='Recette',auteur=self.u)
        rows,_,_=e.calculer(self.u,self.config(population='personnes',axe='objectif.etat',reference=date(2026,1,2)))
        self.assertIn('En cours',{r['axe'] for r in rows});self.assertNotIn('Atteint',{r['axe'] for r in rows})
        rows,_,_=e.calculer(self.u,self.config(population='personnes',axe='objectif.etat',reference=date(2026,1,4)))
        self.assertIn('Atteint',{r['axe'] for r in rows})
        self.u.user_permissions.remove(Permission.objects.get(codename='view_versionobjectif'));self.u=get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):self.total(population='personnes',axe='objectif.etat')

    def test_antecedent_declare_sans_date_inventee_recherche_et_correction(self):
        from . import dossier_complet as dc
        d=dict(etat='detail',libelle='Institution fictive',organisme=None,periode_declaree='Époque déclarée inconnue',date_entree=None,date_sortie=None,precision_dates='')
        x=dc.enregistrer(self.u,'antecedents',self.adulte,date(2026,1,1),None,'Entretien fictif',bd6.jeton(self.adulte),**d)
        self.assertIsNone(x.date_entree);self.assertIsNone(x.date_sortie)
        dc.enregistrer(self.u,'antecedents',self.adulte,date(2026,1,1),None,'Relecture fictive',bd6.jeton(self.adulte),correction=x.pk,motif='Précision fictive de la période',**{**d,'periode_declaree':'Pendant quelques mois déclarés'})
        rows,_,_=e.calculer(self.u,self.config(population='personnes',axe='antecedents.libelle'))
        self.assertIn('Institution fictive',{r['axe'] for r in rows})
        self.client.force_login(self.u)
        r=self.client.get(reverse('dossiers:fiche_a',args=[self.adulte.pk,'histoire']),{'date':'2026-01-02'})
        self.assertEqual(r.status_code,200);self.assertContains(r,'Institution fictive')
        with self.assertRaises(ValidationError):dc.enregistrer(self.u,'antecedents',self.adulte,date(2026,1,1),None,'Fictif',bd6.jeton(self.adulte),**{**d,'date_entree':date(2020,1,1)})


class ConsolidationReleves(TestCase):
    setUpTestData=classmethod(ConsolidationStatistiques.setUpTestData.__func__)
    config=ConsolidationStatistiques.config

    def test_onze_colonnes_filtrees_retour_signe_et_correction_sans_perdre_criteres(self):
        from urllib.parse import urlsplit,parse_qs
        call_command('autoriser_bd6',self.u.username,stdout=StringIO())
        self.client.force_login(self.u)
        params={k:str(v) for k,v in self.config(population='personnes',affichage='detail',nombre_colonnes=11,colonne1='personne',colonne2='age',colonne3='famille.grossesse',filtre1='age',operation1='egal',valeur1='18').items()}
        r=self.client.get(reverse('dossiers:explorer'),params);self.assertEqual(r.status_code,200);self.assertFalse(r.context['form'].errors)
        self.assertIn('colonne11',r.context['form'].fields)
        self.assertContains(r,'Anniversaire fictif F');self.assertNotContains(r,'Adulte fictif F')
        lien=r.context['page_obj'][0]['url'];r=self.client.get(lien);self.assertEqual(r.status_code,200)
        self.assertContains(r,'Revenir aux résultats du rapport')
        retour=r.context['retour_exploration'];self.assertEqual(parse_qs(urlsplit(retour).query)['valeur1'],['18'])
        lien_form=reverse('dossiers:commentaire',args=['personne',self.anniversaire.pk])+'?'+r.context['navigation_query']
        r=self.client.get(lien_form);self.assertEqual(r.status_code,200)
        r=self.client.post(lien_form,{'attendu':r.context['form'].initial['attendu'],'texte':'Commentaire fictif après relevé','motif':'Consolidation fictive'})
        self.assertEqual(r.status_code,302)
        r=self.client.get(r.url);self.assertContains(r,'Revenir aux résultats du rapport')
        from .exploration_releve import retour_verifie
        self.assertIsNone(retour_verifie(self.u,'https://exemple.invalid'))
        autre=get_user_model().objects.create_user('autre-fictif-retour')
        token=parse_qs(urlsplit(lien).query)['retour_exploration'][0]
        self.assertIsNone(retour_verifie(autre,token))
        r=self.client.get(reverse('dossiers:explorer'),{**params,'format':'csv_detail'})
        lignes=list(csv.reader(StringIO(r.content.decode()),delimiter=';'))
        self.assertEqual(len(lignes),2);self.assertIn('18',lignes[1])
        self.assertTrue(all('Adulte fictif F' not in c for c in lignes[1]))
