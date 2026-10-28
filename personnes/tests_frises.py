from datetime import date, timedelta
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.utils import timezone
from django.test.utils import CaptureQueriesContext
from django.db import connection
from . import frises, models as m, hebergement, repas
from .tests_hebergement import Donnees
from acteurs import tests as tests_acteurs


class EchelleTests(TestCase):
    def test_raccord_direction_et_compression(self):
        fin = date(2026,10,28)
        e = frises.Echelle(date(1980,1,1), fin)
        self.assertEqual(e.position(fin),100)
        self.assertEqual(e.position(e.debut),0)
        self.assertAlmostEqual(e.distance(365),365)
        self.assertAlmostEqual(e.distance(365.001)-365,.001,places=6)
        points = [e.position(fin-timedelta(days=x)) for x in (0,30,365,366,1000,10000)]
        self.assertEqual(points, sorted(points,reverse=True))
        self.assertGreater(e.distance(365)-e.distance(335), e.distance(5000)-e.distance(4970))
        self.assertIsNone(e.intervalle(fin+timedelta(days=1),None))
        self.assertIsNone(e.intervalle(date(1970,1,1), e.debut))

    def test_bornes_exactes_et_annee_bissextile(self):
        from types import SimpleNamespace
        e=frises.Echelle(date(2023,3,1),date(2024,3,1))
        self.assertEqual(e.annee,366)
        p=SimpleNamespace(debut=date(2023,6,1),fin=date(2023,6,3),fin_prevue=None)
        f={'id':'fictif','type':'sejour','lane':0,'debut':date(2023,6,2),'fin':date(2023,6,3),'label':'Séjour','annule':False,'url':'/fictif'}
        b=frises.bande(e,[p],[f])
        marque=next(x for x in b['segments'] if x['type']=='sejour')
        attendu=e.intervalle(f['debut'],f['fin'])
        self.assertEqual(marque['x'],attendu['x'])
        self.assertAlmostEqual(float(marque['w']),float(attendu['w']),places=3)
        self.assertFalse(b['approximative'])


class FrisesTests(Donnees,TestCase):
    def setUp(self):
        self.preparer()
        self.client.force_login(self.u)
        self.url = reverse('dossiers:detail',args=['personne',self.p.pk])

    def activer(self):
        page = self.client.get(self.url)
        self.assertEqual(page.status_code,200)
        retour = self.client.post(reverse('dossiers:frises_preference'),{'actif':'1','retour_frise':page.context['frise_retour']})
        self.assertEqual(retour.status_code,302)

    def test_session_commune_et_vue_sur_place(self):
        self.assertNotContains(self.client.get(self.url), 'class="frise-mini')
        self.activer()
        dossier = self.client.get(self.url)
        self.assertContains(dossier, 'class="frise-mini')
        self.assertNotContains(dossier, '>Chronologie des prises')
        entree = self.client.get(reverse('accueil'))
        self.assertContains(entree, 'class="frise-mini')
        prise = self.client.get(reverse('dossiers:prise',args=['personne',self.p.pk,self.a.pk]))
        self.assertContains(prise, 'class="frise-mini')
        self.assertContains(prise, 'Élargir')
        self.assertContains(prise, '#sejour-'+str(self.s.pk))
        self.assertEqual(self.client.post(reverse('dossiers:frises_preference'), {'retour_frise':prise.context['frise_retour']}).status_code,302)
        self.assertNotContains(self.client.get(self.url), 'class="frise-mini')

    def test_retour_recherche_et_depliage_conserve(self):
        from urllib.parse import urlsplit
        self.activer()
        r=self.client.get(reverse('accueil'),{'mode':'personne','q':'fictive'})
        o=next(x for x in r.context['page_obj'] if x.pk==self.p.pk)
        cible=self.client.get(o.frise['details'][0]['url'])
        retour=cible.context['retour_dossier']
        self.assertEqual(urlsplit(retour).path,reverse('accueil'))
        self.assertEqual(urlsplit(retour).fragment,'frise-personne-'+str(self.p.pk))
        revenu=self.client.get(retour)
        self.assertEqual(revenu.context['frise_ouverte'],'personne-'+str(self.p.pk))
        self.assertContains(revenu,'id="frise-personne-'+str(self.p.pk)+'" open')
        r=self.client.get(self.url)
        b=r.context['frises_objets'][('accompagnement',str(self.a.pk))]
        cible=self.client.get(b['details'][0]['url'])
        revenu=self.client.get(cible.context['retour_dossier'])
        self.assertContains(revenu,'id="frise-accompagnement-'+str(self.a.pk)+'" open')

    def test_preference_signee_et_csrf(self):
        self.assertEqual(self.client.get(reverse('dossiers:frises_preference')).status_code,405)
        self.assertEqual(self.client.post(reverse('dossiers:frises_preference'),{'retour_frise':'https://ailleurs.example'}).status_code,400)
        from django.test import Client
        client=Client(enforce_csrf_checks=True);client.force_login(self.u)
        self.assertEqual(client.post(reverse('dossiers:frises_preference'),{}).status_code,403)

    def test_beneficiaires_partiels_densite_et_futur(self):
        self.u.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes'))
        self.u=type(self.u).objects.get(pk=self.u.pk)
        q=m.Personne.objects.create(designation='PERSONNE PRIVEE',cree_par=self.u)
        self.a.beneficiaires.add(q)
        r=m.AccordRepas.objects.create(accompagnement=self.a,debut=date(2026,1,1),fin=date(2026,3,1),service='diner',cree_par=self.u)
        r.beneficiaires.add(q)
        for _ in range(3):
            x=m.AccordRepas.objects.create(accompagnement=self.a,debut=date(2026,1,1),fin=date(2026,3,1),service='dejeuner',cree_par=self.u)
            x.beneficiaires.add(self.p)
        future=m.AccordRepas.objects.create(accompagnement=self.a,debut=timezone.localdate()+timedelta(days=20),service='diner',cree_par=self.u)
        future.beneficiaires.add(self.p)
        frises.charger(self.u,[self.p],'personne')
        self.assertTrue(self.p.frise['dense'])
        self.assertTrue(self.p.frise['futur'])
        self.assertNotIn(str(r.pk),[f['id'] for f in self.p.frise['details']])
        self.assertLessEqual(len(self.p.frise['segments']), 4*64+1)
        for s in self.p.frise['segments']:
            self.assertLessEqual(float(s['x'])+float(s['w']),100.001)

    def test_lecture_groupee_sur_la_page(self):
        with CaptureQueriesContext(connection) as a:
            frises.charger(self.u,[self.p],'personne')
        autres=[]
        for i in range(12):
            p=m.Personne.objects.create(designation=f'Personne fictive {i}',cree_par=self.u)
            self.a.beneficiaires.add(p);self.s.beneficiaires.add(p);self.accord.beneficiaires.add(p)
            autres.append(p)
        with CaptureQueriesContext(connection) as b:
            frises.charger(self.u,[self.p,*autres],'personne')
        self.assertLessEqual(len(b),len(a)+1)


class FrisesAccesTests(TestCase):
    setUp=tests_acteurs.AccesTests.setUp
    compte=tests_acteurs.AccesTests.compte
    dossier=tests_acteurs.AccesTests.dossier

    def test_requetes_groupees_avec_controle_actif(self):
        from acteurs.contexte import perimetre
        with CaptureQueriesContext(connection) as petit:
            frises.charger(self.ua,[self.ma],'menage')
        objets=[self.ma]
        for i in range(8):
            _,_,menage,_,_=self.dossier(self.sa,self.ua,'Fictif '+str(i))
            objets.append(menage)
        with CaptureQueriesContext(connection) as grand:
            frises.charger(self.ua,objets,'menage')
        self.assertLessEqual(len(grand),len(petit)+2)
        self.assertTrue(all(o.frise for o in objets))

    def test_prestation_limitee_et_revocation(self):
        from acteurs.models import Responsabilite,Habilitation,PorteeObjet
        self.sa.politique='individuel';self.sa.save()
        Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,hebergement=self.h,cree_par=self.admin)
        autre=m.AccordHebergement.objects.create(accompagnement=self.a,debut=date(2000,1,1),cree_par=self.ua)
        autre.beneficiaires.add(self.personne_a)
        PorteeObjet.objects.create(modele=autre._meta.label_lower,identifiant=str(autre.pk),service=self.sa,dossier=self.da,prise=self.a,prestation_modele='accordhebergement',prestation_id=autre.pk)
        with __import__('acteurs.contexte',fromlist=['perimetre']).perimetre(self.ua):
            frises.charger(self.ua,[self.ma],'menage')
        self.assertNotIn(str(autre.pk),[f['id'] for f in self.ma.frise['details']])
        Habilitation.objects.filter(compte=self.ua).update(revoque_le=timezone.now())
        self.client.force_login(self.ua)
        session=self.client.session;session[frises.SESSION]=True;session.save()
        self.assertIn(self.client.get(reverse('dossiers:detail',args=['menage',self.ma.pk])).status_code,(403,404))


class EvolutionCompacteTests(TestCase):
    def test_bornes_connues_et_pas_de_cloture_depuis_une_prevision(self):
        from types import SimpleNamespace
        from .vues_trajectoire import Filtres,libelle_borne
        p=SimpleNamespace(pk='fictif',debut=date(2025,1,1),fin=None,fin_prevue=date(2025,6,1),menage='Fictif')
        f=Filtres({},personnes=[],prises=[p]);self.assertTrue(f.is_valid(),f.errors)
        self.assertEqual(f.cleaned_data['debut'],p.debut)
        self.assertEqual(f.cleaned_data['fin'],timezone.localdate())
        self.assertEqual(f.cleaned_data['presentation_evolution'],'changements')
        self.assertIn('Aujourd’hui',libelle_borne(f,'fin',timezone.localdate()))
        p.fin=date(2025,7,1)
        f=Filtres({},personnes=[],prises=[p]);self.assertTrue(f.is_valid(),f.errors)
        self.assertEqual(f.cleaned_data['fin'],date(2025,6,30))
