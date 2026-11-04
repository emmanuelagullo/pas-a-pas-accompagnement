"""NAV9 : regrouper la lecture, jamais les faits ni les quantités."""
from datetime import date
from django.test import TestCase
from django.urls import reverse
from . import models as m, tests_prestations_locales as base

class HebergementsGroupesTests(TestCase):
    setUpBase=base.PrestationsLocalesTests.setUpBase
    preparer=base.PrestationsLocalesTests.preparer
    url=base.PrestationsLocalesTests.url
    def setUp(self):
        base.PrestationsLocalesTests.setUp(self)
        self.autres=[]
        for nom in ['Samira fictive','Enfant fictif']:
            p=m.Personne.objects.create(designation=nom,cree_par=self.u)
            self.a.beneficiaires.add(p);self.accord.beneficiaires.add(p)
            s=m.Sejour.objects.create(accord=self.accord,debut=self.s.debut,cree_par=self.u)
            s.beneficiaires.add(p);self.autres.append((p,s))

    def test_une_carte_commune_et_trois_sejours_conserves(self):
        page=self.client.get(self.detail)
        self.assertContains(page,'data-hebergement-groupe=',count=1)
        self.assertContains(page,'Détails individuels — 3 séjours')
        self.assertContains(page,'Hébergement · 3 personnes')
        self.assertEqual(m.Sejour.objects.count(),3)
        self.assertEqual(m.AccordHebergement.objects.count(),1)
        self.assertNotContains(page,'class="hebergement-individuels" open')
        self.assertContains(page,'Agir sur les personnes…')

    def test_dossier_personne_ne_regroupe_pas_les_autres(self):
        url=reverse('dossiers:prise',args=['personne',self.p.pk,self.a.pk])
        page=self.client.get(url)
        self.assertNotContains(page,'data-hebergement-groupe=')
        hebergement=page.content.decode().split('id="hebergement"',1)[1].split('</section>',1)[0]
        self.assertNotIn('Samira fictive',hebergement)
        self.assertNotIn('Enfant fictif',hebergement)

    def test_divergences_explicitement_presentees(self):
        s=self.autres[0][1];s.debut=date(2026,1,4);s.fin=date(2026,1,5);s.save()
        page=self.client.get(self.detail)
        self.assertContains(page,'Arrivées à des dates différentes')
        self.assertContains(page,'Fins de séjour différentes')
        self.assertContains(page,'Lieux différents ou non renseignés')

    def test_liens_individuel_et_accord_dans_form3(self):
        for cle in ['hebergement:'+str(self.accord.pk),'sejour:'+str(self.autres[0][1].pk)]:
            page=self.client.get(self.url(cle))
            self.assertEqual(page.status_code,200)
            self.assertContains(page,'data-prestation-panneau',count=1)
            self.assertContains(page,'data-hebergement-groupe=',count=1)
