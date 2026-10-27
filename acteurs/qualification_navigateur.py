"""Parcours réels Chromium, sur base fictive et contrôle actif."""
import os
from concurrent.futures import ThreadPoolExecutor
from unittest import skipIf
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db import connections
from django.urls import reverse
from .essai import preparer
from .models import DossierService,Service
try:
    from playwright.sync_api import sync_playwright,expect
except ImportError:sync_playwright=None


def base(faire):
    def executer():
        try:return faire()
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=1) as pool:return pool.submit(executer).result()


@skipIf(sync_playwright is None,'Playwright absent : aucune observation navigateur.')
class ParcoursActeurs(StaticLiveServerTestCase):
    def setUp(self):
        self.social=get_user_model().objects.create_user('social-fictif',password='Recette-acteurs-fictive-2026!')
        self.accueil=get_user_model().objects.create_user('accueil-fictif',password='Recette-acteurs-fictive-2026!')
        self.coord=get_user_model().objects.create_user('coordination-fictive',password='Recette-acteurs-fictive-2026!')
        self.service=preparer(self.social,self.accueil,self.coord)
        self.attente=DossierService.objects.get(menage__libelle='Samira Benali')
        self.protege=DossierService.objects.get(menage__libelle='Louise Durand')

    def navigateur(self,compte):
        if not hasattr(self,'chromium'):
            pw=sync_playwright().start();self.addCleanup(pw.stop)
            options={'executable_path':os.environ['PWA_CHROMIUM']} if os.environ.get('PWA_CHROMIUM') else {}
            self.chromium=pw.chromium.launch(**options);self.addCleanup(self.chromium.close)
        contexte=self.chromium.new_context(viewport={'width':1280,'height':960})
        page=contexte.new_page()
        page.goto(self.live_server_url+'/connexion/')
        page.locator('[name=username]').fill(compte.username)
        page.locator('[name=password]').fill('Recette-acteurs-fictive-2026!')
        page.get_by_role('button',name='Se connecter',exact=True).click()
        page.wait_for_load_state('load')
        return page

    def test_dossiers_reprise_relais_historique_et_refus_direct(self):
        page=self.navigateur(self.social)
        expect(page.get_by_role('heading',name='Quel dossier souhaitez-vous ouvrir ?',exact=True)).to_be_visible()
        expect(page.locator('body')).not_to_contain_text('Dossier réservé à un autre service')
        page.get_by_role('link',name='Samira Benali',exact=False).click()
        page.get_by_role('button',name='Commencer le suivi',exact=True).click()
        expect(page.locator('[aria-label="Responsabilités"]')).to_contain_text('Nadia Martin')
        if os.environ.get('ACTEURS_CAPTURE_DIR'):
            from pathlib import Path
            sortie=Path(os.environ['ACTEURS_CAPTURE_DIR']);sortie.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(sortie/'dossier-acteurs.png'),full_page=True)
        page.get_by_role('link',name='Passer le relais',exact=True).click()
        page.get_by_label('À qui ?',exact=True).select_option(label='Joël Bernard')
        page.get_by_role('button',name='Confirmer le relais',exact=True).click()
        expect(page.locator('[aria-label="Responsabilités"]')).to_contain_text('Joël Bernard')
        page.get_by_text('Interventions précédentes',exact=True).click()
        expect(page.locator('[aria-label="Responsabilités"]')).to_contain_text('Nadia Martin')
        cible=reverse('dossiers:detail',args=['menage',self.protege.menage_id])
        self.assertEqual(page.goto(self.live_server_url+cible).status,404)
        base(lambda:Service.objects.filter(pk=self.service.pk).update(politique='individuel'))
        cible=reverse('dossiers:detail',args=['menage',self.attente.menage_id])
        self.assertEqual(page.goto(self.live_server_url+cible).status,404)

    def test_accueil_creation_en_attente_et_coordination_sans_dossiers(self):
        page=self.navigateur(self.accueil)
        page.goto(self.live_server_url+reverse('dossiers:creer',args=['personne']))
        page.locator('[name=designation]').fill('Nouvelle personne fictive — accueil')
        page.get_by_role('button',name='Créer et ouvrir le dossier',exact=True).click()
        expect(page.locator('[aria-label="Responsabilités"]')).to_contain_text('En attente de suivi social')
        expect(page.get_by_role('button',name='Commencer le suivi',exact=True)).to_have_count(0)
        # Nouvelle session pour la coordination : statistiques regroupées seulement.
        page=self.navigateur(self.coord)
        expect(page.get_by_role('heading',name='Statistiques d’activité',exact=True)).to_be_visible()
        cible=reverse('dossiers:detail',args=['menage',self.attente.menage_id])
        self.assertEqual(page.goto(self.live_server_url+cible).status,403)
