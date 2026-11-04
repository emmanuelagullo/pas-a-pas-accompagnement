"""NAV10 : présence de contenu, jamais complétude ni nouveau droit."""
from datetime import date
from decimal import Decimal
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from . import models as m
from .reperes_sociaux import bilan, compter
from . import tests_condition_sociale as ancien


def groupe(*faits, noms=()):
    return {'fiches':[{'fait':f,'resume':[{'nom':n} for n in noms]} for f in faits]}


class CompteursTests(SimpleTestCase):
    def test_zero_absence_inconnu_et_non_renseigne(self):
        connus=[groupe(m.RessourcePersonnelle(montant=Decimal('0')),noms=('montant',)),
                groupe(m.RessourcePersonnelle(etat='aucun'))]
        inconnu=groupe(m.RessourcePersonnelle(etat='inconnu'))
        vide=groupe(m.SituationPersonnelle(valeur='inconnu'),noms=('valeur',))
        self.assertEqual(compter(connus+[inconnu,vide,{'fiches':[]}]),
                         {'total':5,'informations':2,'non_connu':1})

    def test_collection_comptee_une_fois_et_mixte_non_doublee(self):
        faits=[m.RessourcePersonnelle(etat='aucun') for _ in range(80)]
        faits.append(m.RessourcePersonnelle(etat='inconnu'))
        self.assertEqual(compter([groupe(*faits)]),{'total':1,'informations':1,'non_connu':0})

    def test_denominations_personnelles_et_projet_separees(self):
        personnes=[{'groupes':[groupe(m.Personne(designation='Fictif'),noms=('designation',))]},
                   {'groupes':[{'fiches':[]}]}]
        result=bilan(personnes,[{'items':[1,2]},{'items':[]}])
        self.assertEqual(result,{'personnes':2,'total':2,'informations':1,'non_connu':0,
                                 'projet_total':2,'projet_informations':1})
        self.assertEqual(personnes[1]['reperes']['informations'],0)
        self.assertEqual(bilan([],[])['total'],0)


class ReperesHTTPTests(TestCase):
    setUpTestData=classmethod(ancien.ConditionSocialeTests.setUpTestData.__func__)
    setUp=ancien.ConditionSocialeTests.setUp

    def test_dates_heritage_et_presentations_invariantes(self):
        avant=self.client.get(self.url,{'vue_sociale':'date','date_sociale':'2026-08-01'})
        entree=self.client.get(self.url)
        synthese=self.client.get(self.url,{'presentation_sociale':'synthese'})
        self.assertEqual(entree.context['condition_reperes'],synthese.context['condition_reperes'])
        self.assertEqual(entree.context['condition_reperes']['informations'],
                         avant.context['condition_reperes']['informations']+1)
        self.assertContains(entree,'Situation au 10/10/2026')
        self.assertContains(entree,'data-condition-reperes-personne')
        self.assertContains(entree,'Projet et parcours :')
        with self.assertNumQueries(0):
            bilan(entree.context['condition_personnes'],entree.context['condition_projets'])

    def test_absence_et_non_connu_dans_les_vraies_collections(self):
        initial=self.client.get(self.url).context['condition_reperes']
        m.RessourcePersonnelle.objects.create(personne=self.p,debut=date(2026,1,1),etat='aucun',auteur=self.u)
        m.DettePersonnelle.objects.create(personne=self.p,debut=date(2026,1,1),etat='inconnu',auteur=self.u)
        page=self.client.get(self.url)
        self.assertEqual(page.context['condition_reperes']['informations'],initial['informations']+1)
        self.assertEqual(page.context['condition_reperes']['non_connu'],initial['non_connu']+1)
        self.assertContains(page,'non connu déclaré')

    def test_menage_somme_des_rubriques_par_personne(self):
        autre=m.Personne.objects.create(designation='Autre fictif',cree_par=self.u)
        self.a.beneficiaires.add(autre)
        page=self.client.get(self.url)
        total=page.context['condition_reperes']
        self.assertEqual(total['personnes'],2)
        self.assertEqual(total['total'],sum(p['reperes']['total'] for p in page.context['condition_personnes']))
        self.assertContains(page,'2 personnes consultables')
        individuel=self.client.get(reverse('dossiers:prise',args=['personne',self.p.pk,self.a.pk]))
        # La prise garde ici son ensemble de bénéficiaires (contrat existant).
        self.assertEqual(individuel.context['condition_reperes']['total'],total['total'])

    def test_rubrique_non_autorisee_exclue_des_deux_compteurs(self):
        from django.contrib.auth.models import Permission
        initial=self.client.get(self.url).context['condition_reperes']
        self.u.is_superuser=False;self.u.save()
        self.u.user_permissions.set(Permission.objects.exclude(codename='view_ressourcepersonnelle'))
        self.client.force_login(self.u)
        page=self.client.get(self.url)
        self.assertEqual(page.status_code,200)
        self.assertEqual(page.context['condition_reperes']['total'],initial['total']-1)
