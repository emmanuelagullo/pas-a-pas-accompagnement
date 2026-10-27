from datetime import date
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
import re
from html import unescape
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from . import tests_meta_f,models as m,modeles_personnels as s
from .periodes_rapports import bornes_periode,suggerer

class ConsolidationRapportsTests(TestCase):
    setUpTestData=classmethod(tests_meta_f.ConsolidationStatistiques.setUpTestData.__func__)
    def setUp(self):self.client.force_login(self.u)
    def definition(self):
        r=self.client.get(reverse('statistiques'),dict(rapport='repas',debut='2026-01-01',fin='2026-02-01'))
        url=unescape(re.search(r'href="([^"]+)">Conserver ces réglages',r.content.decode())[1])
        return parse_qs(urlsplit(url).query)['definition'][0]
    def test_personnalisation_et_modele_sont_distincts_anciens_restent_lisibles(self):
        token=self.definition()
        r=self.client.post(reverse('dossiers:rapport_conserver'),dict(definition=token,nom='Midi habituel',nature='personnalisation',periode='',action='creer'))
        self.assertEqual(r.status_code,302,r.content[:500]);x=m.ModeleRapport.objects.get(nom='Midi habituel')
        self.assertEqual(x.nature,'personnalisation');self.assertEqual(x.source_catalogue,'statistiques:repas')
        self.assertEqual(self.client.get(r.url).status_code,200)
        r=self.client.post(reverse('dossiers:rapport_conserver'),dict(definition=token,nom='Modèle décrit',nature='modele',description='Quantités réellement distribuées.',periode='',action='creer'))
        self.assertEqual(r.status_code,302);self.assertEqual(m.ModeleRapport.objects.get(nom='Modèle décrit').description,'Quantités réellement distribuées.')
    def test_definition_privee_aucune_ecriture_get(self):
        token=self.definition();self.assertEqual(self.client.get(reverse('dossiers:rapport_conserver'),{'definition':token}).status_code,200)
        self.assertEqual(m.ModeleRapport.objects.count(),0)
        from django.contrib.auth import get_user_model
        autre=get_user_model().objects.create_user('autre-consolidation');self.client.force_login(autre)
        self.assertEqual(self.client.post(reverse('dossiers:rapport_conserver'),dict(definition=token,nom='Interdit',nature='modele',action='creer')).status_code,409)
    def test_regles_civiles_annee_bissextile_et_suggestion(self):
        j=date(2024,3,1)
        self.assertEqual(bornes_periode('hier',j),(date(2024,2,29),j))
        self.assertEqual(bornes_periode('mois_precedent',j),(date(2024,2,1),j))
        self.assertEqual(bornes_periode('semaine_civile',j),(date(2024,2,26),date(2024,3,4)))
        self.assertEqual(bornes_periode('jours_relatifs',j,decalage_debut=0,decalage_fin=2),(j,date(2024,3,3)))
        self.assertEqual(suggerer(dict(debut='2024-02-29',fin='2024-03-01'),j),'hier')
        self.assertEqual(suggerer(dict(debut='2022-02-03',fin='2022-02-19'),j),'')
    def test_enregistrement_relatif_recalcule_a_ouverture(self):
        token=self.definition()
        with patch('django.utils.timezone.localdate',return_value=date(2026,2,3)):
            r=self.client.post(reverse('dossiers:rapport_conserver'),dict(definition=token,nom='Hier',nature='personnalisation',periode='hier',action='creer'))
            self.assertEqual(r.status_code,302,r.content[:300])
        with patch('django.utils.timezone.localdate',return_value=date(2026,3,2)):
            r=self.client.get(r.url);self.assertEqual(str(r.context['formulaire'].cleaned_data['debut']),'2026-03-01')

    def test_exports_communs_csv_identique_et_pdf_reel(self):
        token=self.definition()
        params=dict(definition=token,format='csv')
        r=self.client.post(reverse('dossiers:rapport_exporter'),params)
        original=self.client.get(reverse('statistiques'),dict(rapport='repas',debut='2026-01-01',fin='2026-02-01',format='csv'))
        self.assertEqual(r.status_code,200,r.content[:200]);self.assertEqual(r.content,original.content)
        r=self.client.post(reverse('dossiers:rapport_exporter'),{**params,'resume':'Résumé de janvier\nSeconde ligne.'})
        self.assertTrue(r.content.startswith(b'# R'));self.assertIn(b'quantite_distribuee',r.content)
        r=self.client.post(reverse('dossiers:rapport_exporter'),dict(definition=token,format='pdf',resume='Bilan fictif de janvier'))
        self.assertEqual(r.status_code,200,r.content[:300]);self.assertTrue(r.content.startswith(b'%PDF-'))
        self.assertIn('no-store',r['Cache-Control'])

    def test_nouvelles_mesures_reconcilient_sans_confondre_unites(self):
        from . import exploration as e
        x=m.Sejour.objects.create(accord=self.accord,debut=date(2026,1,2),fin=date(2026,1,4),cree_par=self.u);x.beneficiaires.set([self.adulte])
        m.Absence.objects.create(sejour=self.sejour,debut=date(2026,1,2),fin=date(2026,1,3))
        def calcul(code):
            return e.calculer(self.u,tests_meta_f.ConsolidationStatistiques.config(self,mesure=code))
        self.assertEqual(calcul('quantite')[1],{'personne-nuit de séjour (absences non déduites)':14})
        self.assertEqual(calcul('nuits_distinctes')[1],{'nuits distinctes par personne':12})
        self.assertEqual(calcul('nuits_hors_absences')[1],{'nuits distinctes par personne':10})
        self.assertEqual(calcul('participations')[1],{'participations':4})
        self.assertEqual(calcul('durees_total')[1],{'jours':6})
        self.assertEqual(calcul('durees_moyenne')[1],{'jours':3})
        r=self.client.get(reverse('dossiers:explorer'),tests_meta_f.ConsolidationStatistiques.config(self,mesure='nuits_hors_absences'))
        preuve=self.client.get(r.context['liens_totaux'][0]['url'])
        self.assertEqual(preuve.status_code,200)
        self.assertEqual(sum(x['valeur'] for x in preuve.context['page_obj']),10)

    def test_modeles_et_personnalisations_lies_sans_modification_silencieuse(self):
        from django.core import signing
        params={k:str(v) for k,v in tests_meta_f.ConsolidationStatistiques.config(self,mesure='personnes').items()}
        params.update(schema=1,exploration=True)
        token=signing.dumps(dict(acteur=str(self.u.pk),source='exploration',parametres=params,cible=None,attendu=None),salt='reglages-rapport-v1')
        r=self.client.post(reverse('dossiers:rapport_conserver'),dict(definition=token,nom='Ma consultation',nom_modele='Mon calcul',nature='ensemble',description='Personnes distinctes.',periode='',action='creer'))
        self.assertEqual(r.status_code,302,r.content[:200])
        root=m.ModeleRapport.objects.get(nom='Mon calcul');perso=m.ModeleRapport.objects.get(nom='Ma consultation')
        self.assertEqual(perso.modele_source,root);self.assertEqual(perso.nature,'personnalisation')
        avant=perso.parametres.copy();s.changer(self.u,root,s.jeton(self.u,root),'Calcul renommé',description='Description corrigée')
        perso.refresh_from_db();self.assertEqual(perso.parametres,avant)
        gestion=self.client.get(reverse('dossiers:rapports_gerer'));self.assertContains(gestion,'Le modèle d’origine a évolué')
        s.supprimer(self.u,root,s.jeton(self.u,root));perso.refresh_from_db()
        self.assertIsNone(perso.modele_source);self.assertEqual(perso.parametres,avant)

    def test_tous_les_rapports_natifs_exportables_sans_notes_identiques(self):
        from .catalogue_rapports import SOURCES
        for source in SOURCES:
            with self.subTest(source=source):
                r=self.client.get(reverse('dossiers:rapport_composer',args=[source]))
                url=unescape(re.search(r'href="([^"]+)">Conserver ces réglages',r.content.decode())[1])
                token=parse_qs(urlsplit(url).query)['definition'][0]
                out=self.client.post(reverse('dossiers:rapport_exporter'),dict(definition=token,format='csv'))
                self.assertEqual(out.status_code,200,out.content[:200]);self.assertIn('text/csv',out['Content-Type'])

    def test_borne_zero_et_erreur_bornes_sans_erreur_serveur(self):
        from .periodes_rapports import resoudre
        p=resoudre(dict(periode='jours_relatifs',decalage_debut=0,decalage_fin=1),date(2026,2,1))
        self.assertEqual(p['debut'],'2026-02-01')
        r=self.client.get(reverse('statistiques'),dict(rapport='repas',periode='jours_relatifs',decalage_debut='invalide',decalage_fin=1))
        self.assertEqual(r.status_code,200);self.assertTrue(r.context['formulaire'].errors)

    def test_nouvelle_personnalisation_depuis_ancienne_version_explicitement_conservee(self):
        params={k:str(v) for k,v in tests_meta_f.ConsolidationStatistiques.config(self,mesure='personnes').items()};params.update(schema=1,exploration=True)
        root=m.ModeleRapport.objects.create(auteur=self.u,nom='Source',parametres=params)
        r=self.client.get(reverse('dossiers:explorer'),{'modele':root.pk})
        url=unescape(re.search(r'href="([^"]+)">Conserver ces réglages',r.content.decode())[1]);token=parse_qs(urlsplit(url).query)['definition'][0]
        ancien=s.etat(root);nouveau={**params,'mesure':'objets'}
        s.changer(self.u,root,s.jeton(self.u,root),'Source',nouveau)
        r=self.client.post(reverse('dossiers:rapport_conserver'),dict(definition=token,nom='Version précédente',nature='personnalisation',periode='',action='creer'))
        self.assertEqual(r.status_code,302,r.content[:200]);perso=m.ModeleRapport.objects.get(nom='Version précédente')
        self.assertEqual(perso.parametres['mesure'],'personnes');self.assertEqual(perso.empreinte_source,ancien)

    def test_situation_a_date_unique_reste_une_date(self):
        r=self.client.get(reverse('dossiers:rapport_composer',args=['coordonnees']),{'date':'2026-01-02'})
        url=unescape(re.search(r'href="([^"]+)">Conserver ces réglages',r.content.decode())[1]);token=parse_qs(urlsplit(url).query)['definition'][0]
        f=self.client.get(url).context['form']
        self.assertNotIn('mois',dict(f.fields['periode'].choices))
        r=self.client.post(reverse('dossiers:rapport_conserver'),dict(definition=token,nom='Coordonnées à jour',nature='personnalisation',periode='date_relative',decalage_debut=0,action='creer'))
        self.assertEqual(r.status_code,302,r.content[:300])
        with patch('django.utils.timezone.localdate',return_value=date(2026,5,4)):
            r=self.client.get(r.url);self.assertEqual(str(r.context['form'].cleaned_data['date']),'2026-05-04')
