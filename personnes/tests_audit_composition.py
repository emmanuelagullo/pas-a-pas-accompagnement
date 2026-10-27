"""Écarts chiffrés à conserver jusqu’à leur traduction fidèle (audit du lot 3)."""
from datetime import date
from django.test import TestCase
from . import models as m, tests_meta_f, exploration as e, statistiques, rapports_metier


class EcartsCompositionTests(TestCase):
    setUpTestData=classmethod(tests_meta_f.ConsolidationStatistiques.setUpTestData.__func__)
    config=tests_meta_f.ConsolidationStatistiques.config

    def test_nuits_distinctes_ne_sont_pas_la_somme_des_sejours(self):
        s=m.Sejour.objects.create(accord=self.accord,debut=date(2026,1,2),fin=date(2026,1,4),cree_par=self.u)
        s.beneficiaires.set([self.adulte])
        m.Absence.objects.create(sejour=self.sejour,debut=date(2026,1,2),fin=date(2026,1,3))
        bilan=statistiques.bilan(date(2026,1,1),date(2026,1,5))
        self.assertEqual(bilan['nuitees_theoriques'],14)
        self.assertEqual(bilan['nuits_distinctes'],12)
        self.assertEqual(bilan['nuits_hors_absences_declarees'],10)
        _,totaux,_=e.calculer(self.u,self.config(mesure='quantite'))
        self.assertEqual(sum(totaux.values()),14)

    def test_duree_civile_n_est_pas_quantite_personnes_nuitees(self):
        rapport=rapports_metier.mouvements(date(2026,1,1),date(2026,1,6))
        self.assertEqual(rapport['nuits_sejours_clos_total'],4)
        self.assertEqual(rapport['nuits_sejours_clos_moyenne'],4)
        _,totaux,_=e.calculer(self.u,self.config(fin=date(2026,1,6),mouvement='sorties',portion='integrale',mesure='moyenne'))
        self.assertEqual(sum(totaux.values()),12)

    def test_age_et_precision_deja_disponibles_sur_la_population_retenue(self):
        reference,comptes,qualite=rapports_metier.ages(date(2026,1,1),date(2026,1,5))
        self.assertEqual(reference,date(2026,1,4));self.assertEqual(comptes,{46:1,18:1})
        self.assertEqual(qualite['inconnue'],1)
        rows,totaux,_=e.calculer(self.u,self.config(reference=reference,mesure='personnes',axe='age'))
        self.assertEqual(sorted(x['valeur'] for x in rows),[1,1,1]);self.assertEqual(totaux,{'personnes':3})
