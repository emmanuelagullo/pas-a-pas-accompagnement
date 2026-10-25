import csv
from io import StringIO
from datetime import date
from decimal import Decimal
from urllib.parse import urlsplit,parse_qs
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from . import exploration as e, justificatifs_exploration as j, tests_meta_f, models as m


class JustificatifsTests(TestCase):
    setUpTestData=classmethod(tests_meta_f.ConsolidationStatistiques.setUpTestData.__func__)
    config=tests_meta_f.ConsolidationStatistiques.config
    def ouvrir(self,mesure='quantite',**kw):
        self.client.force_login(self.u)
        d=self.config(mesure=mesure,**kw)
        rs,ts,xs=e.calculer(self.u,d,contributions=True)
        c=rs[0] if rs else j.totaux_cellules(ts,xs,mesure)[0]
        url=j.lien(self.u,d,mesure,c,3)
        return url,self.client.get(url)

    def test_nuitees_individuelles_justification_objet_retours_pagination(self):
        call_command('autoriser_bd6',self.u.username,stdout=StringIO())
        url,r=self.ouvrir(axe='age',filtre1='age',operation1='egal',valeur1='18')
        self.assertEqual(r.status_code,200,r.content.decode())
        self.assertEqual(r.context['cellule']['valeur'],4)
        self.assertEqual(sum(x['valeur'] for x in r.context['page_obj']),4)
        self.assertIn('page=3',r.context['retour'])
        self.assertContains(r,'Anniversaire fictif F');self.assertNotContains(r,'Adulte fictif F')
        fait=self.client.get(r.context['page_obj'][0]['url']);self.assertEqual(fait.status_code,200)
        self.assertEqual(fait.context['objet']['id'],str(self.sejour.pk))
        dossier=self.client.get(fait.context['native']);self.assertContains(dossier,'Revenir aux résultats du rapport')
        retour=dossier.context['retour_exploration'];self.assertIn('preuve=',retour)
        self.assertEqual(self.client.get(retour).context['cellule']['valeur'],4)
        lignes=list(csv.DictReader(StringIO(self.client.get(url+'&format=csv').content.decode()),delimiter=';'))
        self.assertEqual(sum(Decimal(x['Valeur']) for x in lignes),4)

    def test_distincts_et_sous_total_multivaleurs(self):
        m.ComplementIdentite.objects.create(personne=self.adulte,debut=date(2026,1,1),auteur=self.u,source='Fictif',nationalites=['A','B'])
        self.client.force_login(self.u)
        d=self.config(mesure='personnes',axe='total',croisement='identite.nationalites',sous_totaux=True)
        rows,t,xs=e.calculer(self.u,d,contributions=True)
        c=next(x for x in rows if x.get('sous_total'))
        r=self.client.get(j.lien(self.u,d,'personnes',c))
        self.assertEqual(r.context['cellule']['valeur'],3)
        self.assertEqual(sum(x['valeur'] for x in r.context['page_obj']),3)

    def test_nuitees_majorite_et_moyenne_par_objet(self):
        _,r=self.ouvrir('nuitees_adultes');self.assertEqual(r.context['cellule']['valeur'],6)
        self.assertEqual(sum(x['valeur'] for x in r.context['page_obj']),6)
        _,r=self.ouvrir('moyenne');self.assertEqual(r.context['cellule']['valeur'],12)
        self.assertEqual([x['valeur'] for x in r.context['page_obj']],[12])
        self.assertContains(r,'par objet')

    def test_donnees_modifiees_et_jeton_intercompte_refuses(self):
        url,r=self.ouvrir();self.assertEqual(r.status_code,200)
        self.sejour.fin=date(2026,1,4);self.sejour.save(update_fields=['fin'])
        r=self.client.get(url);self.assertEqual(r.status_code,409);self.assertContains(r,'données ont changé',status_code=409)
        self.assertIn('page=3',r.context['retour'])
        autre=get_user_model().objects.create_user('autre-preuve-fictive');self.client.force_login(autre)
        self.assertEqual(self.client.get(url).status_code,404)

    def test_droits_revalides_et_objet_etranger_refuse(self):
        url,r=self.ouvrir();token=parse_qs(urlsplit(url).query)['preuve'][0]
        self.assertEqual(self.client.get(reverse('dossiers:explorer_fait'),{'preuve':token,'objet':'inexistant'}).status_code,404)
        self.u.user_permissions.remove(Permission.objects.get(codename='view_sejour'))
        self.assertEqual(self.client.get(url).status_code,403)

    def test_liens_html_sur_cellules_et_totaux(self):
        self.client.force_login(self.u)
        r=self.client.get(reverse('dossiers:explorer'),{k:str(v) for k,v in self.config(mesure='quantite',axe='age').items()})
        self.assertEqual(r.status_code,200)
        self.assertIn('url_preuves',r.context['page_obj'][0])
        self.assertTrue(r.context['liens_totaux'])
        preuve=self.client.get(r.context['liens_totaux'][0]['url'])
        self.assertEqual(preuve.context['cellule']['valeur'],12)
