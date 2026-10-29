from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError, PermissionDenied
from . import tests_meta_f as fixtures, models as m, repas, analyses as a


class AnalysesTests(TestCase):
    setUpTestData=classmethod(fixtures.ConsolidationStatistiques.setUpTestData.__func__)

    def definition(self,**kw):
        return {**a.defaut(),'debut':'2026-01-01','fin':'2026-01-05','reference':'2026-01-04',**kw}






    def test_traduction_mouvements_tous_les_dix_indicateurs(self):
        from .traduction_analyses import depuis_rapport
        from .rapports_metier import mouvements
        d=depuis_rapport(self.u,'statistiques',dict(rapport='mouvements',debut='2026-01-01',fin='2026-01-06'))
        r=a.calculer(self.u,d)
        self.assertEqual([next(iter(x['totaux'].values())) for x in r['mesures']],list(mouvements(date(2026,1,1),date(2026,1,6)).values()))

    def test_interface_conservation_export_et_retour_des_preuves(self):
        from django.urls import reverse
        self.client.force_login(self.u)
        d=self.definition(mesures=[dict(source='sejours',mesure='quantite')])
        url=reverse('dossiers:analyse');r=self.client.get(url,dict(definition=a.encoder(d)))
        self.assertEqual(r.status_code,200);self.assertContains(r,'Éléments à compter');self.assertNotContains(r,'Sur quoi porte la recherche')
        lien=r.context['resultat']['mesures'][0]['totaux_affiches'][0]['url_preuves']
        preuve=self.client.get(lien);self.assertEqual(preuve.status_code,200)
        objet=self.client.get(list(preuve.context['page_obj'])[0]['url']);self.assertEqual(objet.status_code,200)
        self.assertIn('retour_exploration=',objet.context['native'])
        x=self.client.post(url,dict(definition=a.encoder(d),nom='Mon analyse',nature='modele',action='creer'))
        self.assertEqual(x.status_code,302,x.content[:500]);modele=m.ModeleRapport.objects.get(nom='Mon analyse')
        r=self.client.get(x.url);self.assertEqual(r.status_code,200)
        export=self.client.post(url,dict(definition=a.encoder(d),cible=modele.pk,format='csv'))
        self.assertEqual(export.status_code,200);self.assertIn(b'12',export.content)
        obsolete=self.client.post(url,dict(definition=a.encoder(d),cible=modele.pk,nom='Remplacer',nature='modele',action='remplacer',attendu='perime'))
        self.assertEqual(obsolete.status_code,409)

    def test_traductions_synthese_hebergement_ages_et_periode_sans_faits(self):
        from .traduction_analyses import depuis_rapport
        from .statistiques import bilan
        params=dict(debut='2026-01-01',fin='2026-01-05')
        r=a.calculer(self.u,depuis_rapport(self.u,'statistiques',dict(rapport='synthese',**params)))
        self.assertEqual([next(iter(x['totaux'].values())) for x in r['mesures']],list(bilan(date(2026,1,1),date(2026,1,5)).values()))
        d=depuis_rapport(self.u,'statistiques',dict(rapport='hebergement',debut='2000-01-01',fin='2000-01-02'))
        r=a.calculer(self.u,d)
        self.assertEqual([next(iter(x['totaux'].values())) for x in r['mesures']],[0]*7)
        r=a.calculer(self.u,depuis_rapport(self.u,'statistiques',dict(rapport='ages',**params)))
        self.assertEqual(r['mesures'][0]['totaux'],{'personnes':3})


    def test_echange_schema_deux_et_anciens_modeles_compatibles(self):
        from . import modeles_echange as ech
        from .traduction_analyses import depuis_exploration
        d=self.definition();x=m.ModeleRapport.objects.create(auteur=self.u,nom='Composition exportée',parametres=a.parametres(d))
        contenu=ech.exporter(self.u,x);copie=ech.importer(self.u,contenu)
        self.assertEqual(a.lire(copie.parametres),a.lire(x.parametres))
        ancien={k:str(v) for k,v in fixtures.ConsolidationStatistiques.config(self,mesure='personnes').items()};ancien.update(schema=1,exploration=True)
        y=m.ModeleRapport.objects.create(auteur=self.u,nom='Historique',parametres=ancien)
        self.assertIn(b'"schema": 1',ech.exporter(self.u,y))
        self.assertEqual(a.calculer(self.u,depuis_exploration(self.u,ancien))['mesures'][0]['totaux'],{'personnes':3})

    def test_preuve_perimee_apres_correction_et_retour_sur_objet_exact(self):
        from django.urls import reverse
        from urllib.parse import urlsplit,parse_qs
        from .exploration_releve import retour_verifie
        self.client.force_login(self.u)
        d=self.definition(affichage='detail',mesures=[dict(source='sejours',mesure='quantite')])
        r=self.client.get(reverse('dossiers:analyse'),dict(definition=a.encoder(d)))
        lien=r.context['resultat']['details'][0]['cellules_affichees'][0][0]['url_preuves']
        preuve=self.client.get(lien);self.assertEqual(preuve.status_code,200)
        fait=self.client.get(list(preuve.context['page_obj'])[0]['url'])
        token=parse_qs(urlsplit(fait.context['native']).query)['retour_exploration'][0]
        self.assertIn(reverse('dossiers:analyse_preuves'),retour_verifie(self.u,token))
        m.Sejour.objects.filter(pk=self.sejour.pk).update(fin=date(2026,1,3))
        self.assertEqual(self.client.get(lien).status_code,409)

    def test_conserver_modele_et_personnalisation_ensemble(self):
        from django.urls import reverse
        self.client.force_login(self.u)
        r=self.client.post(reverse('dossiers:analyse'),dict(definition=a.encoder(self.definition()),action='creer',nom='Habitude',nom_modele='Définition',nature='ensemble'))
        self.assertEqual(r.status_code,302,r.content[:300])
        personnalisation=m.ModeleRapport.objects.get(nom='Habitude');modele=m.ModeleRapport.objects.get(nom='Définition')
        self.assertEqual(personnalisation.modele_source,modele)


    def test_preference_export_depuis_gestion_et_export_invalide(self):
        from . import modeles_personnels as gestion
        from django.urls import reverse
        self.client.force_login(self.u)
        d=self.definition();x=m.ModeleRapport.objects.create(auteur=self.u,nom='Préférence',parametres=a.parametres(d))
        gestion.changer(self.u,x,gestion.jeton(self.u,x),x.nom,export_prioritaire='csv')
        r=self.client.get(reverse('dossiers:analyse'),dict(modele=x.pk))
        self.assertEqual(r.context['prioritaire'],'csv')
        d['mesures'][0]['mesure']='nuits_distinctes'
        r=self.client.post(reverse('dossiers:analyse'),dict(definition=a.encoder(d),format='pdf'))
        self.assertEqual(r.status_code,422)
