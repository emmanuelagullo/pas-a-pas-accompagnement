"""Deux services réels, même composant NAV, sans manipulation de l'interface."""
from datetime import date
from pathlib import Path
import os
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from .tests_hebergement import Donnees
from . import tests_collectifs as fixtures,models as m,collectifs as c,hebergement as h,repas,suivi
from acteurs.models import Service,DossierService,PorteeObjet

class DeuxServicesNAV(Donnees,StaticLiveServerTestCase):
    declarer=fixtures.CollectifsTests.declarer
    restaurer=fixtures.CollectifsTests.restaurer
    def setUp(self):
        fixtures.CollectifsTests.setUp(self)
        self.rg=self.restaurer()
        self.a=m.Accompagnement.objects.select_related('menage').get(pk=self.a.pk)
        self.hg=c.creer(self.u,self.a,'hebergement',self.comp,c.jeton(self.a),[],debut=date(2026,1,10),arrivee=date(2026,1,10),fin_prevue=date(2026,1,31))
        service=Service.objects.create(etablissement=self.service.etablissement,libelle='Accompagnement')
        p=m.Personne.objects.create(designation='Adulte fictif Accompagnement',cree_par=self.u)
        menage=suivi.creer_menage(self.u,'Ménage Accompagnement',[p],date(2026,1,1))
        self.a2=suivi.ouvrir(self.u,menage,[p],date(2026,1,1))
        ds=DossierService.objects.create(service=service,menage=menage,cree_par=self.u)
        for obj in (p,menage,self.a2):PorteeObjet.objects.create(service=service,dossier=ds,modele=obj._meta.label_lower,identifiant=str(obj.pk),prise=self.a2 if obj==self.a2 else None)
        accord=h.accorder(self.u,self.a2,[p],date(2026,1,10),date(2026,1,31))
        self.h2=h.admettre(self.u,accord,[p],date(2026,1,10))
        self.r2=repas.accorder(self.u,self.a2,[p],date(2026,1,10),date(2026,1,31),'diner')

    def parcourir(self,javascript,largeur):
        from playwright.sync_api import sync_playwright,expect
        self.client.force_login(self.u)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                ctx=browser.new_context(java_script_enabled=javascript,viewport={'width':largeur,'height':900})
                ctx.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':self.client.cookies[settings.SESSION_COOKIE_NAME].value,'url':self.live_server_url}])
                page=ctx.new_page();erreurs=[]
                page.on('pageerror',lambda e:erreurs.append(str(e)))
                formes=[]
                for nom,a,cleh,cler in [('Accompagnement',self.a2,'sejour:'+str(self.h2.pk),'repas:'+str(self.r2.pk)),('Amandiers',self.a,'commun:'+str(self.hg.pk),'commun:'+str(self.rg.pk))]:
                    page.goto(self.live_server_url+reverse('dossiers:prise',args=['menage',a.menage_id,a.pk])+'?q=Fictif&page=2')
                    if nom=='Amandiers' and largeur>600:
                        menu=page.locator('#sommaire-dossier')
                        menu.locator('.condition-nav-details').first.locator('summary').first.click()
                        menu.get_by_role('link',name='Voir la composition du ménage',exact=True).click()
                        expect(page.locator('#condition-composition')).to_be_visible()
                        if javascript:
                            self.assertTrue(page.locator('#condition-composition').evaluate('(e)=>e.open && e.closest("[data-condition-volet]").open'))
                    hbox=page.locator('#hebergement');rbox=page.locator('#repas')
                    for boite,label in [(hbox,'Nouveau séjour'),(rbox,'Nouvelle période de repas')]:
                        entete=boite.locator(':scope > .boite-entete')
                        expect(entete.get_by_role('link',name=label,exact=True)).to_be_visible()
                        self.assertEqual(entete.locator('h3').count(),1)
                    ligne=hbox.locator('[data-prestation-carte="'+cleh+'"]')
                    expect(ligne.locator(':scope > label input[type=radio]')).to_be_visible()
                    self.assertGreater(ligne.locator(':scope > a').bounding_box()['width'],ligne.bounding_box()['width']*.65)
                    formes.append(ligne.evaluate('(e)=>[e.className,...[...e.children].map(x=>x.tagName+":"+x.className)]'))
                    frise=page.locator('section[aria-labelledby="titre-prestations"] [data-frise-choix]')
                    if not frise.locator('[name=actif]').is_checked():
                        frise.locator('[name=actif]').check()
                        if not javascript:frise.get_by_role('button',name='Appliquer',exact=True).click()
                    expect(ligne.locator(':scope > a .frise-mini')).to_be_visible()
                    rp=rbox.locator('[data-prestation-carte="'+cler+'"]')
                    expect(rp.locator(':scope > a .frise-mini')).to_be_visible()
                    if os.environ.get('NAV_UNIFIE_CAPTURES'):
                        out=Path(os.environ['NAV_UNIFIE_CAPTURES']);out.mkdir(parents=True,exist_ok=True)
                        page.screenshot(path=str(out/(nom+'-'+str(largeur)+('-js' if javascript else '-html')+'.png')),full_page=True)
                    cadre=hbox.element_handle()
                    rp.locator('input[type=radio]').check()
                    if not javascript:rbox.get_by_role('button',name='Afficher les actions des repas choisis',exact=True).click()
                    # The existing timeline also opens the same NAV panel.
                    commande=rp.locator(':scope > div.frise-slot details.frise-details > summary')
                    titre=rp.locator(':scope > a > strong')
                    self.assertLess(abs(commande.bounding_box()['y']-titre.bounding_box()['y']),12)
                    self.assertGreater(commande.bounding_box()['x'],rp.bounding_box()['x']+rp.bounding_box()['width']*.55)
                    rp.locator(':scope > div.frise-slot details.frise-details > summary').click()
                    detail=rp.locator('.frise-depliee')
                    self.assertGreater(detail.bounding_box()['width'],rp.bounding_box()['width']*.8)
                    if os.environ.get('NAV_UNIFIE_CAPTURES'):
                        page.screenshot(path=str(out/(nom+'-frise-'+str(largeur)+('-js' if javascript else '-html')+'.png')),full_page=True)

                    rp.locator(':scope > div.frise-slot .frise-detail a').first.click()
                    expect(page.locator('[data-prestation-panneau]')).to_have_count(1)
                    expect(page.get_by_role('navigation',name='Fil d’Ariane')).to_be_visible()
                    self.assertIn('q=Fictif',page.url)
                    if javascript:self.assertTrue(cadre.evaluate('(e)=>e.isConnected'))
                    if nom=='Amandiers':
                        panneau=page.locator('[data-prestation-panneau]')
                        rbox.get_by_role('link',name='Modifier',exact=True).click()
                        expect(page.locator('[data-prestation-panneau] form[data-prestation-form]')).to_be_visible()
                        panneau.get_by_role('link',name='Annuler',exact=True).click()
                        expect(rbox.get_by_role('link',name='Modifier',exact=True)).to_be_visible()
                        rbox.get_by_role('link',name='Modifier',exact=True).click()
                        page.locator('[data-prestation-panneau]').get_by_role('button',name='Enregistrer',exact=True).click()
                        expect(page.locator('[data-prestation-panneau] form[data-prestation-form]')).to_have_count(0)
                    page.get_by_role('link',name='Refermer',exact=True).click()
                    expect(page.locator('[data-prestation-panneau]')).to_have_count(0)
                    self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),largeur+1)
                # Identical native line structure; only data and selected state vary.
                normalise=lambda forme:[forme[0].replace(' selectionnee',''),*forme[1:]]
                self.assertEqual(normalise(formes[0]),normalise(formes[1]))
                self.assertEqual(erreurs,[])
            finally:browser.close()

    def test_390_js(self):self.parcourir(True,390)
    def test_1366_js(self):self.parcourir(True,1366)
    def test_390_html(self):self.parcourir(False,390)
    def test_1366_html(self):self.parcourir(False,1366)
