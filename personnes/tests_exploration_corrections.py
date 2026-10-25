"""ST1 : oracles discriminants, sans changer les sources sociales."""
import csv
from datetime import date
from decimal import Decimal
from io import StringIO
from urllib.parse import parse_qs, urlsplit
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from . import bd6, dossier_complet, exploration as e, interventions, models as m, parcours, tests_meta_f
from .tests_parcours import valeurs


class CorrectionsExplorationTests(TestCase):
    setUpTestData = classmethod(tests_meta_f.ConsolidationStatistiques.setUpTestData.__func__)
    config = tests_meta_f.ConsolidationStatistiques.config

    def calcul(self, **kw):
        return e.calculer(self.u, self.config(**kw))

    def params(self, **kw):
        return {k: str(v) for k, v in self.config(**kw).items()}

    def csv(self, params, detail=False):
        self.client.force_login(self.u)
        r = self.client.get(reverse('dossiers:explorer'), {**params, 'format': 'csv_detail' if detail else 'csv'})
        self.assertEqual(r.status_code, 200)
        return list(csv.DictReader(StringIO(r.content.decode()), delimiter=';'))

    def lieux(self, homonymes=False):
        lieux = []
        for nom, debut, fin in [('A', 1, 3), ('B', 3, 5)]:
            lieu = m.LieuHebergement.objects.create(libelle='Chambre fictive' if homonymes else 'Lieu fictif '+nom, cree_par=self.u)
            m.Affectation.objects.create(sejour=self.sejour, lieu=lieu, debut=date(2026, 1, debut), fin=date(2026, 1, fin))
            lieux.append(lieu)
        return lieux

    def demandes(self):
        demandes = []
        for motif, etat in [('Motif A fictif', 'attente'), ('Motif B fictif', 'refusee')]:
            demandes.append(parcours.creer(self.u, 'demandes', self.adulte, [self.adulte], date(2026, 1, 1),
                'Entretien fictif', bd6.jeton(self.adulte), **valeurs('demandes', motif_demande=motif,
                    etat=etat, motif_decision='Refus fictif' if etat=='refusee' else '')))
        return demandes

    def mission(self, **kw):
        prof = m.Intervenant.objects.create(libelle='Professionnel fictif ST1', cree_par=self.u)
        return m.AffectationIntervenant.objects.create(accompagnement=self.prise, debut=date(2026, 1, 1),
            role='referent', intervenant=prof, source='Entretien fictif', auteur=self.u, **kw)

    def test_nuitees_filtrees_et_releve_suivent_la_personne(self):
        self.lieux()
        for code in ('sejours','affectations'):
            with self.subTest(population=code):
                r, t, xs = self.calcul(population=code, mesure='quantite', filtre1='age', operation1='egal', valeur1='18')
                self.assertEqual(list(t.values()), [4])
                self.assertEqual({p for x in xs for p in x['personnes']}, {self.anniversaire.pk})
                self.assertEqual(sum(x['quantite'] for x in xs), 4)
                params=self.params(population=code, mesure='quantite', filtre1='age', operation1='egal', valeur1='18',
                    affichage='detail', nombre_colonnes=2, colonne1='personne', colonne2='quantite')
                lignes=self.csv(params, detail=True)
                self.assertEqual(sum(Decimal(x[e.DIMENSIONS['quantite']]) for x in lignes), 4)
                self.assertTrue(all('Anniversaire fictif F' in x[e.DIMENSIONS['personne']] for x in lignes))
                self.assertTrue(all('Adulte fictif F' not in x[e.DIMENSIONS['personne']] for x in lignes))

    def test_age_partitionne_les_nuitees_et_sous_totaux(self):
        m.ComplementIdentite.objects.create(personne=self.adulte, debut=date(2026,1,1), auteur=self.u,
            source='Déclaration fictive', nationalites=['Fictive A','Fictive B'])
        r,t,_=self.calcul(mesure='quantite',axe='age')
        self.assertEqual({x['axe']:x['valeur'] for x in r},{'18':4,'46':4,e.INCONNU:4})
        self.assertEqual(list(t.values()),[12])
        r,t,_=self.calcul(mesure='quantite',axe='age',croisement='identite.nationalites',sous_totaux=True)
        self.assertEqual({x['axe']:x['valeur'] for x in r if x.get('sous_total')},{'18':4,'46':4,e.INCONNU:4})
        self.assertEqual(sum(x['valeur'] for x in r if not x.get('sous_total')),16)
        self.assertEqual(list(t.values()),[12])
        lignes=self.csv(self.params(mesure='quantite',axe='age',croisement='identite.nationalites',sous_totaux=True))
        self.assertEqual(sum(Decimal(x['Valeur']) for x in lignes if x['Type de ligne']=='Sous-total'),12)

    def test_filtre_quantite_apres_selection_des_personnes(self):
        for seuil,attendu in [('4',1),('5',0)]:
            r,t,_=self.calcul(mesure='objets',filtre1='age',operation1='egal',valeur1='18',
                filtre2='quantite',operation2='gte',valeur2=seuil)
            self.assertEqual(t,{'objets':attendu})
        self.assertEqual(self.calcul(filtre1='quantite',operation1='gte',valeur1='5')[1],{'objets':1})

    def test_min_max_moyenne_sur_nuitees_retenues_par_objet(self):
        autre=m.Sejour.objects.create(accord=self.accord,debut=date(2026,1,1),fin=date(2026,1,3),cree_par=self.u)
        autre.beneficiaires.set([self.adulte])
        for mesure,attendu in [('quantite',6),('minimum',2),('maximum',4),('moyenne',3)]:
            _,t,_=self.calcul(mesure=mesure,filtre1='age',operation1='egal',valeur1='46')
            self.assertEqual(list(t.values()),[attendu])

    def test_fragments_continuation_periode_et_integralite(self):
        self.sejour.fin=date(2026,1,3);self.sejour.save(update_fields=['fin'])
        for p,fin in [(self.adulte,date(2026,1,5)),(self.anniversaire,date(2026,1,4)),(self.inconnu,date(2026,1,5))]:
            x=m.Sejour.objects.create(accord=self.accord,origine_collective=self.sejour,debut=date(2026,1,3),fin=fin,cree_par=self.u)
            x.beneficiaires.set([p])
        filtre=dict(filtre1='age',operation1='egal',valeur1='18')
        self.assertEqual(list(self.calcul(mesure='quantite',**filtre)[1].values()),[3])
        self.assertEqual(list(self.calcul(mesure='quantite',debut=date(2026,1,3),fin=date(2026,1,4),**filtre)[1].values()),[1])
        self.assertEqual(list(self.calcul(mesure='quantite',debut=date(2026,1,3),fin=date(2026,1,4),portion='integrale',**filtre)[1].values()),[3])
        r,t,_=self.calcul(mesure='quantite',axe='age')
        self.assertEqual({x['axe']:x['valeur'] for x in r},{'18':3,'46':4,e.INCONNU:4})
        self.assertEqual(list(t.values()),[11])

    def test_remise_collective_et_cout_non_repartis(self):
        from . import aides,financements
        type_aide=aides.cataloguer(self.u,aides.jeton_catalogue(),'Fictif',nature='transport',libelle='Carte collective fictive',unite='carte',fractionnable=False,precision='',actif=True)
        accord=aides.accorder(self.u,self.prise,type_aide,self.ps,bd6.jeton(self.prise),debut=date(2026,1,1),fin=date(2026,1,5),
            quantite=Decimal(5),prestataire=None,financeur=None,valeur_bon=None,devise='EUR',source='Fictif')
        aides.remettre(self.u,accord,self.ps,date(2026,1,2),Decimal(2),'Fictif',bd6.jeton(accord))
        financements.enregistrer(self.u,accord,financements.jeton(accord),'Fictif','definition',
            [dict(phase='autorise',date=date(2026,1,2),libelle='Carte collective fictive',unite='carte',categorie='',quantite=Decimal(2),prix=Decimal(3),tarif=None,justification='Fictif')],[],
            emetteur=None,mentions='',debut=date(2026,1,1),fin=date(2026,1,5),devise='EUR',prestataire=None,prescripteur=None,facturation=None,signataire=None,reference='',source='Fictif')
        for population,attendu in [('aides',2),('couts',6)]:
            r,t,_=self.calcul(population=population,mesure='quantite',axe='age')
            self.assertEqual([x['valeur'] for x in r],[attendu]*3)
            self.assertEqual(list(t.values()),[attendu])
            _,t,_=self.calcul(population=population,mesure='quantite',filtre1='age',operation1='egal',valeur1='18')
            self.assertEqual(list(t.values()),[attendu])

    def test_lieux_homonymes_et_ancien_critere(self):
        a,b=self.lieux(homonymes=True)
        r,t,_=self.calcul(population='affectations',mesure='quantite',axe='lieu')
        self.assertEqual(len(r),2);self.assertEqual({x['valeur'] for x in r},{6})
        for lieu in (a,b):self.assertTrue(any(str(lieu.pk) in x['axe'] for x in r))
        self.assertEqual(list(t.values()),[12])
        r,t,_=self.calcul(population='affectations',mesure='quantite',axe='lieu',filtre1='lieu',valeur1='Chambre fictive')
        self.assertEqual(len(r),2);self.assertEqual(list(t.values()),[12])
        r,t,_=self.calcul(population='affectations',mesure='quantite',axe='lieu',filtre1='lieu_id',valeur1=str(a.pk))
        self.assertEqual(len(r),1);self.assertEqual(list(t.values()),[6])
        for axe,croisement in [('lieu','total'),('total','lieu')]:
            lignes=self.csv(self.params(population='affectations',mesure='quantite',axe=axe,croisement=croisement))
            self.assertEqual(len(lignes),2);self.assertEqual({Decimal(x['Valeur']) for x in lignes},{6})

    def test_lieux_sous_totaux_et_rapport_specialise(self):
        self.lieux(homonymes=True)
        r,t,_=self.calcul(population='affectations',mesure='quantite',axe='lieu',croisement='age',sous_totaux=True)
        self.assertEqual(len([x for x in r if x.get('sous_total')]),2)
        self.assertEqual([x['valeur'] for x in r if x.get('sous_total')],[6,6])
        self.assertEqual(sum(x['valeur'] for x in r if not x.get('sous_total')),12)
        from .statistiques import exploration_affectations
        specialise=exploration_affectations(date(2026,1,1),date(2026,1,5))
        self.assertEqual(len(specialise),2)
        self.assertEqual(sum(x['nuitees'] for x in specialise),12)

    def test_lieu_unique_et_identifiant_dans_releve(self):
        a,b=self.lieux()
        r,_,_=self.calcul(population='affectations',mesure='quantite',axe='lieu')
        self.assertEqual({x['axe']:x['valeur'] for x in r},{str(a):6,str(b):6})
        lignes=self.csv(self.params(population='affectations',mesure='quantite',nombre_colonnes=2,colonne1='lieu',colonne2='lieu_id'),detail=True)
        self.assertEqual({x[e.DIMENSIONS['lieu_id']] for x in lignes},{str(a.pk),str(b.pk)})

    def test_mission_bornee_par_parent_et_fin_propre(self):
        mission=self.mission()
        m.Accompagnement.objects.filter(pk=self.prise.pk).update(fin=date(2026,1,5))
        for ref,attendu in [(date(2024,12,31),0),(date(2026,1,1),1),(date(2026,1,4),1),(date(2026,1,5),0),(date(2026,1,31),0)]:
            _,t,_=self.calcul(population='prises',reference=ref,filtre1='mission.professionnel',valeur1=str(mission.intervenant))
            self.assertEqual(t,{'objets':attendu})
            self.prise.refresh_from_db();self.assertEqual(interventions.a_date(self.prise,ref).count(),attendu)
        mission.fin=date(2026,1,3);mission.save(update_fields=['fin'])
        self.assertEqual(self.calcul(population='prises',reference=date(2026,1,3),filtre1='mission.professionnel',valeur1=str(mission.intervenant))[1],{'objets':0})

    def test_mission_avant_debut_parent(self):
        mission=self.mission()
        m.Accompagnement.objects.filter(pk=self.prise.pk).update(debut=date(2026,1,3))
        self.assertEqual(self.calcul(population='prises',reference=date(2026,1,2),filtre1='mission.professionnel',valeur1=str(mission.intervenant))[1],{'objets':0})
        self.assertEqual(self.calcul(population='prises',reference=date(2026,1,3),filtre1='mission.professionnel',valeur1=str(mission.intervenant))[1],{'objets':1})

    def test_mission_date_fait_csv_annulation_droits(self):
        mission=self.mission()
        m.Accompagnement.objects.filter(pk=self.prise.pk).update(fin=date(2026,1,5))
        params=self.params(population='accords_hebergement',axe='mission.professionnel',reference_mode='fait')
        self.assertEqual(self.csv(params)[0]['Axe'],str(mission.intervenant))
        self.assertEqual(self.csv({**params,'reference_mode':'commune'})[0]['Axe'],e.INCONNU)
        mission.annule_le=timezone.now();mission.annule_par=self.u;mission.motif_annulation='Erreur fictive';mission.save()
        self.assertEqual(self.csv(params)[0]['Axe'],e.INCONNU)
        self.u.user_permissions.remove(Permission.objects.get(codename='view_affectationintervenant'))
        self.u=get_user_model().objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):self.calcul(population='prises',axe='mission.professionnel')

    def test_meme_demande_etat_motif_classements_csv(self):
        a,b=self.demandes()
        params=self.params(population='demandes',axe='motif',filtre1='etat',valeur1='Refusée',filtre2='demande.motif_demande',valeur2='Motif A fictif')
        self.assertEqual(self.calcul(population='demandes',axe='motif',filtre1='etat',valeur1='Refusée',filtre2='demande.motif_demande',valeur2='Motif A fictif')[1],{'objets':0})
        r,_,_=self.calcul(population='demandes',axe='motif',croisement='demande.motif_demande')
        self.assertEqual({(x['axe'],x['croisement']):x['valeur'] for x in r},{('Motif A fictif','Motif A fictif'):1,('Motif B fictif','Motif B fictif'):1})
        self.assertEqual(self.csv(params),[]);self.assertEqual(self.csv(params,detail=True),[])
        params.update(valeur2='Motif B fictif',nombre_colonnes='2',colonne1='motif',colonne2='demande.motif_demande')
        lignes=self.csv(params,detail=True)
        self.assertEqual(len(lignes),1);self.assertEqual(lignes[0]['Objet'],str(b.pk))
        self.assertEqual(lignes[0][e.DIMENSIONS['demande.motif_demande']],'Motif B fictif')

    def test_demande_derniere_version_autres_populations_a_reference(self):
        a,b=self.demandes()
        parcours.enregistrer(self.u,'demandes',a,date(2026,1,3),'Changement fictif',bd6.jeton(a),**valeurs('demandes',motif_demande='Motif C fictif'))
        r,_,_=self.calcul(population='demandes',reference=date(2026,1,2),axe='motif',croisement='demande.motif_demande')
        self.assertEqual({(x['axe'],x['croisement']) for x in r},{('Motif C fictif','Motif C fictif'),('Motif B fictif','Motif B fictif')})
        r,_,_=self.calcul(population='personnes',reference=date(2026,1,2),axe='demande.motif_demande')
        self.assertEqual({x['axe'] for x in r},{'Motif A fictif','Motif B fictif',e.INCONNU})
        parcours.annuler(self.u,'demandes',b,'Erreur fictive',bd6.jeton(b))
        self.assertEqual(self.calcul(population='demandes')[1],{'objets':1})

    def test_retour_bd_modele_selection_et_pdf(self):
        call_command('autoriser_bd6',self.u.username,stdout=StringIO());self.client.force_login(self.u)
        params=self.params(mesure='quantite',affichage='detail',nombre_colonnes=2,colonne1='personne',colonne2='quantite',filtre1='age',operation1='egal',valeur1='18')
        url=reverse('dossiers:explorer');r=self.client.get(url,params)
        self.assertEqual(list(r.context['totaux'].values()),[4]);self.assertEqual(len(r.context['page_obj']),1)
        lien=r.context['page_obj'][0]['url']
        from .exploration_releve import retour_verifie
        retour=retour_verifie(self.u,parse_qs(urlsplit(lien).query)['retour_exploration'][0])
        self.assertEqual(parse_qs(urlsplit(retour).query)['valeur1'],['18'])
        self.assertContains(self.client.get(lien),'Revenir aux résultats du rapport')
        self.assertEqual(list(self.client.get(retour).context['totaux'].values()),[4])
        r=self.client.post(url,{**params,'nom':'Nuitées individuelles fictives ST1'});self.assertEqual(r.status_code,302)
        self.assertEqual(list(self.client.get(r.url).context['totaux'].values()),[4])
        for fmt in ('pdf','pdf_detail'):
            r=self.client.get(url,{**params,'format':fmt});self.assertEqual(r.status_code,200);self.assertTrue(r.content.startswith(b'%PDF-'))

    def test_source_sociale_brute_distincte_projection_dossier(self):
        call_command('autoriser_bd6',self.u.username,stdout=StringIO());self.u=get_user_model().objects.get(pk=self.u.pk)
        bd6.renseigner(self.u,self.adulte,'ressources','sans_ressources',date(2026,1,1),'Ancienne synthèse fictive',bd6.jeton(self.adulte))
        dossier_complet.enregistrer(self.u,'ressources',self.adulte,date(2026,1,1),None,'Ressource fictive',bd6.jeton(self.adulte),etat='detail',libelle='Salaire fictif',organisme=None,montant=Decimal(100),devise='EUR',periodicite='mensuelle')
        dossier=bd6.etat(self.u,[self.adulte],date(2026,1,31))
        self.assertEqual(next(x for x in dossier[0]['lignes'] if x['dimension']=='ressources')['texte'],'Ressources déclarées')
        r,_,_=self.calcul(population='personnes',axe='social.ressources',filtre1='personne',operation1='contient',valeur1='Adulte fictif')
        self.assertEqual([x['axe'] for x in r],['sans_ressources'])
        self.assertEqual(self.csv(self.params(population='personnes',axe='social.ressources',filtre1='personne',operation1='contient',valeur1='Adulte fictif'))[0]['Axe'],'sans_ressources')
