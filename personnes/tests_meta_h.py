"""Régressions des écarts confirmés par la relecture sémantique Solenne."""
from datetime import date
from io import StringIO
import csv
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied,ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from . import models as m,bd6,dossier_complet as dc,exploration as e,suivi


class ClotureSolenne(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u=get_user_model().objects.create_user('cloture-solenne-fictive')
        call_command('autoriser_chrs7',cls.u.username,stdout=StringIO())
        call_command('autoriser_solenne',cls.u.username,stdout=StringIO())
        cls.p=m.Personne.objects.create(designation='Personne fictive H',precision_naissance='exacte',date_naissance=date(2008,1,3),cree_par=cls.u)
        cls.autre=m.Personne.objects.create(designation='Autre personne fictive H',cree_par=cls.u)
        cls.menage=suivi.creer_menage(cls.u,'Ménage fictif H',[cls.p,cls.autre],date(2025,1,1))
        cls.prise=suivi.ouvrir(cls.u,cls.menage,[cls.p,cls.autre],date(2025,1,1))
        cls.a=cls.sejour(date(2026,1,1),[cls.p])
        cls.b=cls.sejour(date(2026,2,1),[cls.p,cls.autre])

    @classmethod
    def sejour(cls,debut,ps):
        fin=debut.replace(day=2)
        a=m.AccordHebergement.objects.create(accompagnement=cls.prise,debut=debut,fin=fin,cree_par=cls.u);a.beneficiaires.set(ps)
        s=m.Sejour.objects.create(accord=a,debut=debut,fin=fin,cree_par=cls.u);s.beneficiaires.set(ps)
        return s

    def config(self,**kw):
        return dict(dict(population='sejours',debut=date(2026,1,1),fin=date(2026,3,1),reference=date(2026,2,20),reference_mode='fait',mesure='personnes',axe='mois',croisement='',classes='',filtre1='',operation1='egal',valeur1='',filtre2='',operation2='egal',valeur2=''),**kw)

    def territoire(self,**kw):
        d=dict(etat='detail',type_territoire='agglomeration',territoire='Agglomération fictive',anciennete_declaree='Deux ans déclarés',depuis=None,precision_depuis='');d.update(kw)
        return dc.enregistrer(self.u,'territoires',self.p,date(2026,1,1),None,'Entretien fictif',bd6.jeton(self.p),**d)

    def test_anciennete_sans_date_inventee_et_correction_journalisee(self):
        t=self.territoire();ancien=bd6.jeton(self.p)
        dc.enregistrer(self.u,'territoires',self.p,t.debut,None,'Relecture fictive',ancien,correction=t.pk,motif='Précision de durée',etat='detail',type_territoire=t.type_territoire,territoire=t.territoire,anciennete_declaree='Trois ans déclarés',depuis=None,precision_depuis='')
        t.refresh_from_db();self.assertIsNone(t.depuis);self.assertEqual(t.anciennete_declaree,'Trois ans déclarés')
        r=t.revisions.first();self.assertEqual(r.action,'correction');self.assertEqual(r.avant[0]['anciennete_declaree'],'Deux ans déclarés')
        with self.assertRaises(ValidationError):
            dc.annuler(self.u,'territoires',self.p,t,'Erreur fictive',ancien)
        dc.annuler(self.u,'territoires',self.p,t,'Erreur fictive',bd6.jeton(self.p));t.refresh_from_db();self.assertIsNotNone(t.annule_le)

    def test_dates_precision_et_inconnu_distinct_de_detail(self):
        for kw in [dict(depuis=date(2026,1,2),precision_depuis='exacte'),dict(depuis=date(2025,1,1)),dict(precision_depuis='estimee'),dict(territoire=''),dict(etat='inconnu')]:
            with self.subTest(kw=kw),self.assertRaises(ValidationError):self.territoire(**kw)
        t=self.territoire(depuis=date(2025,1,1),precision_depuis='estimee');self.assertEqual(t.depuis,date(2025,1,1))
        with self.assertRaises(ValidationError):self.territoire()

    def test_passage_jamais_frequente_ne_fabrique_ni_date_ni_sejour(self):
        n=m.Sejour.objects.count()
        dc.enregistrer(self.u,'antecedents',self.p,date(2026,1,1),None,'Déclaration fictive',bd6.jeton(self.p),etat='detail',libelle='Institution fictive jamais fréquentée',frequentation='non',organisme=None,periode_declaree='',date_entree=None,date_sortie=None,precision_dates='')
        rows,totaux,_=e.calculer(self.u,self.config(population='personnes',axe='antecedents.frequentation',filtre1='antecedents.frequentation',valeur1='Jamais fréquentée, selon la déclaration'))
        self.assertEqual(totaux,{'personnes':1});self.assertEqual(m.Sejour.objects.count(),n)
        t=m.AntecedentInstitutionnel.objects.get(personne=self.p)
        t.date_entree=date(2025,1,1);t.precision_dates='exactes'
        with self.assertRaises(ValidationError):t.full_clean()

    def test_evolution_structuree_ne_change_pas_situation_ni_objectif(self):
        n=m.SituationPersonnelle.objects.count();o=m.ObjectifParcours.objects.count()
        x=dc.enregistrer(self.u,'evolutions',self.p,date(2026,1,1),None,'Bilan fictif',bd6.jeton(self.p),etat='detail',domaine='emploi',libelle='Accès déclaré à une formation fictive')
        self.assertEqual(m.SituationPersonnelle.objects.count(),n);self.assertEqual(m.ObjectifParcours.objects.count(),o)
        rows,totaux,_=e.calculer(self.u,self.config(population='personnes',axe='evolutions.domaine',filtre1='evolutions.libelle',valeur1=x.libelle))
        self.assertEqual(totaux,{'personnes':1});self.assertEqual(rows[0]['axe'],'Emploi / formation')
        dc.annuler(self.u,'evolutions',self.p,x,'Qualification fictive saisie par erreur',bd6.jeton(self.p))
        _,totaux,_=e.calculer(self.u,self.config(population='personnes',axe='evolutions.domaine',filtre1='evolutions.libelle',valeur1=x.libelle))
        self.assertEqual(totaux,{'personnes':0})

    def test_droits_specifiques_et_aucun_droit_implicite(self):
        lecteur=get_user_model().objects.create_user('lecture-territoire-fictive')
        lecteur.user_permissions.add(Permission.objects.get(codename='view_personne'))
        d=self.config(population='personnes',axe='territoires.territoire')
        with self.assertRaises(PermissionDenied):e.calculer(lecteur,d)
        self.assertFalse(lecteur.has_perm('personnes.view_ancrageterritorial'))
        self.assertFalse(self.u.is_staff)
        self.assertFalse(self.u.has_perm('personnes.delete_ancrageterritorial'))

    def test_lecture_bd_recherche_csv_et_filtre_structures(self):
        self.territoire();self.client.force_login(self.u)
        url=reverse('dossiers:fiche_a',args=[self.p.pk,'histoire'])
        self.assertContains(self.client.get(url,{'date':'2026-02-01'}),'Ancrage territorial déclaré')
        self.assertContains(self.client.get(url,{'date':'2026-02-01','rubrique':'territoires'}),'Deux ans déclarés')
        self.assertContains(self.client.get(url,{'date':'2025-12-31','rubrique':'territoires'}),'Aucune déclaration applicable')
        rows,totaux,_=e.calculer(self.u,self.config(population='personnes',axe='territoires.territoire',filtre1='territoires.anciennete_declaree',valeur1='Deux ans déclarés'))
        self.assertEqual(totaux,{'personnes':1});self.assertEqual(rows[0]['axe'],'Agglomération fictive')
        r=self.client.get(reverse('dossiers:rapport_a'),{'date':'2026-02-01','rubrique':'territoires','texte':'Agglomération','format':'csv'})
        self.assertEqual(r.status_code,200);self.assertIn('Deux ans déclarés',r.content.decode())

    def test_premier_et_dernier_par_personne_apres_filtres(self):
        rows,totaux,lignes=e.calculer(self.u,self.config(cohorte='premier'))
        self.assertEqual(totaux,{'personnes':2});self.assertEqual({r['axe']:r['valeur'] for r in rows},{'2026-01':1,'2026-02':1})
        self.assertEqual({x['id']:x['personnes'] for x in lignes},{str(self.a.pk):{self.p.pk},str(self.b.pk):{self.autre.pk}})
        rows,_,_=e.calculer(self.u,self.config(cohorte='dernier'));self.assertEqual({r['axe']:r['valeur'] for r in rows},{'2026-02':2})
        rows,_,_=e.calculer(self.u,self.config(cohorte='premier',filtre1='jour',operation1='depuis',valeur1='2026-02-01'))
        self.assertEqual({r['axe']:r['valeur'] for r in rows},{'2026-02':2})

    def test_situation_a_la_date_du_premier_objet_pas_date_actuelle(self):
        _,totaux,_=e.calculer(self.u,self.config(cohorte='premier',mesure='enfants_connus'))
        self.assertEqual(totaux,{'enfants_connus':1})
        _,totaux,_=e.calculer(self.u,self.config(cohorte='dernier',mesure='adultes_connus'))
        self.assertEqual(totaux,{'adultes_connus':1})
        _,totaux,_=e.calculer(self.u,self.config(cohorte='premier',mesure='ages_inconnus'))
        self.assertEqual(totaux,{'ages_inconnus':1})

    def test_quantites_et_populations_incompatibles_refusees(self):
        for d in [self.config(cohorte='premier',mesure='quantite'),self.config(cohorte='premier',population='appels'),self.config(cohorte='inconnu')]:
            with self.subTest(d=d),self.assertRaises(ValidationError):e.calculer(self.u,d)

    def test_mode_par_defaut_conserve_toutes_les_lignes_et_filtres_meme_personne(self):
        rows,_,lignes=e.calculer(self.u,self.config());self.assertEqual(len(lignes),2)
        self.assertEqual({r['axe']:r['valeur'] for r in rows},{'2026-01':1,'2026-02':2})
        # Utiliser le libellé réellement configuré, pas une convention imposée au registre.
        label=self.p.get_precision_naissance_display()
        rows,_,lignes=e.calculer(self.u,self.config(cohorte='premier',filtre1='precision_naissance',valeur1=label))
        self.assertEqual({x['id']:x['personnes'] for x in lignes},{str(self.a.pk):{self.p.pk}})

    def test_cohorte_preservee_dans_modele_et_export_du_releve(self):
        from .forms_exploration import ExplorationForm
        self.client.force_login(self.u)
        d={k:str(v) for k,v in self.config(cohorte='premier',affichage='detail',nombre_colonnes='1',colonne1='personne').items()}
        f=ExplorationForm(d,acteur=self.u);self.assertTrue(f.is_valid(),f.errors)
        modele=m.ModeleRapport.objects.create(auteur=self.u,nom='Cohorte fictive',parametres={**d,'schema':1,'exploration':True})
        r=self.client.get(reverse('dossiers:explorer_exporter_modele',args=[modele.pk]));self.assertEqual(r.status_code,200)
        self.assertIn('premier',r.content.decode())
        from . import modeles_echange
        copie=modeles_echange.importer(self.u,r.content)
        self.assertEqual(copie.parametres['cohorte'],'premier')
        r=self.client.get(reverse('dossiers:explorer'),{**d,'format':'csv_detail'});self.assertEqual(r.status_code,200)
        lines=list(csv.reader(StringIO(r.content.decode('utf-8-sig'))));self.assertEqual(len(lines),3)
        texte='\n'.join(';'.join(x) for x in lines)
        self.assertEqual(texte.count('Personne fictive H'),1)

    def test_montant_et_libelle_appartiennent_a_la_meme_ressource(self):
        from decimal import Decimal
        for libelle,montant in [('Salaire fictif',Decimal('100')),('Allocation fictive',Decimal('50'))]:
            dc.enregistrer(self.u,'ressources',self.p,date(2026,1,1),None,'Entretien fictif',bd6.jeton(self.p),etat='detail',libelle=libelle,organisme=None,montant=montant,devise='EUR',periodicite='mensuelle')
        d=self.config(population='ressources',mesure='quantite',axe='ressources.libelle',croisement='ressources.montant')
        rows,totaux,_=e.calculer(self.u,d)
        self.assertEqual({(x['axe'],x['croisement']):x['valeur'] for x in rows},{('Salaire fictif','100.00'):Decimal('100'),('Allocation fictive','50.00'):Decimal('50')})
        self.assertEqual(sum(totaux.values()),Decimal('150'))
        _,totaux,_=e.calculer(self.u,self.config(population='personnes',filtre1='ressources.libelle',valeur1='Salaire fictif',filtre2='ressources.montant',operation2='egal',valeur2='50.00'))
        self.assertEqual(totaux,{'personnes':0})
        rows,_,_=e.calculer(self.u,self.config(population='personnes',axe='ressources.libelle',croisement='ressources.montant'))
        connus={(x['axe'],x['croisement']) for x in rows if x['axe']!=e.INCONNU}
        self.assertEqual(connus,{('Salaire fictif','100.00'),('Allocation fictive','50.00')})

    def test_frequentation_et_institution_ne_se_melangent_pas(self):
        for libelle,f in [('Institution fictive A','oui'),('Institution fictive B','non')]:
            dc.enregistrer(self.u,'antecedents',self.p,date(2026,1,1),None,'Entretien fictif',bd6.jeton(self.p),etat='detail',libelle=libelle,frequentation=f,organisme=None,periode_declaree='',date_entree=None,date_sortie=None,precision_dates='')
        d=self.config(population='personnes',axe='antecedents.libelle',croisement='antecedents.frequentation',filtre1='antecedents.libelle',valeur1='Institution fictive A',filtre2='antecedents.frequentation',valeur2='Jamais fréquentée, selon la déclaration')
        _,total,_=e.calculer(self.u,d);self.assertEqual(total,{'personnes':0})
        d.update(filtre2='',valeur2='')
        rows,_,_=e.calculer(self.u,d)
        self.assertEqual([(r['axe'],r['croisement']) for r in rows],[('Institution fictive A','Déjà fréquentée')])

    def test_information_inconnue_sans_declaration_reste_filtrable(self):
        _,total,_=e.calculer(self.u,self.config(population='personnes',filtre1='territoires.territoire',operation1='inconnu'))
        self.assertEqual(total,{'personnes':2})

    def test_sous_totaux_distincts_sans_addition_des_nationalites(self):
        # Les nationalités multiples ventilent une même personne dans deux lignes.
        from .models import ComplementIdentite
        ComplementIdentite.objects.create(personne=self.p,debut=date(2025,1,1),source='Déclaration fictive',auteur=self.u,nationalites=['Fictive A','Fictive B'])
        rows,totaux,_=e.calculer(self.u,self.config(sous_totaux=True,croisement='identite.nationalites'))
        sous={r['axe']:r['valeur'] for r in rows if r.get('sous_total')}
        self.assertEqual(sous,{'2026-01':1,'2026-02':2});self.assertEqual(totaux,{'personnes':2})
        self.assertEqual(sum(r['valeur'] for r in rows if r['axe']=='2026-02' and not r.get('sous_total')),3)

    def test_sous_total_quantite_collective_n_est_pas_multiplie(self):
        from decimal import Decimal
        m.ComplementIdentite.objects.create(personne=self.p,debut=date(2025,1,1),source='Déclaration fictive',auteur=self.u,nationalites=['Fictive A','Fictive B'])
        dc.enregistrer(self.u,'ressources',self.p,date(2026,1,1),None,'Entretien fictif',bd6.jeton(self.p),etat='detail',libelle='Salaire fictif',organisme=None,montant=Decimal('100'),devise='EUR',periodicite='mensuelle')
        rows,totaux,_=e.calculer(self.u,self.config(population='ressources',mesure='quantite',sous_totaux=True,axe='type',croisement='identite.nationalites'))
        self.assertEqual([r['valeur'] for r in rows if r.get('sous_total')],[Decimal('100')]);self.assertEqual(sum(totaux.values()),Decimal('100'))

    def test_sous_totaux_exportes_et_signales_comme_tels(self):
        self.client.force_login(self.u)
        d={k:str(v) for k,v in self.config(sous_totaux=True,croisement='precision_naissance').items()}
        r=self.client.get(reverse('dossiers:explorer'),{**d,'format':'csv'})
        self.assertEqual(r.status_code,200)
        rows=list(csv.reader(StringIO(r.content.decode('utf-8-sig')),delimiter=';'))
        self.assertEqual(rows[0][-2:],['Type de ligne','Profondeur du sous-total'])
        self.assertEqual(sum(r[-2]=='Sous-total' for r in rows[1:]),2)
        self.assertContains(self.client.get(reverse('dossiers:explorer'),d),'Sous-total —')


    def test_derniere_adresse_fixe_distincte_du_contact_et_de_la_presence(self):
        from . import coordonnees
        vals=dict(rue='Rue fictive',code_postal='00100',ville='Ville fictive',pays='',telephone='',courriel='',fax='')
        ancien=coordonnees.renseigner(self.u,self.p,date(2026,1,1),'Déclaration fictive',bd6.jeton(self.p),usage_adresse='dernier_fixe',**vals)
        coordonnees.renseigner(self.u,self.p,date(2026,2,1),'Nouvelle adresse fictive',bd6.jeton(self.p),usage_adresse='contact',**{**vals,'rue':'Adresse de courrier fictive'})
        self.assertEqual(coordonnees.a_date([self.p],date(2026,1,20)).get().usage_adresse,'dernier_fixe')
        self.assertEqual(coordonnees.a_date([self.p],date(2026,2,20)).get().usage_adresse,'contact')
        ancien.refresh_from_db();self.assertEqual(ancien.fin,date(2026,2,1))
        self.assertEqual(m.Sejour.objects.count(),2)
        self.client.force_login(self.u)
        url=reverse('dossiers:rapport_coordonnees')
        r=self.client.get(url,{'date':'2026-01-20','usage_adresse':'dernier_fixe','format':'csv'})
        self.assertEqual(r.status_code,200);self.assertIn('dernier_fixe',r.content.decode());self.assertIn('00100',r.content.decode())
        _,totaux,_=e.calculer(self.u,self.config(population='personnes',filtre1='coordonnees.usage_adresse',valeur1='Adresse de contact déclarée'))
        self.assertEqual(totaux,{'personnes':1})

    def test_anciennes_coordonnees_non_qualifiees_et_correction_tracee(self):
        from . import coordonnees
        vals=dict(rue='Rue fictive',code_postal='',ville='',pays='',telephone='',courriel='',fax='')
        x=coordonnees.renseigner(self.u,self.p,date(2026,1,1),'Ancienne saisie fictive',bd6.jeton(self.p),**vals)
        self.assertEqual(x.usage_adresse,'')
        self.client.force_login(self.u)
        r=self.client.get(reverse('dossiers:rapport_coordonnees'),{'date':'2026-02-20','usage_adresse':'non_qualifiee','format':'csv'})
        self.assertIn('Personne fictive H',r.content.decode());self.assertNotIn('Autre personne fictive H',r.content.decode())
        coordonnees.renseigner(self.u,self.p,x.debut,'Relecture fictive',bd6.jeton(self.p),motif='Qualification omise',correction=x.pk,usage_adresse='dernier_fixe',**vals)
        x.refresh_from_db();self.assertEqual(x.usage_adresse,'dernier_fixe')
        self.assertEqual(x.revisions.first().avant[0]['usage_adresse'],'')
