"""Une présentation NAV, plusieurs capacités et sources métier réelles."""
from datetime import date
from urllib.parse import urlencode
from django.test import TestCase
from django.urls import reverse
from . import tests_collectifs as base, models as m, collectifs as c
from .tests_hebergement import Donnees

class PrestationsUnifieesTests(Donnees,TestCase):
    setUp=base.CollectifsTests.setUp
    declarer=base.CollectifsTests.declarer
    restaurer=base.CollectifsTests.restaurer

    def url(self,cle='',operation='',**kw):
        return reverse('dossiers:prise',args=['menage',self.m.pk,self.a.pk])+'?'+urlencode({'prestation':cle,'operation':operation,'q':'Fictif','page':'3',**kw})

    def test_memes_entetes_lignes_selection_et_frises(self):
        p=self.restaurer()
        self.client.force_login(self.u)
        session=self.client.session;session['frises_visibles']=True;session.save()
        page=self.client.get(self.url())
        self.assertEqual(page.status_code,200)
        self.assertTemplateUsed(page,'dossiers/_prestation_entete.html')
        self.assertTemplateUsed(page,'dossiers/_prestation_ligne.html')
        self.assertContains(page,'data-prestation-carte="sejour:'+str(self.s.pk)+'"')
        self.assertContains(page,'data-prestation-carte="commun:'+str(p.pk)+'"')
        self.assertContains(page,'data-frise-slot="bande-prestationcollective-'+str(p.pk)+'"')
        self.assertIn(('prestationcollective',str(p.pk)),page.context['frises_objets'])
        self.assertNotContains(page,'prestations-communes')
        self.assertNotContains(page,'col_action=creation')

    def test_consultation_correction_et_prolongation_sont_des_panneaux_nav(self):
        p=self.restaurer();self.client.force_login(self.u)
        page=self.client.get(self.url('commun:'+str(p.pk)))
        self.assertEqual(page.status_code,200)
        self.assertContains(page,'data-prestation-panneau',count=1)
        self.assertContains(page,'>Modifier</a>')
        self.assertContains(page,'%2Fcorrection%2F%3Fpk%3D'+str(p.pk))
        self.assertContains(page,'id="condition-composition"',count=1)
        self.assertContains(page,'>Refermer</a>',count=1)
        self.assertContains(page,'<h1>Prise en charge',count=1)
        operation=reverse('dossiers:collectif_action',args=['prise',self.a.pk,'prolongation'])+'?'+urlencode({'pk':p.pk})
        page=self.client.get(self.url('commun:'+str(p.pk),operation))
        self.assertContains(page,'data-prestation-form')
        response=self.client.post(self.url('commun:'+str(p.pk),operation),{'date':'2026-01-15','attendu':c.jeton(p),'motif':''})
        self.assertEqual(response.status_code,302)
        self.assertIn('prestation=commun',response.url)
        page=self.client.get(response.url)
        self.assertContains(page,'15/01/2026')
        self.assertEqual(p.versions.count(),2)

    def test_cible_et_operation_etrangeres_refusees(self):
        p=self.restaurer();self.client.force_login(self.u)
        operation=reverse('dossiers:collectif_action',args=['prise',self.a.pk,'correction'])+'?'+urlencode({'pk':self.s.pk})
        self.assertEqual(self.client.get(self.url('commun:'+str(p.pk),operation)).status_code,404)
        self.assertEqual(self.client.get(self.url('commun:'+str(self.s.pk))).status_code,404)

    def test_creation_et_apercu_sans_second_dispatcher(self):
        self.client.force_login(self.u)
        from .tests_reprise_collective import RepriseCollectiveTests
        self.a=m.Accompagnement.objects.select_related('menage').get(pk=self.a.pk)
        d=RepriseCollectiveTests.donnees(self)
        response=self.client.post(self.url('nouveau:commun_restauration',apercu='1'),d)
        self.assertEqual(response.status_code,200)
        self.assertIn('80.00 EUR',response.json()['message'])
        self.assertFalse(m.PrestationCollective.objects.exists())
        response=self.client.post(self.url('nouveau:commun_restauration'),d)
        self.assertEqual(response.status_code,302)
        self.assertContains(self.client.get(response.url),'data-prestation-panneau',count=1)
        self.assertEqual(m.PrestationCollective.objects.count(),1)

    def test_desactivation_ne_cache_pas_histoire_et_garde_interface(self):
        p=self.restaurer();self.service.profil_collectif={};self.service.save()
        self.client.force_login(self.u)
        page=self.client.get(self.url('commun:'+str(p.pk)))
        self.assertEqual(page.status_code,200)
        self.assertContains(page,'data-prestation-panneau',count=1)
        self.assertTemplateUsed(page,'dossiers/_prestation_ligne.html')
