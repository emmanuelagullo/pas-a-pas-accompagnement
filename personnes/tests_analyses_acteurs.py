from django.test import TestCase,Client
from django.urls import reverse
from acteurs import tests as fixtures
from acteurs.models import Habilitation,Responsabilite
from . import analyses as a, models as m


class AnalysesActeursTests(TestCase):
    setUp=fixtures.AccesTests.setUp
    compte=fixtures.AccesTests.compte
    dossier=fixtures.AccesTests.dossier

    def test_selection_enregistree_preuves_exports_et_revocation(self):
        Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin)
        Habilitation.objects.filter(compte=self.ua).update(exporter=True)
        c=Client();c.force_login(self.ua)
        d=a.defaut();d.update(filtre='mes',mesures=[dict(source='personnes',mesure='personnes')])
        modele=m.ModeleRapport.objects.create(auteur=self.ua,nom='Mes dossiers composés',parametres=a.parametres(d))
        r=c.get(reverse('dossiers:analyse'),{'modele':modele.pk})
        self.assertEqual(r.status_code,200,r.content[:300]);self.assertEqual(r.context['resultat']['mesures'][0]['totaux'],{'personnes':1})
        lien=r.context['resultat']['mesures'][0]['totaux_affiches'][0]['url_preuves']
        preuve=c.get(lien);self.assertEqual(preuve.status_code,200)
        self.assertEqual(preuve.context['cellule']['valeur'],1)
        export=c.post(reverse('dossiers:analyse'),dict(definition=a.encoder(d),format='csv'))
        self.assertEqual(export.status_code,200,export.content[:300])
        Habilitation.objects.filter(compte=self.ua).update(exporter=False)
        self.assertEqual(c.post(reverse('dossiers:analyse'),dict(definition=a.encoder(d),format='csv')).status_code,403)

    def test_aucun_basculement_vers_totaux_service_dans_une_analyse_libre(self):
        c=Client();c.force_login(self.ua)
        d=a.defaut();d['mesures']=[dict(source='personnes',mesure='personnes')]
        r=c.get(reverse('dossiers:analyse'),dict(definition=a.encoder(d),portee_statistiques='service'))
        # La route n'interprète pas ce paramètre comme une autorisation nouvelle.
        self.assertEqual(r.status_code,200)
        self.assertNotIn('Dossier B',r.content.decode())

    def test_assemblage_sous_controle_actif_et_export_revoque(self):
        from . import assemblages
        Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin)
        Habilitation.objects.filter(compte=self.ua).update(exporter=True)
        c=Client();c.force_login(self.ua)
        d=a.defaut();d.update(filtre='mes',mesures=[dict(source='personnes',mesure='personnes')])
        composition={**assemblages.defaut(),'parties':[dict(titre='Mes personnes',source='analyse',parametres=a.parametres(d),modele=None,empreinte='',periode_commune=False)]}
        p=dict(definition=a.encoder(composition));url=reverse('dossiers:assemblage')
        r=c.get(url,p);self.assertEqual(r.status_code,200,r.content[:300])
        self.assertEqual(r.context['docs'][0]['blocs'][0]['valeurs'][-1],1)
        self.assertEqual(c.post(url,{**p,'format':'csv'}).status_code,200)
        Habilitation.objects.filter(compte=self.ua).update(exporter=False)
        self.assertEqual(c.post(url,{**p,'format':'csv'}).status_code,403)
