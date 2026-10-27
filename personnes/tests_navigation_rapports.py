import re
from datetime import date
from decimal import Decimal
from html import unescape
from urllib.parse import urlsplit,parse_qs
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from . import tests_meta_f,models as m,financements,exploration as e
from .exploration_releve import relever,retour_verifie,signer_retour


class NavigationRapportsTests(TestCase):
    setUpTestData=classmethod(tests_meta_f.ConsolidationStatistiques.setUpTestData.__func__)
    config=tests_meta_f.ConsolidationStatistiques.config
    def setUp(self):self.client.force_login(self.u)
    def lien(self,r,motif):
        for href in re.findall(r'href="([^"]+)"',r.content.decode()):
            href=unescape(href)
            if motif in href:return href
        self.fail('Lien absent : '+motif)
    def retour(self,r):
        texte=r.content.decode();m=re.search(r'href="([^"]+)">← Revenir aux résultats du rapport</a>',texte)
        self.assertIsNotNone(m);return unescape(m.group(1))
    def test_sejour_exact_et_pas_seulement_la_prise(self):
        rows,ts,xs=e.calculer(self.u,self.config(mesure='quantite'))
        _,faits=relever(self.config(mesure='quantite'),xs,self.u)
        self.assertEqual(urlsplit(faits[0]['url']).path,reverse('suivi:accord_hebergement',args=[self.accord.pk]))
        self.assertEqual(urlsplit(faits[0]['url']).fragment,'sejour-'+str(self.sejour.pk))
        r=self.client.get(faits[0]['url']);self.assertEqual(r.status_code,200)
        self.assertContains(r,'id="sejour-'+str(self.sejour.pk)+'"')
        analyse=self.client.get(self.retour(r));self.assertEqual(analyse.context['totaux'],{'personne-nuit de séjour (absences non déduites)':Decimal(12)})
    def test_financement_version_composante_et_retour_edition(self):
        l=dict(phase='autorise',date=date(2026,1,2),libelle='Coût repérable',unite='nuit',categorie='',quantite=Decimal(3),prix=Decimal('2.10'),tarif=None,justification='Fictif')
        financements.enregistrer(self.u,self.accord,financements.jeton(self.accord),'Fictif','definition',[l],[],emetteur=None,mentions='',debut=date(2026,1,1),fin=date(2026,1,5),devise='EUR',prestataire=None,prescripteur=None,facturation=None,signataire=None,reference='REF',source='Fictif')
        params=dict(debut='2026-01-01',fin='2026-02-01',mode='couts',phase='autorise',reference='REF')
        r=self.client.get(reverse('dossiers:rapport_composer',args=['financements']),params)
        self.assertEqual(r.context['totaux'],{'EUR':Decimal('6.30')})
        url=self.lien(r,'#cout-');self.assertIn('version=1',url);fiche=self.client.get(url);self.assertEqual(fiche.status_code,200)
        self.assertContains(fiche,'id="'+urlsplit(url).fragment+'"');self.assertContains(fiche,'Navigation principale')
        retour=self.retour(fiche);self.assertEqual(urlsplit(retour).path,reverse('dossiers:rapport_composer',args=['financements']))
        self.assertEqual(parse_qs(urlsplit(retour).query)['reference'],['REF'])
        self.assertEqual(self.client.get(retour).context['totaux'],{'EUR':Decimal('6.30')})
        prestation=self.client.get(fiche.context['retour']);self.assertContains(prestation,'Revenir aux résultats du rapport')
    def test_rapport_familial_vers_fiche_vers_dossier_et_retour(self):
        r=self.client.get(reverse('dossiers:rapport_composer',args=['familles']),{'date':'2026-01-15'})
        url=self.lien(r,'retour_exploration=')
        fiche=self.client.get(url);self.assertEqual(fiche.status_code,200)
        retour=self.retour(fiche);self.assertIn('date=2026-01-15',retour)
        dossier=self.client.get(fiche.context['retour']);self.assertEqual(dossier.status_code,200)
        self.assertContains(dossier,'Revenir aux résultats du rapport');self.assertContains(dossier,'Prises en charge')
    def test_jeton_prive_source_fermee_et_navigation_sans_acces_implicite(self):
        p=dict(_source_rapport='financements',debut='2026-01-01',fin='2026-02-01',phase='autorise')
        token=signer_retour(self.u,p);self.assertIn('financements',retour_verifie(self.u,token))
        autre=get_user_model().objects.create_user('autre-retour-prive')
        self.assertIsNone(retour_verifie(autre,token))
        self.assertIsNone(retour_verifie(self.u,signer_retour(self.u,{'_source_rapport':'https://example.invalid/'})))
        self.client.force_login(autre);self.assertEqual(self.client.get(retour_verifie(self.u,token)).status_code,403)
    def test_liens_natifs_charges_en_lot_et_projections_sans_requetes(self):
        for _ in range(12):
            s=m.Sejour.objects.create(accord=self.accord,debut=date(2026,1,1),fin=date(2026,1,5),cree_par=self.u);s.beneficiaires.set([self.adulte])
        _,_,xs=e.calculer(self.u,self.config())
        with self.assertNumQueries(1):relever(self.config(),xs,self.u)
        with self.assertNumQueries(0):relever(self.config(),xs,self.u,liens=False)
