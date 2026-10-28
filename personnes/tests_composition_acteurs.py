from django.test import TestCase,Client
from django.urls import reverse
from acteurs import tests as acteurs_tests
from acteurs.models import Habilitation,Responsabilite
from . import models as m
from . import tests_exports_composition

class CompositionActeursTests(TestCase):
    setUp=acteurs_tests.AccesTests.setUp
    compte=acteurs_tests.AccesTests.compte
    dossier=acteurs_tests.AccesTests.dossier
    token=tests_exports_composition.ExportsCompositionTests.token
    def test_perimetre_enregistre_liens_justificatifs_et_exports(self):
        from acteurs import services as s
        from datetime import date
        Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin)
        Habilitation.objects.filter(compte=self.ua).update(exporter=True)
        c=Client();c.force_login(self.ua)
        params=dict(schema=1,exploration=True,population='personnes',debut='2026-01-01',fin='2026-02-01',reference='2026-01-31',mesure='personnes',axe='total',filtre='mes')
        modele=m.ModeleRapport.objects.create(auteur=self.ua,nom='Mes personnes',parametres=params)
        r=c.get(reverse('dossiers:explorer'),{'modele':modele.pk})
        self.assertEqual(r.status_code,200,r.content[:300]);self.assertEqual(r.context['totaux'],{'personnes':1})
        self.assertContains(r,'value="mes"');self.assertIn('filtre=mes',r.context['query_rapport'])
        preuve=c.get(r.context['liens_totaux'][0]['url']);self.assertEqual(preuve.status_code,200,preuve.content[:300])
        self.assertIn('filtre=mes',preuve.context['retour'])
        ex=c.post(reverse('dossiers:rapport_exporter'),dict(definition=self.token(r),format='csv'))
        self.assertEqual(ex.status_code,200,ex.content[:300])
        Habilitation.objects.filter(compte=self.ua).update(exporter=False)
        self.assertEqual(c.post(reverse('dossiers:rapport_exporter'),dict(definition=self.token(r),format='csv')).status_code,403)
