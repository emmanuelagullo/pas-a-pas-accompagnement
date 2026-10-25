"""Modèles personnels : variantes, compatibilité et confirmations concurrentes."""
import json
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase,Client
from django.urls import reverse
from . import models as m, modeles_personnels as s, modeles_echange, tests_meta_f


class ModelesPersonnelsTests(TestCase):
    setUpTestData=classmethod(tests_meta_f.ConsolidationStatistiques.setUpTestData.__func__)
    config=tests_meta_f.ConsolidationStatistiques.config
    def setUp(self):
        self.client.force_login(self.u)
        self.params={k:str(v) for k,v in self.config(mesure='quantite').items()}
        self.params.update(schema=1,exploration=True)
        self.modele=m.ModeleRapport.objects.create(auteur=self.u,nom='Nuitées',parametres=self.params)
    def url(self):return reverse('dossiers:modele_gerer',args=[self.modele.pk])
    def test_renommer_dupliquer_et_ancien_format_exportable(self):
        old=self.modele.parametres.copy()
        r=self.client.post(self.url(),dict(action='renommer',nom='Mon rapport',attendu=s.jeton(self.u,self.modele)))
        self.assertEqual(r.status_code,302);self.modele.refresh_from_db()
        self.assertEqual(self.modele.nom,'Mon rapport')
        self.assertEqual({k:v for k,v in self.modele.parametres.items() if k!=s.REVISION},old)
        r=self.client.post(self.url(),dict(action='dupliquer',nom='Copie',attendu=s.jeton(self.u,self.modele)))
        self.assertEqual(r.status_code,302);copie=m.ModeleRapport.objects.get(nom='Copie')
        self.assertNotEqual(copie.pk,self.modele.pk);self.assertNotIn(s.REVISION,copie.parametres)
        export=json.loads(modeles_echange.exporter(self.u,self.modele));self.assertNotIn(s.REVISION,export['parametres'])
        self.assertEqual(export['parametres']['schema'],1)
    def test_formulaire_perime_meme_apres_renommage_aller_retour(self):
        ticket=s.jeton(self.u,self.modele)
        s.changer(self.u,self.modele,ticket,'Autre')
        s.changer(self.u,self.modele,s.jeton(self.u,self.modele),'Nuitées')
        r=self.client.post(self.url(),dict(action='renommer',nom='Saisie conservée',attendu=ticket))
        self.assertEqual(r.status_code,409);self.assertContains(r,'Saisie conservée',status_code=409)
        self.modele.refresh_from_db();self.assertEqual(self.modele.nom,'Nuitées')
    def test_remplacement_conditionnel_refuse_course_entre_verification_et_update(self):
        ticket=s.jeton(self.u,self.modele)
        with patch('personnes.modeles_personnels.m.ModeleRapport.objects.filter') as filtre:
            filtre.return_value.update.return_value=0
            with self.assertRaises(s.ConflitModele):s.changer(self.u,self.modele,ticket,'Écrasement')
        self.modele.refresh_from_db();self.assertEqual(self.modele.nom,'Nuitées')
    def test_explorateur_variante_remplacement_et_recalcul_garde_ticket(self):
        url=reverse('dossiers:explorer')
        r=self.client.get(url,{'modele':self.modele.pk});ticket=r.context['attendu_modele']
        self.assertContains(r,'Conserver une variante');self.assertContains(r,'Remplacer explicitement')
        d={**self.params,'modele_cible':self.modele.pk,'attendu_modele':ticket,'nom':'Personnes','mesure':'personnes'}
        r=self.client.get(url,d);self.assertEqual(r.context['attendu_modele'],ticket)
        self.assertEqual(r.context['totaux'],{'personnes':3})
        r=self.client.post(url,{**d,'action_modele':'variante'});self.assertEqual(r.status_code,302)
        self.modele.refresh_from_db();self.assertEqual(self.modele.parametres['mesure'],'quantite')
        r=self.client.post(url,{**d,'action_modele':'remplacer'});self.assertEqual(r.status_code,302)
        self.modele.refresh_from_db();self.assertEqual(self.modele.parametres['mesure'],'personnes')
        r=self.client.post(url,{**d,'action_modele':'remplacer','mesure':'objets','nom':'Conflit conservé'})
        self.assertEqual(r.status_code,409);self.assertContains(r,'Conflit conservé',status_code=409)
        self.assertEqual(r.context['form']['mesure'].value(),'objets');self.assertEqual(r.context['attendu_modele'],ticket)
    def test_retour_detail_conserve_page_et_confirmation_du_modele(self):
        from urllib.parse import urlsplit,parse_qs
        from .exploration_releve import retour_verifie
        r=self.client.get(reverse('dossiers:explorer'),{'modele':self.modele.pk})
        ticket=r.context['attendu_modele']
        d={**self.params,'modele_cible':self.modele.pk,'attendu_modele':ticket,'affichage':'detail','page':'1','panneau':'afficher'}
        r=self.client.get(reverse('dossiers:explorer'),d)
        lien=r.context['page_obj'][0]['url']
        token=parse_qs(urlsplit(lien).query)['retour_exploration'][0]
        retour=parse_qs(urlsplit(retour_verifie(self.u,token)).query)
        self.assertEqual(retour['attendu_modele'],[ticket]);self.assertEqual(retour['page'],['1'])
        self.assertEqual(retour['modele_cible'],[str(self.modele.pk)])

    def test_ancien_modele_natif_reste_natif_et_conflit_garde_configuration(self):
        self.modele.parametres=dict(rapport='repas',debut='2026-01-01',fin='2026-01-05',periode='',regroupement='mois_categorie',service='',lieu='',comparer='')
        self.modele.save();ticket=s.jeton(self.u,self.modele)
        r=self.client.get(reverse('statistiques'),{'modele':self.modele.pk})
        self.assertEqual(r.status_code,200);self.assertContains(r,'Remplacer explicitement')
        d={**self.modele.parametres,'rapport':'ages','nom':'Âges','attendu':ticket,'action':'remplacer'}
        r=self.client.post(self.url(),d);self.assertEqual(r.status_code,302)
        self.modele.refresh_from_db();self.assertNotIn('exploration',self.modele.parametres)
        self.assertEqual(self.modele.parametres['rapport'],'ages')
        r=self.client.post(self.url(),{**d,'rapport':'repas'});self.assertEqual(r.status_code,409)
        self.assertIn('rapport=repas',r.context['reprise_configuration'])
    def test_propriete_droits_csrf_et_jeton_obligatoire(self):
        autre=get_user_model().objects.create_user('autre-fictif');self.client.force_login(autre)
        self.assertEqual(self.client.get(self.url()).status_code,404)
        self.assertEqual(self.client.post(self.url(),{'action':'renommer'}).status_code,404)
        self.client.force_login(self.u)
        r=self.client.post(self.url(),dict(action='renommer',nom='Sans jeton',attendu='faux'))
        self.assertEqual(r.status_code,409)
        c=Client(enforce_csrf_checks=True);c.force_login(self.u)
        self.assertEqual(c.post(self.url(),dict(action='renommer',nom='Sans CSRF')).status_code,403)
        self.modele.refresh_from_db();self.assertEqual(self.modele.nom,'Nuitées')
    def test_invalides_limite_et_type_ne_changent_pas_original(self):
        ticket=s.jeton(self.u,self.modele)
        for params in ({**self.params,'mesure':'injection'},dict(rapport='repas')):
            with self.assertRaises(ValidationError):s.changer(self.u,self.modele,ticket,'Invalide',params)
        with self.assertRaises(ValidationError):s.changer(self.u,self.modele,ticket,' ')
        m.ModeleRapport.objects.bulk_create([m.ModeleRapport(auteur=self.u,nom=str(i),parametres=self.params) for i in range(29)])
        with self.assertRaises(ValidationError):s.dupliquer(self.u,self.modele,ticket,'Trop')
        self.modele.refresh_from_db();self.assertEqual(self.modele.parametres,self.params)


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import connections
from django.test import TransactionTestCase
from django.contrib.auth.models import Permission


class ConcurrenceModelesTests(TransactionTestCase):
    def test_deux_confirmations_sqlite_un_seul_remplacement(self):
        u=get_user_model().objects.create_user('concurrence-modele-fictive')
        u.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes',codename__in=['view_accompagnement','view_sejour','view_repasdistribue']))
        modele=m.ModeleRapport.objects.create(auteur=u,nom='Initial',parametres={'rapport':'repas'})
        ticket=s.jeton(u,modele);barriere=Barrier(2);verifier=s.verifier
        def synchroniser(*args):
            verifier(*args);barriere.wait(timeout=10)
        def confirmer(nom):
            try:
                acteur=get_user_model().objects.get(pk=u.pk);copie=m.ModeleRapport.objects.get(pk=modele.pk)
                try:s.changer(acteur,copie,ticket,nom);return 'ok'
                except s.ConflitModele:return 'conflit'
            finally:connections.close_all()
        with patch('personnes.modeles_personnels.verifier',side_effect=synchroniser):
            with ThreadPoolExecutor(max_workers=2) as pool:resultats=list(pool.map(confirmer,['Premier','Second']))
        self.assertCountEqual(resultats,['ok','conflit']);modele.refresh_from_db()
        self.assertEqual(modele.parametres[s.REVISION],1)
