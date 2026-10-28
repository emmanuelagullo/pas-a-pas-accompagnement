"""Recette réelle Chromium : portée, brouillon, publication et attribution partagée."""
from datetime import timedelta
from unittest import skipIf
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.utils import timezone
from acteurs import qualification_navigateur as ancien,services as a
from acteurs.models import DossierService,LienCompteProfessionnel,Habilitation
from acteurs.contexte import perimetre
from . import models as m,transmissions,hebergement

@skipIf(ancien.sync_playwright is None,'Playwright absent : aucune observation navigateur.')
class CahierNavigateur(StaticLiveServerTestCase):
    navigateur=ancien.ParcoursActeurs.navigateur
    def setUp(self):
        ancien.ParcoursActeurs.setUp(self)
        self.ds=DossierService.objects.get(menage__libelle='Alex Martin')
        self.prise=m.Accompagnement.objects.get(menage=self.ds.menage)
        self.collegue=get_user_model().objects.create_user('collegue-liaisons',password='Recette-acteurs-fictive-2026!')
        LienCompteProfessionnel.objects.create(compte=self.collegue,professionnel=m.Intervenant.objects.get(libelle='Joël Bernard'))
        a.habiliter(self.social,self.collegue,self.service,'social',timezone.localdate())
        with perimetre(self.social,self.service):
            self.h=hebergement.accorder(self.social,self.prise,list(self.prise.beneficiaires.all()),timezone.localdate(),timezone.localdate()+timedelta(days=30))
            transmissions.noter(self.social,'Message commun du dossier',menage=self.ds.menage)
            transmissions.noter(self.social,'Message de la prise',accompagnement=self.prise)
            transmissions.noter(self.social,'Message de l’hébergement',accord_hebergement=self.h)
            transmissions.transmettre(self.social,'Message du service')
    def ouvrir(self,page,nature='menage',pk=None,prise=None):
        url=reverse('dossiers:prise',args=[nature,pk or self.ds.menage_id,prise]) if prise else reverse('dossiers:detail',args=[nature,pk or self.ds.menage_id])
        page.goto(self.live_server_url+url)
        page.get_by_text('Liaisons',exact=True).click()
        root=page.locator('#liaisons .liaisons-contenu')
        ancien.expect(root.locator('.liaisons-fil')).to_be_visible()
        return root
    def test_niveaux_brouillon_riche_publication_et_remontee(self):
        page=self.navigateur(self.social);root=self.ouvrir(page,prise=self.prise.pk)
        ancien.expect(root.locator('.liaisons-fil')).to_contain_text('Message de l’hébergement')
        ancien.expect(root.locator('.liaisons-fil')).not_to_contain_text('Message commun du dossier')
        root.locator('input[type=checkbox][name=lia_sous]').uncheck()
        ancien.expect(root.locator('.liaisons-fil')).not_to_contain_text('Message de l’hébergement')
        root.get_by_text('Écrire un message',exact=True).click()
        editeur=root.locator('.ProseMirror');editeur.fill('Brouillon conservé')
        editeur.press('ControlOrMeta+a');editeur.press('ControlOrMeta+b');editeur.press('ArrowRight')
        root.get_by_label('Équipe',exact=True).uncheck()
        ancien.expect(root).not_to_have_attribute('aria-busy','true')
        ancien.expect(root.locator('.ProseMirror')).to_contain_text('Brouillon conservé')
        root.get_by_role('button',name='Publier le message',exact=True).click()
        ancien.expect(root.locator('.liaisons-fil')).to_contain_text('Brouillon conservé')
        root.get_by_role('navigation',name='Cahiers des niveaux supérieurs').get_by_role('link').filter(has_text='Dossier').click()
        root=page.locator('#liaisons .liaisons-contenu')
        ancien.expect(page.locator('#liaisons')).to_have_attribute('open','')
        ancien.expect(root.locator('.liaisons-fil')).to_contain_text('Message commun du dossier')
        root.get_by_role('navigation',name='Cahiers des niveaux supérieurs').get_by_role('link').filter(has_text='service').click()
        ancien.expect(page.locator('.liaisons-fil')).to_contain_text('Message du service')
    def test_attribution_message_auteur_et_notification_ouvrent_le_cahier(self):
        page=self.navigateur(self.social)
        page.goto(self.live_server_url+reverse('dossiers:detail',args=['menage',self.ds.menage_id]))
        page.get_by_text('Équipe de suivi',exact=True).click();page.get_by_role('link',name='Ajouter un intervenant',exact=True).click()
        ancien.expect(page.locator('body')).to_contain_text('Ce n’est pas un message privé.')
        page.locator('[name=professionnel]').select_option(label='Joël Bernard')
        page.locator('[name=message]').fill('Remplacement pendant mon absence.')
        page.get_by_role('button',name='Enregistrer',exact=True).click()
        autre=self.navigateur(self.collegue)
        autre.get_by_text('Compte : collegue-liaisons',exact=True).click();autre.get_by_role('link',name='À suivre',exact=False).click()
        ancien.expect(autre.locator('body')).to_contain_text('Nadia Martin')
        ancien.expect(autre.locator('blockquote')).to_contain_text('Remplacement pendant mon absence.')
        autre.get_by_role('link',name='Alex Martin',exact=False).click()
        root=autre.locator('#liaisons .liaisons-contenu')
        ancien.expect(root.locator('.liaisons-fil')).to_contain_text('Remplacement pendant mon absence.')
        ancien.expect(root.locator('.liaisons-fil')).to_contain_text('par Nadia Martin')
        l=autre.get_by_text('Liaisons',exact=True).bounding_box();e=autre.get_by_text('Équipe de suivi',exact=True).bounding_box()
        self.assertLess(l['x']+l['width'],e['x'])
        autre.set_viewport_size({'width':390,'height':844})
        self.assertTrue(autre.evaluate('document.documentElement.scrollWidth<=innerWidth'))
    def test_fin_habilitation_nettoie_le_fragment_sans_perdre_son_brouillon(self):
        page=self.navigateur(self.social);root=self.ouvrir(page)
        root.get_by_text('Écrire un message',exact=True).click();root.locator('.ProseMirror').fill('Brouillon personnel non envoyé')
        ancien.base(lambda:Habilitation.objects.filter(compte=self.social).update(revoque_le=timezone.now()))
        root.get_by_label('Équipe',exact=True).uncheck()
        ancien.expect(root).to_contain_text('Ce cahier n’est plus accessible')
        ancien.expect(root.locator('.liaisons-fil')).to_have_count(0)
        ancien.expect(root.locator('textarea')).to_have_value('Brouillon personnel non envoyé')
