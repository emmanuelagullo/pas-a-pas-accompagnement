"""Recette Chromium à deux professionnels sur des dossiers inventés."""
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.utils import timezone
from unittest import skipIf
from . import qualification_navigateur as ancien,services as s
from .models import Etablissement,Service,LienCompteProfessionnel,DossierService
from personnes import models as m

@skipIf(ancien.sync_playwright is None,'Playwright absent : aucune observation navigateur.')
class ReperageNavigateur(StaticLiveServerTestCase):
    navigateur=ancien.ParcoursActeurs.navigateur
    def setUp(self):
        ancien.ParcoursActeurs.setUp(self)
        self.collegue=get_user_model().objects.create_user('collegue-recette',password='Recette-acteurs-fictive-2026!')
        prof=m.Intervenant.objects.get(libelle='Joël Bernard')
        LienCompteProfessionnel.objects.create(compte=self.collegue,professionnel=prof)
        s.habiliter(self.social,self.collegue,self.service,'social',timezone.localdate())
        Service.objects.filter(pk=self.service.pk).update(politique='individuel')
        Etablissement.objects.filter(pk=self.service.etablissement_id).update(reperage_identites=True)
    def test_demande_acceptation_signal_et_fin_de_suivi(self):
        page=self.navigateur(self.social)
        page.goto(self.live_server_url+'/?q=Thomas&filtre=mes')
        page.get_by_role('link',name='Voir les correspondances dans Tous',exact=True).click()
        page.get_by_role('link',name='Thomas Leroy',exact=False).click()
        ancien.expect(page.get_by_text('Identité repérée · Vous n’avez pas accès au contenu de ce suivi.',exact=True)).to_be_visible()
        page.get_by_role('link',name='Demander à rejoindre le suivi',exact=True).click()
        page.get_by_role('button',name='Enregistrer',exact=True).click()
        ancien.expect(page.get_by_text('Votre demande de rattachement est en attente.',exact=True)).to_be_visible()
        ds=ancien.base(lambda:DossierService.objects.get(menage__libelle='Thomas Leroy'))
        cible=self.live_server_url+reverse('dossiers:detail',args=['menage',ds.menage_id])
        autre=self.navigateur(self.collegue);autre.goto(cible)
        autre.get_by_text('Équipe de suivi',exact=True).click()
        autre.get_by_role('link',name='Examiner la demande',exact=True).click()
        autre.get_by_role('button',name='Enregistrer',exact=True).click()
        page.goto(cible)
        ancien.expect(page.get_by_text('Vous suivez ce dossier',exact=True)).to_be_visible()
        page.get_by_text('Compte : social-fictif',exact=True).click()
        page.get_by_role('link',name='Notifications',exact=False).click()
        ancien.expect(page.get_by_text('Un suivi vous a été attribué',exact=False)).to_be_visible()
        page.get_by_role('button',name='Marquer comme lu',exact=True).first.click()
        ancien.expect(page.get_by_text('Lu',exact=False).first).to_be_visible()
        page.goto(cible);page.get_by_text('Équipe de suivi',exact=True).click()
        page.locator('[aria-label="Responsabilités"] li').filter(has_text='Nadia Martin').get_by_role('link',name='Terminer l’intervention',exact=True).click()
        page.get_by_role('button',name='Enregistrer',exact=True).click()
        page.goto(cible)
        ancien.expect(page.get_by_text('Identité repérée · Vous n’avez pas accès au contenu de ce suivi.',exact=True)).to_be_visible()
        page.set_viewport_size({'width':390,'height':844})
        self.assertTrue(page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
    def test_prestation_depuis_identite_sans_reprendre_suivi(self):
        page=self.navigateur(self.social)
        page.get_by_role('link',name='Thomas Leroy',exact=False).click()
        page.get_by_role('link',name='Ajouter des repas',exact=True).click()
        page.locator('[name=service]').select_option('dejeuner')
        page.get_by_role('button',name='Accorder les repas',exact=True).click()
        ancien.expect(page.locator('body')).not_to_contain_text('Cette liste de choix')
        # Confirmation réelle en base ; la mission créée porte sur le nouvel accord.
        def verifier():
            from .models import Responsabilite
            rs=Responsabilite.objects.filter(professionnel__libelle='Nadia Martin',dossier__menage__libelle='Thomas Leroy')
            return rs.filter(repas__isnull=False).exists(),rs.filter(prise__isnull=True,hebergement__isnull=True,repas__isnull=True,aide__isnull=True).exists()
        self.assertEqual(ancien.base(verifier),(True,False))
