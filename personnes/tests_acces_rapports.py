"""Actions sur le rapport affiché, catalogue distinct et composition indépendante."""
import re
from datetime import date
from html import unescape
from urllib.parse import urlsplit,parse_qs
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from . import models as m, tests_meta_f, repas


class AccesRapportsTests(TestCase):
    setUpTestData=classmethod(tests_meta_f.ConsolidationStatistiques.setUpTestData.__func__)
    config=tests_meta_f.ConsolidationStatistiques.config
    def setUp(self):self.client.force_login(self.u)
    def lien(self,r,texte):
        correspondance=re.search(r'<a\b[^>]*href="([^"]+)"[^>]*>'+re.escape(texte)+r'</a>',r.content.decode())
        self.assertIsNotNone(correspondance,texte)
        return unescape(correspondance.group(1))
    def test_actions_hors_catalogue_et_reprise_exacte_du_rapport_affiche(self):
        repas.distribuer(self.u,self.ar,self.adulte,date(2026,1,2),2)
        params=dict(rapport='exploration_repas',debut='2026-01-01',fin='2026-02-01',regroupement='mois_categorie',service='dejeuner')
        r=self.client.get(reverse('statistiques'),params);self.assertEqual(r.status_code,200)
        html=r.content.decode();debut=html.index('<section class="rapport-composer"');fin=html.index('</section>',debut)
        self.assertLess(html.index('<h1>Statistiques'),debut)
        catalogue=html[html.index('<nav class="rapports-navigation"'):html.index('</nav>',fin)]
        self.assertNotIn('Personnaliser ce rapport',catalogue);self.assertNotIn('Créer un nouveau rapport',catalogue)
        self.assertContains(r,'Rapport affiché — ');self.assertContains(r,'Autres rapports disponibles')
        cible=self.client.get(self.lien(r,'Personnaliser ce rapport'))
        self.assertEqual(cible.status_code,302)
        analyse=self.client.get(cible.url);self.assertEqual(analyse.context['totaux'],{'repas':2})
        self.assertEqual(analyse.context['form']['valeur1'].value(),'Déjeuner')
        self.assertEqual(analyse.context['form']['debut'].value(),'2026-01-01')
    def test_limite_synthese_visible_avant_clic_et_nouveau_rapport_disponible(self):
        r=self.client.get(reverse('statistiques'))
        self.assertContains(r,'disabled aria-describedby="limite-personnalisation"')
        self.assertContains(r,'Cette définition ne peut pas encore être reprise intégralement')
        self.assertContains(r,'Pourquoi ?')
        nouvelle=self.client.get(self.lien(r,'Créer un nouveau rapport'),follow=True)
        self.assertEqual(nouvelle.status_code,200);self.assertContains(nouvelle,'<h1>Nouveau rapport</h1>',html=True)
        self.assertEqual([p['cle'] for p in nouvelle.context['parties_analyse'] if p['ouvert']],['retenir'])
        self.assertEqual(nouvelle.context['form']['population'].value(),'personnes')
        retenir=next(p for p in nouvelle.context['parties_analyse'] if p['cle']=='retenir')
        self.assertEqual([f.name for f in retenir['champs'][:4]],['population','periode','debut','fin'])
    def test_nouveau_ignore_anciens_filtres_et_cible_de_modele_sans_creer(self):
        params={k:str(v) for k,v in self.config(mesure='quantite',filtre1='age',operation1='egal',valeur1='18').items()}
        modele=m.ModeleRapport.objects.create(auteur=self.u,nom='Ne pas remplacer',parametres={**params,'schema':1,'exploration':True})
        r=self.client.get(reverse('dossiers:explorer_nouveau'),{**params,'modele':modele.pk,'modele_cible':modele.pk,'attendu_modele':'ancienne-confirmation','page':'7'},follow=True)
        self.assertEqual(r.status_code,200);self.assertFalse(r.context['form'].errors)
        self.assertEqual(r.context['form']['population'].value(),'personnes');self.assertEqual(r.context['form']['mesure'].value(),'objets')
        self.assertEqual(r.context['form']['filtre1'].value(),'');self.assertIsNone(r.context['modele_cible'])
        self.assertEqual(r.context['attendu_modele'],'');self.assertEqual(r.context['page_obj'].number,1)
        self.assertNotContains(r,'Remplacer explicitement');self.assertContains(r,'name="nouveau" value="1"')
        self.assertEqual(m.ModeleRapport.objects.count(),1);modele.refresh_from_db();self.assertEqual(modele.parametres['valeur1'],'18')
        donnees={k:str(v) if v is not None else '' for k,v in r.context['form'].cleaned_data.items()}
        enregistre=self.client.post(reverse('dossiers:explorer'),{**donnees,'nouveau':'1','nom':'Mon nouveau rapport','action_modele':'variante'})
        self.assertEqual(enregistre.status_code,302);self.assertNotIn('nouveau=',enregistre.url)
        self.assertEqual(m.ModeleRapport.objects.count(),2);modele.refresh_from_db();self.assertEqual(modele.nom,'Ne pas remplacer')
        self.assertNotEqual(parse_qs(urlsplit(enregistre.url).query)['modele'],[str(modele.pk)])
    def test_nouveau_recalcul_et_retour_des_faits_conservent_la_composition(self):
        d={k:str(v) for k,v in self.config(mesure='personnes').items()};d.update(nouveau='1',panneau='compter')
        r=self.client.get(reverse('dossiers:explorer'),d);self.assertTrue(r.context['nouveau_rapport'])
        preuve=self.client.get(r.context['liens_totaux'][0]['url'])
        retour=parse_qs(urlsplit(preuve.context['retour']).query)
        self.assertEqual(retour['nouveau'],['1']);self.assertEqual(retour['panneau'],['compter'])
        self.assertEqual(retour['population'],['sejours'])
        self.assertEqual(self.client.get(preuve.context['retour']).context['totaux'],{'personnes':3})
    def test_actions_specialisees_apres_titre_et_criteres_compatibles(self):
        for route in ('rapport_financements','appels115','rapport_aides','rapport_hebergement_individuel','rapport_parcours','rapport_a'):
            with self.subTest(route=route):
                r=self.client.get(reverse('dossiers:'+route));self.assertEqual(r.status_code,200)
                html=r.content.decode();self.assertLess(html.index('</h1>'),html.index('class="rapport-composer"'))
                self.assertEqual(self.lien(r,'Créer un nouveau rapport'),reverse('dossiers:explorer_nouveau'))
                if route in ('rapport_financements','appels115'):
                    self.assertEqual(self.client.get(self.lien(r,'Personnaliser ce rapport')).status_code,302)
    def test_limite_comparaison_et_appels_conserve_les_criteres_du_rapport(self):
        for route,d in [('statistiques',dict(rapport='repas',debut='2026-01-01',fin='2026-02-01',comparer='1')),
                        ('dossiers:appels115',dict(debut='2026-01-01',fin='2026-02-01',q='texte fictif'))]:
            r=self.client.get(reverse(route),d);self.assertContains(r,'disabled aria-describedby="limite-personnalisation"')
            self.assertNotIn('>Personnaliser ce rapport</a>',r.content.decode())
    def test_creation_sous_droits_sans_permission_enregistrement_ni_ecriture_get(self):
        u=get_user_model().objects.create_user('composeur-lecture-fictif')
        u.user_permissions.add(Permission.objects.get(content_type__app_label='personnes',codename='view_personne'))
        self.client.force_login(u)
        r=self.client.get(reverse('dossiers:explorer_nouveau'),follow=True);self.assertEqual(r.status_code,200)
        self.assertNotContains(r,'Nom du modèle personnel');self.assertEqual(m.ModeleRapport.objects.count(),0)
        self.assertEqual(self.client.post(reverse('dossiers:explorer_nouveau')).status_code,405)
        u.user_permissions.clear();self.assertEqual(self.client.get(reverse('dossiers:explorer_nouveau')).status_code,403)
        self.client.logout();self.assertEqual(self.client.get(reverse('dossiers:explorer_nouveau')).status_code,302)
    def test_rapports_courants_sans_droit_personne_n_exposent_pas_composition(self):
        u=get_user_model().objects.create_user('rapports-courants-fictif')
        u.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes',codename__in=['view_accompagnement','view_sejour','view_repasdistribue']))
        self.client.force_login(u)
        r=self.client.get(reverse('statistiques'));self.assertEqual(r.status_code,200)
        self.assertNotContains(r,'Créer un nouveau rapport');self.assertNotContains(r,'rapport-composer')
