"""Ergonomie contextuelle, conservation et résultats indépendants."""
from django.test import TestCase
from django.urls import reverse
from django.utils.choices import flatten_choices
from . import analyses as a, tests_meta_f as fixtures
from .forms_analyses import AnalyseForm,aplatir


class CompositeurTests(TestCase):
    setUpTestData=classmethod(fixtures.ConsolidationStatistiques.setUpTestData.__func__)

    def definition(self,**kw):
        return {**a.defaut(),'debut':'2026-01-01','fin':'2026-01-05','reference':'2026-01-04',**kw}

    def form(self,**kw):return AnalyseForm(aplatir(self.definition(**kw)),acteur=self.u)

    def test_repas_choix_compatibles_et_regles_locales(self):
        f=self.form();choix=dict(flatten_choices(f.fields['mesure1_mesure'].choices))
        self.assertIn('quantite',choix);self.assertNotIn('nuits_distinctes',choix)
        self.assertNotIn('adultes_declares',choix)
        self.assertTrue(f['mesure1_portion'].is_hidden)
        self.assertTrue(f['mesure1_mouvement'].is_hidden)
        self.assertTrue(f['lignes'].is_hidden)
        self.assertTrue(f['classes1'].is_hidden)
        self.assertNotIn('phase',dict(flatten_choices(f.fields['axes1'].choices)))
        self.assertIn('age',dict(flatten_choices(f.fields['axes1'].choices)))
        self.assertTrue(f.is_valid(),f.errors)

    def test_valeur_incompatible_conservee_avec_erreur_locale(self):
        f=self.form(mesures=[dict(source='repas',mesure='nuits_distinctes',portion='integrale')])
        self.assertIn('nuits_distinctes',dict(flatten_choices(f.fields['mesure1_mesure'].choices)))
        self.assertFalse(f['mesure1_portion'].is_hidden)
        self.assertFalse(f.is_valid());self.assertIn('mesure1_mesure',f.errors)
        self.assertEqual(f['mesure1_portion'].value(),'integrale')

    def test_detail_et_classes_reprises_sans_perte(self):
        d=self.definition(affichage='detail',lignes='personnes',colonnes=['famille.situation_familiale'],axes=['age'],classes=['Mineurs | 0 | 18'])
        f=AnalyseForm(aplatir(d),acteur=self.u)
        self.assertFalse(f['lignes'].is_hidden);self.assertFalse(f['classes1'].is_hidden)
        self.assertTrue(f.is_valid(),f.errors)
        nouveau=f.definition()
        self.assertEqual(nouveau['classes'],d['classes']);self.assertEqual(nouveau['colonnes'],d['colonnes'])
        self.assertEqual(a.calculer(self.u,d)['mesures'][0]['totaux'],a.calculer(self.u,nouveau)['mesures'][0]['totaux'])

    def test_ajout_ouvre_seulement_le_bloc_ajoute_et_resume_lisible(self):
        self.client.force_login(self.u)
        r=self.client.get(reverse('dossiers:analyse'),{'definition':a.encoder(self.definition()),'ajouter':'mesure'})
        self.assertEqual(r.status_code,200)
        parties=r.context['parties'];self.assertEqual([p['nom'] for p in parties if p['ouvert']],['compter'])
        blocs=parties[2]['blocs'];self.assertFalse(blocs[0]['ouvert']);self.assertTrue(blocs[1]['ouvert'])
        self.assertIn('Somme',blocs[1]['titre']);self.assertNotContains(r,'<summary>Mesure 1</summary>')

    def test_erreur_ouvre_la_mesure_et_conserve_les_autres_choix(self):
        self.client.force_login(self.u)
        d=self.definition(mesures=[dict(source='repas',mesure='nuits_distinctes')])
        r=self.client.get(reverse('dossiers:analyse'),{'definition':a.encoder(d)})
        self.assertEqual(r.status_code,200)
        self.assertEqual([p['nom'] for p in r.context['parties'] if p['ouvert']],['compter'])
        self.assertTrue(r.context['parties'][2]['blocs'][0]['ouvert'])
        self.assertContains(r,'Choix conservé — à vérifier')

    def test_regles_finance_et_axes_communs(self):
        f=self.form(mesures=[dict(source='couts',mesure='quantite')])
        self.assertIn('phase',dict(flatten_choices(f.fields['axes1'].choices)))
        autorisation=self.form(mesures=[dict(source='accords_repas',mesure='objets')])
        self.assertNotIn('quantite',dict(flatten_choices(autorisation.fields['mesure1_mesure'].choices)))
        f=self.form(mesures=[dict(source='repas',mesure='quantite'),dict(source='couts',mesure='quantite')])
        self.assertNotIn('phase',dict(flatten_choices(f.fields['axes1'].choices)))
        self.assertIn('age',dict(flatten_choices(f.fields['axes1'].choices)))

    def test_regle_case_decochee_reste_masquee_apres_soumission(self):
        p=aplatir(self.definition());p['mesure1_lignes_vides']='False'
        f=AnalyseForm(p,acteur=self.u)
        self.assertTrue(f['mesure1_lignes_vides'].is_hidden)
        self.assertTrue(f.is_valid(),f.errors)
        self.assertFalse(f.definition()['mesures'][0]['lignes_vides'])

    def test_resume_filtre_texte_et_calcul_inchanges(self):
        self.client.force_login(self.u)
        d=self.definition(mesures=[dict(source='sejours',mesure='quantite',filtres=[dict(champ='age',operation='gte',valeur='18')])])
        attendu=a.calculer(self.u,d)['mesures'][0]['totaux']
        # Deux personnes majeures à la référence × quatre nuits ; l'âge inconnu est exclu.
        self.assertEqual(sum(attendu.values()),8)
        r=self.client.get(reverse('dossiers:analyse'),{'definition':a.encoder(d)})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.context['resultat']['mesures'][0]['totaux'],attendu)
        self.assertIn('18',r.context['parties'][2]['blocs'][0]['titre'])

    def test_comptes_invalides_restent_bornes(self):
        p=aplatir(self.definition());p.update(nombre_mesure='1000000000',nombre_axes='1000000000')
        f=AnalyseForm(p,acteur=self.u)
        self.assertEqual(len(f.parties['mesure']),12)
        self.assertEqual(len([k for k in f.fields if k.startswith('axes')]),7)
        self.assertFalse(f.is_valid())
