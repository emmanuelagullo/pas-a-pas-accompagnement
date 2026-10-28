from django.test import TestCase
from django.urls import reverse
from . import tests_meta_f

class ErgonomieCompositionTests(TestCase):
    setUpTestData=classmethod(tests_meta_f.ConsolidationStatistiques.setUpTestData.__func__)
    def setUp(self):self.client.force_login(self.u)
    def get(self,**kw):return self.client.get(reverse('dossiers:explorer'),tests_meta_f.ConsolidationStatistiques.config(self,**kw))
    def test_repartition_des_regles_et_choix(self):
        r=self.get(panneau='retenir');p={x['cle']:x for x in r.context['parties_analyse']}
        noms=lambda cle:{f.name for g in p[cle]['groupes'] for f in g['champs']}
        self.assertIn('population',noms('retenir'));self.assertIn('debut',noms('retenir'))
        self.assertNotIn('portion',noms('retenir'));self.assertIn('portion',noms('compter'))
        self.assertIn('sous_totaux',noms('classer'))
        self.assertEqual(list(r.context['totaux'].values()),[1])
        self.assertContains(r,'Règles de sélection');self.assertContains(r,'Règles de calcul')
    def test_case_avant_libelle_et_valeurs_inapplicables_conservees(self):
        r=self.get(population='personnes',panneau='classer')
        h=r.content.decode();self.assertLess(h.index('id="id_sous_totaux"'),h.index('for="id_sous_totaux"'))
        self.assertContains(r,'type="hidden" name="portion"')
        r=self.get(population='personnes',portion='integrale')
        self.assertContains(r,'id="id_portion"');self.assertEqual(r.context['form']['portion'].value(),'integrale')
    def test_compteurs_correspondent_au_tableau_et_aux_mesures_uniques(self):
        r=self.get(affichage='detail',nombre_colonnes=2,colonne1='personne',colonne2='age',nombre_mesures=2,mesure2='objets')
        p={x['cle']:x for x in r.context['parties_analyse']}
        self.assertEqual(p['retenir']['compteur'],'0 filtres supplémentaires')
        self.assertEqual(p['afficher']['compteur'],'4 colonnes')
        self.assertEqual(len(r.context['colonnes_detail'])+2,4)
        self.assertEqual(p['compter']['compteur'],'1 mesure')
        self.assertEqual(p['classer']['compteur'],'Aucun regroupement')
        r=self.get(axe='age',croisement='mois',niveaux=3,axe3='type',nombre_mesures=2,mesure2='personnes',filtre1='age',operation1='gte',valeur1='18')
        p={x['cle']:x for x in r.context['parties_analyse']}
        self.assertEqual(p['retenir']['compteur'],'1 filtre supplémentaire')
        self.assertEqual(p['afficher']['compteur'],'6 colonnes')
        self.assertEqual(p['compter']['compteur'],'2 mesures');self.assertEqual(p['classer']['compteur'],'3 niveaux')
    def test_regles_particulieres_visibles_dans_syntheses(self):
        r=self.get(portion='integrale',mouvement='entrees')
        p={x['cle']:x for x in r.context['parties_analyse']}
        self.assertIn('Intégralité',p['compter']['resume']);self.assertIn('débuts',p['retenir']['resume'])
        r=self.get(niveaux=8)
        self.assertTrue(all(p['a_verifier'] for p in r.context['parties_analyse']))
