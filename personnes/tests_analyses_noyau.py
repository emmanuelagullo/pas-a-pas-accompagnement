from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError, PermissionDenied
from . import tests_meta_f as fixtures, models as m, repas, analyses as a


class NoyauAnalysesTests(TestCase):
    setUpTestData=classmethod(fixtures.ConsolidationStatistiques.setUpTestData.__func__)

    def definition(self,**kw):
        return {**a.defaut(),'debut':'2026-01-01','fin':'2026-01-05','reference':'2026-01-04',**kw}

    def test_personnes_sans_repas_et_mesures_independantes_sans_produit(self):
        repas.distribuer(self.u,self.ar,self.adulte,date(2026,1,2),2)
        repas.distribuer(self.u,self.ar,self.adulte,date(2026,1,3),3)
        d=self.definition(affichage='detail',criteres=[dict(source='prises',mode='avec')],mesures=[dict(source='repas',mesure='quantite'),dict(source='sejours',mesure='quantite')])
        r=a.calculer(self.u,d)
        self.assertEqual(len(r['details']),3)
        par_personne={x['objet']['id']:x['mesures'] for x in r['details']}
        self.assertEqual(list(par_personne[str(self.adulte.pk)][0].values()),[5])
        self.assertEqual(list(par_personne[str(self.inconnu.pk)][0].values()),[0])
        self.assertEqual([list(x[1].values())[0] for x in par_personne.values()],[4,4,4])
        self.assertEqual(sum(r['mesures'][0]['totaux'].values()),5)
        self.assertEqual(sum(r['mesures'][1]['totaux'].values()),12)

    def test_sans_repas_et_meme_personne_pour_tous_les_criteres(self):
        repas.distribuer(self.u,self.ar,self.adulte,date(2026,1,2),2)
        d=self.definition(criteres=[dict(source='prises'),dict(source='repas',mode='sans')],mesures=[dict(source='personnes',mesure='personnes')])
        r=a.calculer(self.u,d)
        self.assertEqual(r['mesures'][0]['totaux'],{'personnes':2})

    def test_criteres_sur_un_meme_fait_ou_deux_faits(self):
        repas.distribuer(self.u,self.ar,self.adulte,date(2026,1,2),2)
        autre=m.AccordRepas.objects.create(accompagnement=self.prise,debut=date(2026,1,1),fin=date(2026,1,5),service='diner',cree_par=self.u)
        autre.beneficiaires.set([self.adulte]);repas.distribuer(self.u,autre,self.adulte,date(2026,1,3),1)
        f1=dict(champ='jour',valeur='2026-01-02');f2=dict(champ='type',valeur='Dîner')
        d=self.definition(criteres=[dict(source='repas',filtres=[f1,f2])],mesures=[dict(source='personnes',mesure='personnes')])
        self.assertEqual(a.calculer(self.u,d)['mesures'][0]['totaux'],{'personnes':0})
        d['criteres']=[dict(source='repas',filtres=[f1]),dict(source='repas',filtres=[f2])]
        self.assertEqual(a.calculer(self.u,d)['mesures'][0]['totaux'],{'personnes':1})

    def test_plusieurs_regles_temporelles_et_distincts(self):
        d=self.definition(fin='2026-01-06',mesures=[dict(source='sejours',mesure='objets',mouvement='entrees'),dict(source='sejours',mesure='objets',mouvement='sorties'),dict(source='sejours',mesure='durees_moyenne',mouvement='sorties',portion='integrale')])
        r=a.calculer(self.u,d)
        self.assertEqual([sum(x['totaux'].values()) for x in r['mesures']],[1,1,4])

    def test_droits_et_parametres_non_representables_refuses(self):
        d=self.definition();d['axes']=['sql.libre']
        with self.assertRaises(ValidationError):a.calculer(self.u,d)
        d=self.definition(mesures=[dict(source='repas',mesure='nuits_distinctes')])
        with self.assertRaises(ValidationError):a.calculer(self.u,d)
        self.u.user_permissions.clear()
        self.u=type(self.u).objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied):a.calculer(self.u,self.definition())

    def test_declarations_detaillees_non_renseigne_et_retrait(self):
        d=self.definition(affichage='detail',colonnes=['personne','famille.situation_familiale','famille.declaration_applicable','famille.source'],mesures=[dict(source='famille',mesure='objets')])
        r=a.calculer(self.u,d);self.assertEqual(len(r['details']),3)
        self.assertEqual(r['mesures'][0]['totaux'],{'objets':2})
        m.DeclarationFamiliale.objects.filter(personne=self.adulte).update(retire_le=__import__('django.utils.timezone',fromlist=['now']).now())
        self.assertEqual(a.calculer(self.u,d)['mesures'][0]['totaux'],{'objets':1})

    def test_absence_declaration_montant_n_est_pas_zero(self):
        d=self.definition(affichage='detail',mesures=[dict(source='ressources',mesure='quantite')])
        r=a.calculer(self.u,d)
        self.assertTrue(all(list(x['mesures'][0].values())==[None] for x in r['details']))
