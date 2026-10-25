import csv
from datetime import date
from decimal import Decimal
from io import StringIO
from django.test import TestCase
from django.urls import reverse
from . import models as m, exploration as e, statistiques, tests_meta_f, repas, financements


class PersonnalisationTests(TestCase):
    setUpTestData=classmethod(tests_meta_f.ConsolidationStatistiques.setUpTestData.__func__)
    config=tests_meta_f.ConsolidationStatistiques.config

    def adapter(self,source,**params):
        self.client.force_login(self.u)
        return self.client.get(reverse('dossiers:personnaliser_rapport',args=[source]),params)

    def test_repas_mois_services_filtre_et_zero_exactement_repris(self):
        repas.distribuer(self.u,self.ar,self.adulte,date(2026,1,2),2)
        params=dict(rapport='exploration_repas',debut='2026-01-01',fin='2026-03-01',regroupement='mois_categorie',service='dejeuner')
        r=self.adapter('statistiques',**params);self.assertEqual(r.status_code,302,r.content.decode())
        r=self.client.get(r.url);self.assertEqual(r.status_code,200);self.assertFalse(r.context['form'].errors,r.context['form'].errors)
        attendu=statistiques.exploration_repas(date(2026,1,1),date(2026,3,1),service='dejeuner')
        obtenu=list(r.context['page_obj'])
        self.assertEqual([(x['axe'],x['valeur']) for x in obtenu],[(x['mois'],x['quantite']) for x in attendu])
        self.assertEqual([x['valeur'] for x in obtenu],[2,0])
        self.assertContains(r,'Revenir au rapport courant')

    def test_rapport_repas_vide_trois_services_zero_et_preuve_zero(self):
        r=self.adapter('statistiques',rapport='repas',debut='2026-01-01',fin='2026-02-01')
        r=self.client.get(r.url)
        self.assertEqual([x['valeur'] for x in r.context['page_obj']],[0,0,0])
        self.assertEqual(r.context['totaux'],{'repas':0})
        preuve=self.client.get(r.context['page_obj'][0]['url_preuves']);self.assertEqual(preuve.status_code,200)
        self.assertEqual(preuve.context['cellule']['valeur'],0);self.assertEqual(len(preuve.context['page_obj']),0)

    def test_regroupements_repas_et_csv(self):
        repas.distribuer(self.u,self.ar,self.adulte,date(2026,1,2),2)
        for regroupement in ('mois','categorie','mois_categorie'):
            r=self.adapter('statistiques',rapport='exploration_repas',debut='2026-01-01',fin='2026-02-01',regroupement=regroupement)
            r=self.client.get(r.url+'&format=csv');self.assertEqual(r.status_code,200)
            lignes=list(csv.DictReader(StringIO(r.content.decode()),delimiter=';'))
            self.assertEqual(sum(Decimal(x['Valeur']) for x in lignes),2)

    def test_refus_rapport_non_representable_et_comparaison_sans_perte(self):
        for rapport in ('synthese','hebergement','mensuel','mouvements','ages'):
            r=self.adapter('statistiques',rapport=rapport,debut='2026-01-01',fin='2026-02-01')
            self.assertEqual(r.status_code,422);self.assertContains(r,'Aucune population',status_code=422)
            self.assertIn('rapport='+rapport,r.context['retour'])
        self.assertEqual(self.adapter('statistiques',rapport='repas',debut='2026-01-01',fin='2026-02-01',comparer='1').status_code,422)

    def test_financements_repris_quantite_prix_montant_et_casse(self):
        lignes=[dict(phase='autorise',date=date(2026,1,2),libelle='Coût fictif',unite=unite,categorie='Adultes',quantite=Decimal(2),prix=prix,tarif=None,justification='Fictif') for unite,prix in [('Titre',Decimal(3)),('titre',Decimal(7))]]
        financements.enregistrer(self.u,self.accord,financements.jeton(self.accord),'Fictif','definition',lignes,[],
            emetteur=None,mentions='',debut=date(2026,1,1),fin=date(2026,1,5),devise='EUR',prestataire=None,prescripteur=None,facturation=None,signataire=None,reference='Calcul FICTIF',source='Fictif')
        params=dict(debut='2026-01-01',fin='2026-02-01',phase='autorise',mode='couts',unite='Titre',reference='Calcul FICTIF',q='Ménage fictif F',nature='hebergement')
        original=self.client.get(reverse('dossiers:rapport_financements'),params) if self.client.session.get('_auth_user_id') else None
        r=self.adapter('financements',**params);self.assertEqual(r.status_code,302)
        r=self.client.get(r.url);self.assertFalse(r.context['form'].errors,r.context['form'].errors)
        self.assertEqual(r.context['totaux'],{'EUR / autorise':6})
        self.assertEqual(r.context['nombre'],1)
        params['unite']='titre';r=self.adapter('financements',**params)
        self.assertEqual(self.client.get(r.url).context['totaux'],{'EUR / autorise':14})

    def test_appels_incompatibles_et_droits(self):
        r=self.adapter('appels',debut='2026-01-01',fin='2026-02-01',q='texte fictif')
        self.assertEqual(r.status_code,422)
        r=self.adapter('appels',debut='2026-01-01',fin='2026-02-01',motif_principal='Hébergement fictif',heure_min=22,heure_max=24)
        self.assertEqual(r.status_code,302)
        self.assertFalse(self.client.get(r.url).context['form'].errors)
        from django.contrib.auth import get_user_model
        u=get_user_model().objects.create_user('sans-rapports-fictif');self.client.force_login(u)
        self.assertEqual(self.client.get(reverse('dossiers:personnaliser_rapport',args=['financements']),{}).status_code,403)
