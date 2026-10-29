from copy import deepcopy
from datetime import date
from django.test import TestCase,RequestFactory
from django.core.exceptions import ValidationError,PermissionDenied
from django.urls import reverse
from . import tests_meta_f as fixtures, models as m, analyses, assemblages as a, modeles_personnels as gestion


class AssemblagesTests(TestCase):
    setUpTestData=classmethod(fixtures.ConsolidationStatistiques.setUpTestData.__func__)
    def setUp(self):
        self.client.force_login(self.u)
        self.request=RequestFactory().get('/');self.request.user=self.u;self.request.session={}
    def partie(self):
        return dict(titre='Repas',description='',source='statistiques',parametres=dict(rapport='repas',debut='2026-01-01',fin='2026-01-05'),modele=None,empreinte='',periode_commune=False)
    def test_toutes_definitions_du_catalogue_reutilisables_sous_leurs_droits(self):
        from .catalogue_rapports import catalogue
        resultats=[]
        for choix in catalogue(self.u):
            partie=a.photographier(self.u,self.request,cle=choix['cle'])
            d={**a.defaut(),'parties':[partie]}
            docs=a.documents(self.u,self.request,d)
            self.assertEqual(len(docs),1,choix['cle']);self.assertEqual(docs[0]['titre'],choix['titre']);resultats.append(choix['cle'])
        self.assertEqual(len(resultats),18)
    def test_version_stable_modification_et_suppression_original(self):
        d=analyses.defaut();d.update(debut='2026-01-01',fin='2026-01-05',reference='2026-01-04')
        modele=m.ModeleRapport.objects.create(auteur=self.u,nom='Mon modèle',parametres=analyses.parametres(d))
        p=a.photographier(self.u,self.request,modele=modele);compose={**a.defaut(),'parties':[p]}
        avant=deepcopy(compose)
        modele.nom='Modifié';modele.save()
        doc=a.documents(self.u,self.request,compose)[0];self.assertTrue(doc['origine_modifiee']);self.assertEqual(doc['titre'],'Mon modèle')
        self.assertEqual(compose,avant)
        modele.delete();self.assertTrue(a.documents(self.u,self.request,compose)[0]['origine_absente'])
    def test_periode_commune_explicite_et_date_reference_non_ecrasee(self):
        p=self.partie();d={**a.defaut(),'parties':[p],'debut':'2026-02-01','fin':'2026-03-01'}
        self.assertEqual(a.appliquer_periode(d,p)['debut'],'2026-01-01')
        p['periode_commune']=True;self.assertEqual(a.appliquer_periode(d,p)['debut'],'2026-02-01')
        p['parametres']={'date':'2026-01-03'}
        with self.assertRaises(ValidationError):a.appliquer_periode(d,p)
    def test_interface_reordonner_conserver_exporter_et_cas(self):
        d={**a.defaut(),'parties':[self.partie(),{**self.partie(),'titre':'Second'}]};url=reverse('dossiers:assemblage')
        r=self.client.get(url,{'definition':analyses.encoder(d)});self.assertEqual(r.status_code,200,r.content[:300])
        r=self.client.post(url,dict(definition=analyses.encoder(d),action='monter',partie=1));self.assertEqual(r.status_code,200)
        self.assertEqual(r.context['d']['parties'][0]['titre'],'Second')
        r=self.client.post(url,dict(definition=analyses.encoder(d),action='creer',nom='Bilan',nature='modele'));self.assertEqual(r.status_code,302,r.content[:300])
        modele=m.ModeleRapport.objects.get(nom='Bilan')
        r=self.client.post(url,dict(definition=analyses.encoder(d),cible=modele.pk,format='csv',resume='Essai'))
        self.assertEqual(r.status_code,200);self.assertIn(b'# Partie;1;Repas',r.content);self.assertIn(b'# Partie;2;Second',r.content)
        r=self.client.post(url,dict(definition=analyses.encoder(d),cible=modele.pk,format='pdf'))
        self.assertEqual(r.status_code,200);self.assertTrue(r.content.startswith(b'%PDF'))
        r=self.client.post(url,dict(definition=analyses.encoder(d),cible=modele.pk,action='remplacer',nom='Bilan',nature='modele',attendu='vieux'))
        self.assertEqual(r.status_code,409)
    def test_pas_de_compte_exterieur_ni_imbrication(self):
        from django.contrib.auth import get_user_model
        autre=get_user_model().objects.create_user('autre-assemblage')
        modele=m.ModeleRapport.objects.create(auteur=autre,nom='Privé',parametres=analyses.parametres(analyses.defaut()))
        with self.assertRaises(PermissionDenied):a.photographier(self.u,self.request,modele=modele)
        modele=m.ModeleRapport.objects.create(auteur=self.u,nom='Assemblée',parametres=a.parametres(a.defaut()))
        with self.assertRaises(ValidationError):a.photographier(self.u,self.request,modele=modele)
