"""COL2–4 : vrais gestes Chromium, avec et sans JavaScript."""
from pathlib import Path
import os
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from .tests_hebergement import Donnees
from . import tests_collectifs as tests
from django.conf import settings

class CollectifsNavigateur(Donnees,StaticLiveServerTestCase):
    declarer=tests.CollectifsTests.declarer
    restaurer=tests.CollectifsTests.restaurer
    def setUp(self):tests.CollectifsTests.setUp(self)

    def parcourir(self,javascript,largeur):
        from playwright.sync_api import sync_playwright,expect
        self.client.force_login(self.u)
        session=self.client.cookies[settings.SESSION_COOKIE_NAME].value
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                ctx=browser.new_context(java_script_enabled=javascript,viewport={'width':largeur,'height':900})
                ctx.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':session,'url':self.live_server_url}])
                page=ctx.new_page()
                url=self.live_server_url+reverse('dossiers:prise',args=['menage',self.m.pk,self.a.pk])
                erreurs=[];documents=[];reponses=[];echecs=[]
                page.on('response',lambda r:reponses.append((r.status,r.url)))
                page.on('response',lambda r:echecs.append(r) if r.status>=400 else None)
                page.on('pageerror',lambda e:erreurs.append(str(e)))
                page.goto(url)
                page.on('request',lambda r:documents.append(r.url) if r.resource_type=='document' else None)
                page.get_by_role('link',name='Nouvelle période de repas',exact=True).click()
                form=page.locator('#collectif-form form');expect(form).to_be_visible()
                form.locator('[name=debut]').fill('2026-01-10')
                form.locator('[name=fin_prevue]').fill('2026-01-13')
                form.locator('[name=premier]').select_option('diner')
                form.locator('[name=dernier]').select_option('dejeuner')
                form.locator('[name=prix_adulte]').fill('8')
                form.locator('[name=prix_enfant]').fill('5')
                if javascript:
                    form.locator('[name=diner]').uncheck()
                    expect(form.locator('[name=premier]')).to_be_disabled()
                    expect(form.locator('[name=dernier]')).to_have_value('dejeuner')
                    form.locator('[name=diner]').check()
                    form.locator('[name=premier]').select_option('diner')
                    form.locator('[name=dernier]').select_option('dejeuner')
                form.locator('details').filter(has=page.locator('summary',has_text='Choisir un groupe')).locator('summary').click()
                form.locator('[name=restreindre]').check()
                form.locator('[name=selection_enfant]').fill('1')
                if javascript:expect(form.locator('[data-collectif-calcul]')).to_contain_text('30.00 EUR')
                else:
                    form.get_by_role('button',name='Calculer',exact=True).click()
                    expect(form.locator('[data-collectif-calcul]')).to_contain_text('30.00 EUR')
                if os.environ.get('COL_CAPTURES'):
                    out=Path(os.environ['COL_CAPTURES']);out.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(out/(f'COL-restauration-{largeur}-'+('js' if javascript else 'html')+'.png')),full_page=True)
                form.get_by_role('button',name='Enregistrer',exact=True).click()
                expect(page.locator('#collectif-form')).to_have_count(0)
                expect(page.locator('#repas')).to_contain_text('Déjeuner')
                expect(page.locator('#repas')).to_contain_text('30,00 EUR')
                carte=page.locator('#repas [data-prestation-carte]').first
                # The compact list has one full-width title, no row of action buttons.
                expect(carte.locator(':scope > nav')).to_have_count(0)
                resume=carte.locator(':scope > a.prestation-consulter')
                self.assertGreater(resume.bounding_box()['width'],carte.bounding_box()['width']*.8)
                if os.environ.get('COL_CAPTURES'):
                    page.screenshot(path=str(out/(f'COL-liste-{largeur}-'+('js' if javascript else 'html')+'.png')),full_page=True)
                resume.click()
                form=page.locator('#collectif-form form');expect(form).to_be_visible()
                self.assertGreater(form.bounding_box()['width'],carte.bounding_box()['width']*.65)
                if javascript:
                    form.locator('[name=fin]').fill('2025-01-01')
                    form.get_by_role('button',name='Enregistrer',exact=True).click()
                    expect(form.locator('.errorlist').first).to_contain_text('fin')
                    expect(page.locator('#etat-dossier')).to_contain_text('Vérifiez')
                    form.locator('[name=fin]').fill('')
                form.locator('[name=fin_prevue]').fill('2026-01-15')
                if os.environ.get('COL_CAPTURES'):
                    page.screenshot(path=str(out/(f'COL-edition-{largeur}-'+('js' if javascript else 'html')+'.png')),full_page=True)
                form.get_by_role('button',name='Enregistrer',exact=True).click()
                expect(page.locator('#collectif-form')).to_have_count(0)
                expect(page.locator('#repas [data-prestation-carte]').first).to_contain_text('15/01/2026')
                self.assertEqual(erreurs,[])
                if javascript:self.assertEqual(documents,[])
                page.get_by_role('link',name='Bilan / Imprimer',exact=True).click()
                expect(page.get_by_role('heading',name='Bilan des prestations')).to_be_visible()
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),largeur+1)
                if os.environ.get('COL_CAPTURES'):
                    out=Path(os.environ['COL_CAPTURES']);out.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(out/(f'COL-bilan-{largeur}-'+('js' if javascript else 'html')+'.png')),full_page=True)
            except Exception:
                print('URL navigateur :',page.url)
                print('Statut NAV :',page.locator('#etat-dossier').inner_text())
                print('Champs invalides :',page.locator('#collectif-form form').evaluate('(f)=>[...f.elements].filter(e=>e.validity && !e.validity.valid).map(e=>[e.name,e.validationMessage])') if page.locator('#collectif-form form').count() else [])
                print('Réponses :',reponses[-3:])
                for r in echecs:
                    try:print('Erreur HTTP :',r.status,r.text()[:3500])
                    except Exception:pass
                print('Erreurs navigateur :',erreurs)
                print('Formulaire :',page.locator('#collectif-form').inner_text() if page.locator('#collectif-form').count() else 'aucun')
                raise
            finally:browser.close()

    def test_1366_avec_javascript(self):self.parcourir(True,1366)
    def test_390_sans_javascript(self):self.parcourir(False,390)
    def test_390_avec_javascript(self):self.parcourir(True,390)
    def test_1366_sans_javascript(self):self.parcourir(False,1366)


    def parcourir_hebergement_et_repas(self,largeur):
        from datetime import date
        from . import collectifs as c, models as m
        from playwright.sync_api import sync_playwright,expect
        self.restaurer()
        self.a=m.Accompagnement.objects.select_related('menage').get(pk=self.a.pk)
        c.creer(self.u,self.a,'hebergement',self.comp,c.jeton(self.a),[],debut=date(2026,1,10),arrivee=date(2026,1,10),fin_prevue=date(2026,1,13))
        self.client.force_login(self.u)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                ctx=browser.new_context(viewport={'width':largeur,'height':900})
                ctx.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':self.client.cookies[settings.SESSION_COOKIE_NAME].value,'url':self.live_server_url}])
                page=ctx.new_page()
                page.goto(self.live_server_url+reverse('dossiers:prise',args=['menage',self.m.pk,self.a.pk]))
                cartes=page.locator('.prestations-communes [data-prestation-carte]')
                expect(cartes).to_have_count(2)
                expect(cartes.locator(':scope > nav')).to_have_count(0)
                for carte in cartes.all():
                    self.assertGreater(carte.locator(':scope > a').bounding_box()['width'],carte.bounding_box()['width']*.8)
                if os.environ.get('COL_CAPTURES'):
                    out=Path(os.environ['COL_CAPTURES']);out.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(out/f'COL-deux-listes-{largeur}.png'),full_page=True)
                page.locator('#hebergement .prestations-communes .prestation-consulter').click()
                f=page.locator('#collectif-form form');expect(f).to_be_visible()
                f.locator('[name=fin]').fill('2026-01-12')
                if os.environ.get('COL_CAPTURES'):page.screenshot(path=str(out/f'COL-depart-{largeur}.png'),full_page=True)
                f.get_by_role('button',name='Enregistrer',exact=True).click()
                expect(page.locator('#collectif-form')).to_have_count(0)
                expect(page.locator('#hebergement .prestations-communes')).to_contain_text('12/01/2026')
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),largeur+1)
            finally:browser.close()

    def test_listes_et_depart_390(self):self.parcourir_hebergement_et_repas(390)
    def test_listes_et_depart_1366(self):self.parcourir_hebergement_et_repas(1366)


class ParametrageCollectifNavigateur(Donnees,StaticLiveServerTestCase):
    declarer=tests.CollectifsTests.declarer
    restaurer=tests.CollectifsTests.restaurer
    def setUp(self):
        tests.CollectifsTests.setUp(self)
        from django.contrib.auth.models import Permission
        self.u.user_permissions.add(Permission.objects.get(content_type__app_label='acteurs',codename='gerer_organisation'))
        self.u=type(self.u).objects.get(pk=self.u.pk)

    def parcourir(self,largeur):
        from playwright.sync_api import sync_playwright,expect
        import re
        self.client.force_login(self.u)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                ctx=browser.new_context(viewport={'width':largeur,'height':900})
                ctx.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':self.client.cookies[settings.SESSION_COOKIE_NAME].value,'url':self.live_server_url}])
                page=ctx.new_page();erreurs=[];documents=[]
                page.on('pageerror',lambda e:erreurs.append(str(e)))
                page.goto(self.live_server_url+reverse('acteurs:service',args=[self.service.pk]))
                page.on('request',lambda r:documents.append(r.url) if r.resource_type=='document' else None)
                page.get_by_role('link',name='Prestataires',exact=True).click()
                page.get_by_role('link',name='Nouvelle offre',exact=True).click()
                f=page.locator('#parametrage form')
                f.locator('[name=libelle]').fill('Table d’essai')
                f.locator('[name=nouveau_lieu]').fill('Restaurant fictif')
                f.locator('[name=nature]').select_option('restauration')
                f.get_by_role('button',name='Enregistrer',exact=True).click()
                page.get_by_role('link',name='Renseigner un tarif',exact=True).click()
                expect(page.get_by_role('heading',name='Table d’essai',exact=True)).to_be_visible()
                f=page.locator('#parametrage-editeur form')
                f.locator('[name=categorie]').select_option('adulte')
                f.locator('[name=debut]').fill('2026-01-01')
                f.locator('[name=prix]').fill('8');f.locator('[name=prix_diner]').fill('10')
                f.get_by_role('button',name='Enregistrer',exact=True).click()
                expect(page.locator('#parametrage-editeur')).to_have_count(0)
                page.get_by_role('link',name='Services',exact=True).click()
                page.get_by_role('link',name=re.compile('^Les Amandiers')).click()
                page.get_by_role('link',name='Modifier les informations et prestations',exact=True).click()
                expect(page.get_by_role('heading',name='Les Amandiers',exact=True)).to_be_visible()
                editeur=page.locator('#parametrage-editeur')
                expect(page.locator('[data-parametrage-bloc] #parametrage-editeur')).to_have_count(1)
                self.assertEqual(editeur.locator('..').get_attribute('id'),'service-'+str(self.service.pk)+'-collecte')
                membres=page.locator('#service-'+str(self.service.pk)+'-membres').element_handle()
                f=editeur.locator('form')
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),largeur+1)
                expect(page.get_by_role('link',name='Modifier les informations et prestations',exact=True)).to_be_hidden()
                f.locator('[name=catalogue]').check()
                f.locator('[name=prestations][value=hebergement]').uncheck()
                f.get_by_label('Table d’essai',exact=True).check()
                if os.environ.get('COL_CAPTURES'):
                    out=Path(os.environ['COL_CAPTURES']);out.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(out/f'COL-parametrage-{largeur}.png'),full_page=True)
                f.get_by_role('button',name='Enregistrer',exact=True).click()
                expect(page.locator('#parametrage-editeur')).to_have_count(0)
                self.assertTrue(membres.evaluate('(e)=>e.isConnected'))
                # The access editor opens in its own section, never at page bottom.
                page.get_by_role('link',name='Modifier l’accès aux dossiers',exact=True).click()
                expect(page.locator('#service-'+str(self.service.pk)+'-acces #parametrage-editeur')).to_be_visible()
                page.locator('#parametrage-editeur').get_by_role('link',name='Annuler',exact=True).click()
                expect(page.locator('#parametrage-editeur')).to_have_count(0)
                self.assertEqual(erreurs,[]);self.assertEqual(documents,[])
            finally:browser.close()
        self.service.refresh_from_db();self.assertTrue(self.service.catalogue_prestations)
        self.assertEqual(self.service.profil_collectif['prestations'],['restauration'])

    def test_390(self):self.parcourir(390)
    def test_1366(self):self.parcourir(1366)
