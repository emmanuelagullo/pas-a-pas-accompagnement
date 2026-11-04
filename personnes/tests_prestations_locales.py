"""NAV7 : même Form3, opérations bornées et droits métier inchangés."""
from datetime import date
from urllib.parse import urlencode
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Permission
from . import models as m, tests_form2 as precedent

class PrestationsLocalesTests(TestCase):
    setUpBase = precedent.Form2Tests.setUp
    preparer = precedent.Form2Tests.preparer

    def setUp(self):
        self.setUpBase()
        self.u.is_superuser=True; self.u.save()
        self.r=m.AccordRepas.objects.create(accompagnement=self.a, debut=date(2026,1,1), service='diner', cree_par=self.u)
        self.r.beneficiaires.add(self.p)
        self.aides=[]
        for code,_ in m.TypeAide.NATURES:
            t=m.TypeAide.objects.create(nature=code,libelle='Aide fictive '+code,unite='unité',cree_par=self.u)
            a=m.AccordAide.objects.create(accompagnement=self.a,type_aide=t,nature=code,libelle=t.libelle,unite=t.unite,debut=date(2026,1,1),source='Fictif',cree_par=self.u)
            a.beneficiaires.add(self.p); self.aides.append(a)

    def url(self,cle,operation=''):
        return self.detail+'?'+urlencode({'prestation':cle,'operation':operation,'q':'Fictif','page':'3','presentation_sociale':'synthese'})

    def test_toutes_les_familles_restent_dans_form3(self):
        for cle in ['sejour:'+str(self.s.pk),'repas:'+str(self.r.pk)]+['aide_'+a.nature+':'+str(a.pk) for a in self.aides]:
            page=self.client.get(self.url(cle))
            self.assertEqual(page.status_code,200)
            self.assertContains(page,'aria-label="Fil d’Ariane"',count=1)
            self.assertContains(page,'<h1>Prise en charge',count=1)
            self.assertContains(page,'data-prestation-panneau',count=1)
            self.assertContains(page,'>Refermer</a>',count=1)
            self.assertContains(page,'id="hebergement"')
            self.assertContains(page,'id="repas"')
            self.assertContains(page,'data-prestation-form',count=0)

    def test_validation_et_enregistrement_depuis_form3(self):
        operation=reverse('suivi:distribuer_repas',args=[self.r.pk])
        url=self.url('repas:'+str(self.r.pk),operation)
        form=self.client.get(url)
        self.assertContains(form,'data-prestation-form')
        data={'beneficiaire':str(self.p.pk),'date':'2025-12-31','quantite':'2'}
        refus=self.client.post(url,data)
        self.assertEqual(refus.status_code,200)
        self.assertContains(refus,'errorlist')
        self.assertContains(refus,'aria-label="Fil d’Ariane"')
        self.assertEqual(m.RepasDistribue.objects.count(),0)
        data['date']='2026-01-05'
        page=self.client.post(url,data,follow=True)
        self.assertEqual(page.status_code,200)
        self.assertContains(page,'data-prestation-panneau',count=1)
        self.assertEqual(m.RepasDistribue.objects.get().quantite,2)

    def test_scope_et_url_non_autorisee(self):
        cle='repas:'+str(self.r.pk)
        for operation in [reverse('suivi:sortir',args=[self.s.pk]),'https://example.org/action','/statistiques/']:
            self.assertEqual(self.client.get(self.url(cle,operation)).status_code,404)
        self.assertEqual(self.client.get(self.url('repas:'+str(self.s.pk))).status_code,404)

    def test_droits_operation_non_contournes(self):
        self.u.is_superuser=False;self.u.save()
        self.u.user_permissions.remove(Permission.objects.get(content_type__app_label='personnes',codename='add_repasdistribue'))
        url=self.url('repas:'+str(self.r.pk),reverse('suivi:distribuer_repas',args=[self.r.pk]))
        self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.post(url,{'beneficiaire':str(self.p.pk),'date':'2026-01-05','quantite':'1'}).status_code,403)
        self.assertEqual(m.RepasDistribue.objects.count(),0)

    def test_operations_secondaires_restant_locales(self):
        from html.parser import HTMLParser
        class Liens(HTMLParser):
            def __init__(self):super().__init__();self.dans=False;self.externes=[]
            def handle_starttag(self,tag,attrs):
                a=dict(attrs)
                if tag=='a' and 'data-prestation-externe' in a:self.externes.append(a.get('href'))
        cas=[('sejour:'+str(self.s.pk),route,args) for route,args in [
            ('suivi:affecter',[self.s.pk]),('suivi:absence',[self.s.pk]),('suivi:sortir',[self.s.pk]),
            ('suivi:corriger_saisie',['sejour',self.s.pk]),('suivi:prolonger_accord',['hebergement',self.accord.pk]),
            ('suivi:notes',['sejour',self.s.pk]),('dossiers:financement',['hebergement',self.accord.pk])]]
        cas += [('repas:'+str(self.r.pk),route,args) for route,args in [
            ('suivi:distribuer_repas',[self.r.pk]),('suivi:notes',['accord_repas',self.r.pk]),
            ('dossiers:corriger_service_repas',[self.r.pk]),('dossiers:financement',['repas',self.r.pk])]]
        for a in self.aides:
            cas += [('aide_'+a.nature+':'+str(a.pk),route,[a.pk]) for route in ('dossiers:aide_remettre','dossiers:aide_corriger','dossiers:aide_annuler')]
        for cle,route,args in cas:
            with self.subTest(cle=cle,route=route):
                page=self.client.get(self.url(cle,reverse(route,args=args)))
                self.assertEqual(page.status_code,200)
                self.assertContains(page,'<h1>Prise en charge',count=1)
                self.assertContains(page,'data-prestation-panneau',count=1)
                self.assertNotContains(page,'<h1>Enregistrer')
                self.assertNotContains(page,'&lt;!DOCTYPE')
                liens=Liens();liens.feed(page.content.decode())
                self.assertTrue(all('/tarifs/' in u or '/rapports/' in u or '/liaison/' in u or ('/dossiers/' in u and 'lia_ouvrir=1' in u) for u in liens.externes),liens.externes)

    def test_creation_prevue_et_arrivee_dans_form3(self):
        from . import hebergement, admission
        hebergement.sortir(self.u,self.s,date(2026,1,20))
        data=precedent.Form2Tests.donnees(self)
        data.pop('arrivee_effectuee',None)
        url=self.url('nouveau:hebergement')
        page=self.client.post(url,data,follow=True)
        self.assertEqual(page.status_code,200)
        self.assertContains(page,'Accord d’hébergement du')
        prevu=m.AccordHebergement.objects.exclude(pk=self.accord.pk).get()
        url=self.url('hebergement:'+str(prevu.pk),reverse('suivi:arrivee_prevue',args=[prevu.pk]))
        from . import accords
        page=self.client.post(url,{'attendu':accords.jeton(prevu),'debut':'2026-04-01','beneficiaires':[str(self.p.pk)]},follow=True)
        self.assertEqual(page.status_code,200)
        self.assertContains(page,'Séjour du 01/04/2026')
        self.assertContains(page,'data-prestation-panneau',count=1)
        self.assertEqual(prevu.sejours.count(),1)

    def test_erreur_stockage_ne_rejoue_pas_et_conserve_saisie(self):
        from unittest.mock import patch
        from django.db import OperationalError
        url=self.url('sejour:'+str(self.s.pk),reverse('suivi:affecter',args=[self.s.pk]))
        with patch('personnes.hebergement.ajouter_periode',side_effect=OperationalError('occupé')) as action:
            page=self.client.post(url,{'debut':'2026-01-05','lieu':str(self.lieu.pk),'fin':''})
        self.assertEqual(page.status_code,409)
        self.assertContains(page,'2026-01-05',status_code=409)
        self.assertContains(page,'data-prestation-form',status_code=409)
        self.assertEqual(action.call_count,1)
        self.assertEqual(m.Affectation.objects.count(),0)

    def test_dossier_individuel_ne_propose_pas_aide_autre_personne(self):
        autre=m.Personne.objects.create(designation='Autre personne fictive',cree_par=self.u)
        self.a.beneficiaires.add(autre)
        accord=self.aides[0];accord.beneficiaires.set([autre])
        url=reverse('dossiers:prise',args=['personne',self.p.pk,self.a.pk])
        self.assertNotContains(self.client.get(url),str(accord.pk))
        self.assertEqual(self.client.get(url+'?'+urlencode({'prestation':'aide_transport:'+str(accord.pk)})).status_code,404)

    def test_notes_publication_depuis_prestation(self):
        from html.parser import HTMLParser
        class Formulaire(HTMLParser):
            def __init__(self):super().__init__();self.jetons={}
            def handle_starttag(self,tag,attrs):
                a=dict(attrs)
                if tag=='input' and a.get('name')=='lia_envoi':self.jetons[a['name']]=a.get('value','')
        cle='repas:'+str(self.r.pk)
        operation=reverse('suivi:cahier')+'?'+urlencode({'lia_cible':'repas','lia_id':self.r.pk})
        url=self.url(cle,operation)
        page=self.client.get(url)
        self.assertContains(page,'Publier le message')
        f=Formulaire();f.feed(page.content.decode())
        self.assertIn('lia_envoi',f.jetons)
        resultat=self.client.post(url,{**f.jetons,'contenu':'Message fictif NAV7','date_fait':'2026-01-05'},follow=True)
        self.assertEqual(resultat.status_code,200)
        self.assertContains(resultat,'Message fictif NAV7')
        self.assertContains(resultat,'data-prestation-panneau',count=1)
        self.assertEqual(m.NotePartagee.objects.filter(accord_repas=self.r).count(),1)
        autre=operation.replace(str(self.r.pk),str(self.s.pk))
        self.assertEqual(self.client.post(self.url(cle,autre),f.jetons).status_code,404)

    def test_operations_sous_prefixe_serveur_et_pwa(self):
        from django.urls import get_script_prefix, set_script_prefix
        prefixe=get_script_prefix()
        try:
            set_script_prefix('/chrs/app/')
            for cle in ['sejour:'+str(self.s.pk),'repas:'+str(self.r.pk)]+['aide_'+a.nature+':'+str(a.pk) for a in self.aides]:
                page=self.client.get(self.url(cle),SCRIPT_NAME='/chrs/app/')
                self.assertEqual(page.status_code,200)
                self.assertContains(page,'data-prestation-panneau',count=1)
                self.assertContains(page,'/chrs/app/dossiers/')
        finally:set_script_prefix(prefixe)
