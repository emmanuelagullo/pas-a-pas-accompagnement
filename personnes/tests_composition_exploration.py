from datetime import date
from io import StringIO
from django.test import TestCase
from django.urls import reverse
from . import exploration as e, models as m, tests_meta_f


class CompositionTests(TestCase):
    setUpTestData=classmethod(tests_meta_f.ConsolidationStatistiques.setUpTestData.__func__)
    config=tests_meta_f.ConsolidationStatistiques.config
    def params(self,**kw):return {k:str(v) for k,v in self.config(**kw).items()}
    def get(self,d):
        self.client.force_login(self.u)
        r=self.client.get(reverse('dossiers:explorer'),d)
        self.assertEqual(r.status_code,200);return r

    def test_quatre_parties_modification_directe_et_criteres_conserves(self):
        d=self.params(mesure='quantite',filtre1='age',operation1='egal',valeur1='18',axe='age',affichage='detail',nombre_colonnes=1,colonne1='personne')
        for panneau in ('retenir','afficher','compter','classer'):
            r=self.get({**d,'panneau':panneau})
            self.assertFalse(r.context['form'].errors,r.context['form'].errors)
            self.assertEqual(list(r.context['totaux'].values()),[4])
            self.assertEqual([p['cle'] for p in r.context['parties_analyse'] if p['ouvert']],[panneau])
            self.assertEqual(r.context['form']['valeur1'].value(),'18')
            self.assertEqual(r.context['form']['colonne1'].value(),'personne')
            for titre in ('Retenir','Afficher','Compter','Classer'):self.assertContains(r,titre)
            self.assertContains(r,'Rapports courants')

    def test_deplacer_axes_et_classes_ensemble_sans_changer_population(self):
        d=self.params(mesure='personnes',axe='age',classes='Jeune|0|20\nAdulte|20|',croisement='famille.grossesse',niveaux=3,axe3='mois',sous_totaux=True)
        r=self.get({**d,'deplacer_niveau':'1:1'})
        f=r.context['form'];self.assertFalse(f.errors,f.errors)
        self.assertEqual(f['axe'].value(),'famille.grossesse');self.assertEqual(f['croisement'].value(),'age')
        self.assertEqual(f['classes'].value(),'');self.assertEqual(f['classes_croisement'].value(),d['classes'])
        self.assertEqual(r.context['totaux'],{'personnes':3})
        self.assertEqual([p['cle'] for p in r.context['parties_analyse'] if p['ouvert']],['classer'])
        self.assertTrue(any(x.get('sous_total') for x in r.context['page_obj']))

    def test_retirer_niveau_conserve_mesures_colonnes_et_filtre(self):
        d=self.params(axe='age',croisement='mois',axe3='precision_naissance',niveaux=3,mesure='personnes',nombre_mesures=2,mesure2='ages_inconnus',
            affichage='detail',nombre_colonnes=1,colonne1='personne',filtre1='age',operation1='gte',valeur1='18')
        r=self.get({**d,'retirer_niveau':'1'});f=r.context['form']
        self.assertEqual(f['axe'].value(),'mois');self.assertEqual(f['croisement'].value(),'precision_naissance')
        self.assertEqual(f['mesure2'].value(),'ages_inconnus');self.assertEqual(f['colonne1'].value(),'personne')
        self.assertEqual(f['valeur1'].value(),'18');self.assertEqual(r.context['nombre'],1)

    def test_effectifs_distincts_sous_totaux_apres_reorganisation(self):
        m.ComplementIdentite.objects.create(personne=self.adulte,debut=date(2026,1,1),auteur=self.u,source='Fictif',nationalites=['A','B'])
        d=self.params(population='personnes',mesure='personnes',axe='identite.nationalites',croisement='total',sous_totaux=True)
        r=self.get({**d,'deplacer_niveau':'1:1'})
        self.assertEqual(r.context['totaux'],{'personnes':3})
        self.assertEqual([x['valeur'] for x in r.context['page_obj'] if x.get('sous_total')],[3])
        self.assertEqual(sum(x['valeur'] for x in r.context['page_obj'] if not x.get('sous_total')),4)

    def test_erreurs_et_ajouts_ouvrent_le_bon_panneau_sans_js(self):
        for action,panneau in [('ajouter_niveau','classer'),('ajouter_filtre','retenir'),('ajouter_colonne','afficher'),('ajouter_mesure','compter')]:
            r=self.get({action:'1'})
            self.assertEqual([p['cle'] for p in r.context['parties_analyse'] if p['ouvert']],[panneau])
        r=self.get({'niveaux':'8'});self.assertContains(r,'errorlist');self.assertContains(r,'<details open>')
        self.assertContains(r,'déclaration personnelle saisie')

    def test_action_invalide_ne_modifie_pas_les_parametres(self):
        d=self.params(axe='age',croisement='mois')
        r=self.get({**d,'deplacer_niveau':'999:5'})
        self.assertEqual(r.context['form']['axe'].value(),'age')
        self.assertEqual(r.context['form']['croisement'].value(),'mois')
