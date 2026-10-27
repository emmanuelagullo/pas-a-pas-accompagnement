from datetime import date
from io import StringIO
from urllib.parse import urlsplit,parse_qs
from django.test import TestCase,Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from . import models as m,tests_meta_f,catalogue_rapports as c,modeles_personnels as s


class GestionRapportsTests(TestCase):
    setUpTestData=classmethod(tests_meta_f.ConsolidationStatistiques.setUpTestData.__func__)
    def setUp(self):self.client.force_login(self.u)
    def composer(self,source,d=None):return self.client.get(reverse('dossiers:rapport_composer',args=[source]),d or {})
    def test_accueil_rapports_en_premier_creation_et_gestion(self):
        r=self.client.get(reverse('statistiques'),follow=True);self.assertEqual(r.status_code,200)
        html=r.content.decode();self.assertLess(html.index('Rapports prêts à utiliser'),html.index('<h2>Mes modèles</h2>'))
        self.assertContains(r,'Gérer mes modèles');self.assertContains(r,'Mouvements')
        r=self.client.get(reverse('dossiers:rapport_nouveau'));self.assertContains(r,'Partir de zéro');self.assertContains(r,'À partir d’une définition composable')
    def test_catalogue_tous_les_sources_ouvrables_et_derivees(self):
        for source in c.SOURCES:
            with self.subTest(source=source):
                r=self.composer(source);self.assertEqual(r.status_code,200,r.content[:200])
                self.assertContains(r,'Enregistrer les paramètres de ce rapport');self.assertContains(r,'Enregistrer mon modèle')
                f=r.context.get('form') or r.context.get('formulaire');self.assertTrue(f.is_valid(),f.errors)
                d=dict(r.context['parametres_composition']);d.update(nom='Essai '+source,action_modele='creer')
                r=self.client.post(reverse('dossiers:rapport_composer',args=[source]),d)
                self.assertEqual(r.status_code,302,r.content[:500])
                modele=m.ModeleRapport.objects.get(nom='Essai '+source)
                self.assertEqual(modele.parametres.get(c.CLE_SOURCE),source if source!='statistiques' else None)
                self.assertEqual(self.client.get(c.ouvrir(modele)).status_code,200)
                duplique=s.dupliquer(self.u,modele,s.jeton(self.u,modele),'Copie '+source)
                self.assertEqual(duplique.parametres.get(c.CLE_SOURCE),modele.parametres.get(c.CLE_SOURCE))
    def test_synthese_reprise_complete_sans_conversion_et_second_rapport(self):
        d=dict(rapport='synthese',debut='2026-01-01',fin='2026-01-05')
        original=self.client.get(reverse('statistiques'),d);copie=self.composer('statistiques',d)
        self.assertEqual(copie.context['resultats'],original.context['resultats'])
        self.assertEqual(copie.context['resultats']['nuitees_theoriques'],12)
        self.assertEqual(copie.context['resultats']['nuits_distinctes'],12)
        r=self.client.post(reverse('dossiers:rapport_composer',args=['statistiques']),{**d,'nom':'Synthèse conservée','action_modele':'creer'})
        self.assertEqual(r.status_code,302);x=m.ModeleRapport.objects.get(nom='Synthèse conservée')
        r=self.composer('statistiques',{'modele':x.pk});ticket=r.context['attendu_rapport']
        self.assertContains(r,'Enregistrer un second modèle');self.assertContains(r,'Remplacer explicitement')
        r=self.client.post(reverse('dossiers:rapport_composer',args=['statistiques']),{**d,'nom':'Seconde','action_modele':'creer','modele_cible':x.pk,'attendu_modele':ticket,'fin':'2026-01-04'})
        self.assertEqual(r.status_code,302);x.refresh_from_db();self.assertEqual(x.parametres['fin'],'2026-01-05')
        self.assertEqual(m.ModeleRapport.objects.count(),2)
    def test_remplacement_perime_et_suppression_perimee_refuses(self):
        x=m.ModeleRapport.objects.create(auteur=self.u,nom='Original',parametres=dict(rapport='repas',debut='2026-01-01',fin='2026-01-05'))
        ticket=s.jeton(self.u,x);s.changer(self.u,x,ticket,'Renommé')
        d=dict(rapport='repas',debut='2026-01-01',fin='2026-01-05',nom='Saisie conservée',action_modele='remplacer',modele_cible=x.pk,attendu_modele=ticket)
        r=self.client.post(reverse('dossiers:rapport_composer',args=['statistiques']),d)
        self.assertEqual(r.status_code,409);self.assertContains(r,'Saisie conservée',status_code=409)
        r=self.client.post(reverse('dossiers:modele_gerer',args=[x.pk]),dict(nom='Renommé',attendu=ticket,action='supprimer'))
        self.assertEqual(r.status_code,409);self.assertTrue(m.ModeleRapport.objects.filter(pk=x.pk).exists())
        r=self.client.post(reverse('dossiers:modele_gerer',args=[x.pk]),dict(nom='Renommé',attendu=s.jeton(self.u,x),action='supprimer'))
        self.assertEqual(r.status_code,302);self.assertFalse(m.ModeleRapport.objects.filter(pk=x.pk).exists())
        self.assertEqual(m.Personne.objects.count(),3)
    def test_tous_indicateurs_statistiques_derivables_periode_relative_conservee(self):
        from .vues_statistiques import RAPPORTS
        for rapport in RAPPORTS:
            r=self.composer('statistiques',dict(rapport=rapport,periode='mois'))
            self.assertEqual(r.status_code,200)
            from .vues_rapports import parametres_response
            p=parametres_response(r,'statistiques',dict(rapport=rapport,periode='mois'))
            self.assertEqual(p['rapport'],rapport);self.assertEqual(p['periode'],'mois')
    def test_gestion_proprietaire_csrf_et_aucune_ecriture_get(self):
        x=m.ModeleRapport.objects.create(auteur=self.u,nom='Privé',parametres=dict(rapport='repas',debut='2026-01-01',fin='2026-01-05'))
        self.assertContains(self.client.get(reverse('dossiers:rapports_gerer')),'Privé')
        avant=m.ModeleRapport.objects.count();self.client.get(reverse('dossiers:rapport_nouveau'),{'modele':x.pk},follow=True)
        self.assertEqual(m.ModeleRapport.objects.count(),avant)
        autre=get_user_model().objects.create_user('autre-gestion');self.client.force_login(autre)
        self.assertNotContains(self.client.get(reverse('dossiers:rapports_gerer')),'Privé')
        self.assertEqual(self.client.get(reverse('dossiers:rapport_nouveau'),{'modele':x.pk}).status_code,404)
        self.client.force_login(self.u);client=Client(enforce_csrf_checks=True);client.force_login(self.u)
        self.assertEqual(client.post(reverse('dossiers:modele_gerer',args=[x.pk]),dict(action='supprimer',nom='Privé',attendu=s.jeton(self.u,x))).status_code,403)

    def test_confirmation_absente_ne_devient_pas_une_confirmation_fraiche(self):
        params={k:str(v) for k,v in tests_meta_f.ConsolidationStatistiques.config(self,mesure='quantite').items()}
        params.update(schema=1,exploration=True)
        x=m.ModeleRapport.objects.create(auteur=self.u,nom='Ne pas écraser',parametres=params)
        r=self.client.post(reverse('dossiers:explorer'),{**params,'modele_cible':x.pk,'nom':'Écrasement interdit','action_modele':'remplacer'})
        self.assertEqual(r.status_code,409);x.refresh_from_db();self.assertEqual(x.nom,'Ne pas écraser')
