import re
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from . import tests_meta_f, tests_consolidation_rapports, models as m, modeles_personnels as s
from .presentation_exports import prioritaire,DEFAUTS_STATISTIQUES,DEFAUTS_SOURCES


class PresentationExportsTests(TestCase):
    setUpTestData=classmethod(tests_meta_f.ConsolidationStatistiques.setUpTestData.__func__)
    definition=tests_consolidation_rapports.ConsolidationRapportsTests.definition
    def setUp(self):self.client.force_login(self.u)
    def boutons(self,r,principal):
        self.assertEqual(r.status_code,200)
        boutons=re.findall(r'<button([^>]*)name="format" value="(pdf|csv)"',r.content.decode())
        self.assertEqual([format for attrs,format in boutons],['pdf','csv'])
        self.assertEqual([format for attrs,format in boutons if 'secondaire' not in attrs],[principal])
    def test_defaults_tous_les_modeles_et_boutons_reels(self):
        from .vues_statistiques import RAPPORTS
        from .catalogue_rapports import SOURCES
        self.assertEqual(set(DEFAUTS_STATISTIQUES),set(RAPPORTS))
        self.assertEqual(set(DEFAUTS_SOURCES),set(SOURCES)-{'statistiques'})
        for code,format in DEFAUTS_STATISTIQUES.items():
            self.boutons(self.client.get(reverse('statistiques'),dict(rapport=code,debut='2026-01-01',fin='2026-02-01')),format)
        for source,format in DEFAUTS_SOURCES.items():
            self.boutons(self.client.get(reverse('dossiers:rapport_composer',args=[source])),format)
    def test_conserver_puis_modifier_sans_changer_chiffres_et_sans_ecrasement_perime(self):
        token=self.definition()
        r=self.client.post(reverse('dossiers:rapport_conserver'),dict(definition=token,nom='Repas CSV',nature='modele',periode='',action='creer',export_prioritaire='csv'))
        self.assertEqual(r.status_code,302)
        x=m.ModeleRapport.objects.get(nom='Repas CSV');self.assertEqual(x.parametres['export_prioritaire'],'csv')
        rapport=self.client.get(r.url);self.boutons(rapport,'csv');chiffres=rapport.context['resultats']
        ticket=s.jeton(self.u,x);url=reverse('dossiers:modele_gerer',args=[x.pk])
        r=self.client.post(url,dict(nom=x.nom,attendu=ticket,action='renommer',export_prioritaire='pdf'))
        self.assertEqual(r.status_code,302);self.boutons(self.client.get(r.url),'pdf')
        self.assertEqual(self.client.get(r.url).context['resultats'],chiffres)
        self.assertEqual(self.client.post(url,dict(nom=x.nom,attendu=ticket,action='renommer',export_prioritaire='csv')).status_code,409)
        x.refresh_from_db();self.assertEqual(x.parametres['export_prioritaire'],'pdf')
    def test_echange_composable_duplication_et_valeur_invalide(self):
        from .modeles_echange import valider,exporter,importer
        p={**tests_meta_f.ConsolidationStatistiques.config(self), 'schema':1,'exploration':True,'export_prioritaire':'csv'}
        x=m.ModeleRapport.objects.create(auteur=self.u,nom='CSV composable',parametres=valider(self.u,p))
        copie=s.dupliquer(self.u,x,s.jeton(self.u,x),'Copie')
        self.assertEqual(copie.parametres['export_prioritaire'],'csv')
        self.assertEqual(importer(self.u,exporter(self.u,x)).parametres['export_prioritaire'],'csv')
        self.boutons(self.client.get(reverse('dossiers:explorer'),{'modele':x.pk}),'csv')
        with self.assertRaises(ValidationError):valider(self.u,{**p,'export_prioritaire':'html'})
    def test_ancien_modele_non_reecrit_et_defaut_detail(self):
        self.assertEqual(prioritaire('exploration',{'affichage':'detail'}),'csv')
        self.assertEqual(prioritaire('exploration',{}),'pdf')
        x=m.ModeleRapport.objects.create(auteur=self.u,nom='Ancien',parametres=dict(rapport='repas',debut='2026-01-01',fin='2026-02-01'))
        self.boutons(self.client.get(reverse('statistiques'),{'modele':x.pk}),'pdf')
        x.refresh_from_db();self.assertNotIn('export_prioritaire',x.parametres)
        from .personnalisation_rapports import adapter
        self.assertEqual(adapter(self.u,'statistiques',{**x.parametres,'export_prioritaire':'csv'})['export_prioritaire'],'csv')
    def test_preference_ne_change_pas_export_csv_et_personnalisation_autonome(self):
        from html import unescape
        from urllib.parse import urlsplit,parse_qs
        from .catalogue_rapports import ouvrir
        from .vues_statistiques import parametres_modele
        p=parametres_modele(dict(rapport='repas',debut='2026-01-01',fin='2026-02-01',export_prioritaire='pdf'))
        parent=m.ModeleRapport.objects.create(auteur=self.u,nom='Parent',parametres=p)
        enfant=m.ModeleRapport.objects.create(auteur=self.u,nom='Personnel',nature='personnalisation',modele_source=parent,parametres=p,empreinte_source=s.etat(parent))
        def csv(modele):
            r=self.client.get(ouvrir(modele))
            token=parse_qs(urlsplit(unescape(re.search(r'href="([^"]+)">Conserver ces réglages',r.content.decode())[1])).query)['definition'][0]
            r=self.client.post(reverse('dossiers:rapport_exporter'),dict(definition=token,format='csv'))
            self.assertEqual(r.status_code,200);return r.content
        avant=csv(parent)
        s.changer(self.u,parent,s.jeton(self.u,parent),parent.nom,export_prioritaire='csv')
        self.assertEqual(csv(parent),avant)
        enfant.refresh_from_db();self.assertEqual(enfant.parametres['export_prioritaire'],'pdf')
        self.boutons(self.client.get(ouvrir(enfant)),'pdf')
