"""Scénarios exclusivement fictifs : états, corrections et périmètres."""
from datetime import date,timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.db import connection
from django.test.utils import CaptureQueriesContext
from . import models as m, parcours, bd6, frises, frises_objectifs
from .tests_parcours import valeurs
from acteurs import tests as acteurs_tests


class ObjectifsTests(TestCase):
    def setUp(self):
        self.u=get_user_model().objects.create_superuser('objectifs-fictifs')
        self.p=m.Personne.objects.create(designation='Maïa fictive',cree_par=self.u)
        self.q=m.Personne.objects.create(designation='Autre personne fictive',cree_par=self.u)
        self.client.force_login(self.u)
        self.url=reverse('dossiers:detail',args=['personne',self.p.pk])
        self.e=self.creer(self.p)

    def creer(self,p,jour=date(2026,1,10),**kw):
        return parcours.creer(self.u,'objectifs',p,[p],jour,'Entretien fictif',bd6.jeton(p),**valeurs('objectifs',echeance=date(2026,12,31),**kw))

    def version(self,jour,**kw):
        d=valeurs('objectifs',echeance=date(2026,12,31),**kw)
        parcours.enregistrer(self.u,'objectifs',self.e,jour,'Entretien fictif',bd6.jeton(self.e),**d)

    def activer(self):
        r=self.client.get(self.url)
        self.client.post(reverse('dossiers:frises_preference'),{'actif':'1','retour_frise':r.context['frise_retour']})

    def bande(self,page):
        g=next(x for x in page.context['condition_projets'] if x['ancre']=='projet-objectifs')
        return g['items'][0]['frise_objectif']

    def test_alternative_sur_place_et_retour_exact(self):
        r=self.client.get(self.url)
        self.assertContains(r,'data-frise-slot="objectif-'+str(self.e.pk)+'"')
        self.assertNotContains(r,'class="objectif-mini"')
        self.activer();r=self.client.get(self.url)
        self.assertContains(r,'class="objectif-mini"')
        b=self.bande(r)
        self.assertEqual(b['lignes'][0]['fait'].element_id,self.e.pk)
        source=self.client.get(b['source']);retour=source.context['retour']
        self.assertIn(self.url,retour)
        revenu=self.client.get(retour)
        self.assertContains(revenu,'id="objectif-histoire-'+str(self.e.pk)+'" open')
        from django.core import signing
        from urllib.parse import urlsplit,parse_qsl,urlencode
        u=urlsplit(b['source']);query=dict(parse_qsl(u.query))
        for payload in [{'compte':str(self.u.pk),'retour':'https://exemple.invalid'},
                        {'compte':'autre-compte','retour':self.url},
                        {'compte':str(self.u.pk),'retour':42}]:
            query['retour_frise_objectif']=signing.dumps(payload,salt=frises.SEL)
            refuse=self.client.get(u.path+'?'+urlencode(query))
            self.assertNotIn('frise_objectif=',refuse.context['retour'])
            self.assertNotIn('exemple.invalid',refuse.context['retour'])

    def test_suspension_reprise_atteint_et_echeance_independante(self):
        self.version(date(2026,2,15),etat='suspendu')
        self.version(date(2026,3,5))
        self.version(date(2026,6,12),etat='atteint')
        self.activer();b=self.bande(self.client.get(self.url))
        self.assertEqual([x['type'] for x in b['marques']],['encours','suspendu','encours','atteint'])
        self.assertTrue(b['marques'][-1]['point'])
        self.assertEqual(b['lignes'][-1]['fait'].echeance,date(2026,12,31))
        # La lecture à mars n'affiche pas l'état atteint en juin.
        r=self.client.get(self.url,{'vue_sociale':'date','date_sociale':'2026-03-10'})
        b=self.bande(r)
        self.assertEqual([x['type'] for x in b['marques']],['encours','suspendu','encours'])
        self.assertEqual(b['fin'],date(2026,3,10))
        menage=m.Menage.objects.create(libelle='Ménage fictif de qualification',cree_par=self.u)
        m.Appartenance.objects.create(menage=menage,personne=self.p,debut=date(2026,1,1))
        prise=m.Accompagnement.objects.create(menage=menage,debut=date(2026,3,10),cree_par=self.u)
        prise.beneficiaires.add(self.p)
        url3=reverse('dossiers:prise',args=['personne',self.p.pk,prise.pk])
        b3=self.bande(self.client.get(url3))
        self.assertEqual(b3['fin'],date(2026,3,10))
        self.assertEqual([x['type'] for x in b3['marques']],['encours','suspendu','encours'])
        self.assertIn(url3,self.client.get(b3['source']).context['retour'])

        # Un début le jour consulté reste ponctuel, sans durée fabriquée.
        v=m.VersionObjectif(debut=date(2026,10,29),etat='encours',titre='Fictif')
        point=frises_objectifs.projeter([v],frises.Echelle(date(2026,10,28),date(2026,10,29),comprimee=False))
        self.assertEqual(point['marques'],[{'x':'100','w':'0','type':'encours','point':True}])


    def test_correction_annulation_et_beneficiaires(self):
        self.version(date(2026,2,15),etat='suspendu')
        v=self.e.versions.get(debut=date(2026,2,15))
        parcours.enregistrer(self.u,'objectifs',self.e,v.debut,'Correction fictive',bd6.jeton(self.e),correction=v.pk,motif='Erreur fictive',**valeurs('objectifs',etat='abandonne'))
        autre=self.creer(self.q,titre='Objectif autre personne réservé')
        self.activer();r=self.client.get(self.url);b=self.bande(r)
        self.assertEqual([x['type'] for x in b['marques']],['encours','abandonne'])
        self.assertNotContains(r,'Objectif autre personne réservé')
        self.assertEqual(len(b['lignes']),2)
        parcours.annuler(self.u,'objectifs',self.e,'Erreur de cible fictive',bd6.jeton(self.e))
        self.assertNotContains(self.client.get(self.url),'data-frise-slot="objectif-'+str(self.e.pk)+'"')

    def test_changement_de_titre_ne_cree_pas_une_reussite_supplementaire(self):
        self.version(date(2026,2,1),etat='atteint')
        self.version(date(2026,3,1),etat='atteint',titre='Titre rectifié fictif')
        self.activer();b=self.bande(self.client.get(self.url))
        self.assertEqual(len([x for x in b['marques'] if x['type']=='atteint']),1)
        self.assertEqual(len(b['lignes']),3)

    def test_formulaires_existants_et_portee(self):
        self.activer();b=self.bande(self.client.get(self.url));l=b['lignes'][0]
        r=self.client.get(l['modifier'],HTTP_X_CONDITION_FORM='1')
        self.assertContains(r,'data-condition-form')
        self.assertContains(r,'condition_confirmation')
        self.assertEqual(r.context['form'].initial['debut'],l['fait'].debut)

    def test_chargement_groupe_et_pas_de_fausse_continuite(self):
        items=[{'fait':self.e.versions.first(),'url':'/fictif'}]
        with CaptureQueriesContext(connection) as petit:frises_objectifs.charger(self.u,items,'personne',self.p,date(2026,10,29),lambda *a:'/fictif')
        for i in range(8):
            e=self.creer(self.p,titre=f'Objectif fictif {i}')
            items.append({'fait':e.versions.select_related('element').first(),'url':'/fictif'})
        with CaptureQueriesContext(connection) as grand:frises_objectifs.charger(self.u,items,'personne',self.p,date(2026,10,29),lambda *a:'/fictif')
        self.assertLessEqual(len(grand),len(petit)+1)
        self.version(date(2026,3,1))
        v=self.e.versions.get(debut=date(2026,1,10));v.fin=date(2026,2,1);v.save(update_fields=['fin'])
        vs=list(self.e.versions.order_by('debut'))
        b=frises_objectifs.projeter(vs,frises.Echelle(date(2026,1,10),date(2026,4,1),comprimee=False))
        self.assertEqual(len(b['marques']),2)
        debut=date(2025,1,1)
        versions=[m.VersionObjectif(debut=debut+timedelta(days=i),fin=debut+timedelta(days=i+1),etat='encours' if i%2 else 'suspendu',titre='Fictif') for i in range(200)]
        dense=frises_objectifs.projeter(versions,frises.Echelle(debut,debut+timedelta(days=201),comprimee=False))
        self.assertTrue(dense['condensee'])
        self.assertLessEqual(len(dense['marques']),64)
        self.assertEqual(len(dense['lignes']),80)
        self.assertTrue(dense['suite'])


    def test_objectif_collectif_beneficiaires_explicites(self):
        menage=m.Menage.objects.create(libelle='Ménage fictif',cree_par=self.u)
        for p in [self.p,self.q]:m.Appartenance.objects.create(menage=menage,personne=p,debut=date(2026,1,1))
        e=parcours.creer(self.u,'objectifs',menage,[self.p],date(2026,1,1),'Fictif',bd6.jeton(menage),**valeurs('objectifs',titre='Objectif collectif ciblé'))
        self.activer()
        a=self.client.get(self.url)
        self.assertContains(a,'data-frise-slot="objectif-'+str(e.pk)+'"')
        b=self.client.get(reverse('dossiers:detail',args=['personne',self.q.pk]))
        self.assertNotContains(b,'Objectif collectif ciblé')
        self.assertNotContains(b,'data-frise-slot="objectif-'+str(e.pk)+'"')


class AccesObjectifsTests(TestCase):
    setUp=acteurs_tests.AccesTests.setUp
    compte=acteurs_tests.AccesTests.compte
    dossier=acteurs_tests.AccesTests.dossier

    def test_requetes_groupees_sous_controle_actif(self):
        from acteurs.models import PorteeObjet
        items=[]
        for i in range(9):
            e=m.ObjectifParcours.objects.create(personne=self.personne_a,cree_par=self.ua)
            e.beneficiaires.add(self.personne_a)
            v=m.VersionObjectif.objects.create(element=e,debut=date(2026,1,1),etat='encours',titre=f'Objectif fictif {i}',theme='Fictif',horizon='court',auteur=self.ua)
            for objet in [e,v]:PorteeObjet.objects.create(modele=objet._meta.label_lower,identifiant=str(objet.pk),service=self.sa,dossier=self.da)
            items.append({'fait':v,'url':'/fictif'})
        with CaptureQueriesContext(connection) as petit:frises_objectifs.charger(self.ua,items[:1],'personne',self.personne_a,date(2026,10,29),lambda *a:'/fictif')
        with CaptureQueriesContext(connection) as grand:frises_objectifs.charger(self.ua,items,'personne',self.personne_a,date(2026,10,29),lambda *a:'/fictif')
        self.assertLessEqual(len(grand),len(petit)+2)
        self.assertTrue(all(i.get('frise_objectif') for i in items))

    def test_version_hors_service_et_retrait_de_droit(self):
        from acteurs.models import PorteeObjet
        e=m.ObjectifParcours.objects.create(personne=self.personne_a,cree_par=self.ua)
        e.beneficiaires.add(self.personne_a)
        PorteeObjet.objects.create(modele=e._meta.label_lower,identifiant=str(e.pk),service=self.sa,dossier=self.da)
        public=m.VersionObjectif.objects.create(element=e,debut=date(2026,2,1),etat='encours',titre='Objectif visible fictif',theme='Fictif',horizon='court',auteur=self.ua)
        prive=m.VersionObjectif.objects.create(element=e,debut=date(2026,1,1),fin=date(2026,2,1),etat='suspendu',titre='Version autre service réservée',theme='Fictif',horizon='court',auteur=self.ub)
        PorteeObjet.objects.create(modele=public._meta.label_lower,identifiant=str(public.pk),service=self.sa,dossier=self.da)
        PorteeObjet.objects.create(modele=prive._meta.label_lower,identifiant=str(prive.pk),service=self.sb,dossier=self.db)
        # Les droits de modèles seuls ne court-circuitent pas les portées SQL.
        noms=['view_objectifparcours','view_versionobjectif','view_revisionobjectif']
        self.ua.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes',codename__in=noms))
        self.ua=type(self.ua).objects.get(pk=self.ua.pk)
        item={'fait':public,'url':'/fictif'}
        frises_objectifs.charger(self.ua,[item],'personne',self.personne_a,date(2026,10,29),lambda *a:'/fictif')
        self.assertIn('frise_objectif',item)
        self.assertEqual([l['fait'].pk for l in item['frise_objectif']['lignes']],[public.pk])
        self.assertEqual(item['frise_objectif']['debut'],date(2026,2,1))
        self.assertNotIn('Version autre service réservée',str(item.get('frise_objectif')))
        from acteurs.models import Habilitation
        from django.utils import timezone
        Habilitation.objects.filter(compte=self.ua).update(revoque_le=timezone.now())
        self.ua=type(self.ua).objects.get(pk=self.ua.pk)
        frises_objectifs.charger(self.ua,[item],'personne',self.personne_a,date(2026,10,29),lambda *a:'/fictif')
        self.assertNotIn('frise_objectif',item)
