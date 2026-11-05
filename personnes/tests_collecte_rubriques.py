from datetime import date
from django.test import TestCase
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from acteurs.collecte import profil, verifier
from acteurs.contexte import perimetre
from acteurs import services as organisation
from acteurs.vues_collecte import CollecteForm
from . import tests_collectifs as base, models as m, collectifs as c, collecte, bd6
from .tests_hebergement import Donnees

class CollecteRubriquesTests(Donnees,TestCase):
    setUp=base.CollectifsTests.setUp
    declarer=base.CollectifsTests.declarer
    def politique(self,nom='menage'):
        self.service.collecte_rubriques=profil(nom);self.service.save(update_fields=['collecte_rubriques'])
    def test_schema_et_scopes_distincts(self):
        r=profil('menage');verifier(r,self.service.profil_collectif['categories'])
        r['protections']['portee']='menage'
        with self.assertRaises(ValidationError):verifier(r)
    def test_refus_metier_et_population_datee(self):
        self.p.date_naissance=date(2008,1,11);self.p.precision_naissance="exacte";self.p.save()
        self.politique('adultes')
        with perimetre(self.u,self.service):
            self.assertFalse(collecte.concerne(self.p,{'portee':'personne','population':'adultes'},date(2026,1,10),self.a))
            self.assertTrue(collecte.concerne(self.p,{'portee':'personne','population':'adultes'},date(2026,1,11),self.a))
            with self.assertRaises(PermissionDenied):bd6.renseigner(self.u,self.p,'emploi','sans_emploi',date(2026,1,10),'',bd6.jeton(self.p))
        self.assertFalse(m.SituationPersonnelle.objects.exists())
    def test_menage_n_est_pas_une_valeur_personnelle(self):
        self.politique()
        with perimetre(self.u,self.service):
            cfg=c.profil(self.a)
            self.assertIn('revenu',cfg['rubriques'])
            with self.assertRaises(PermissionDenied):collecte.exiger(self.p,'ressources',date(2026,1,10),self.a)
        self.assertFalse(m.RessourcePersonnelle.objects.exists())
    def test_presentation_et_reperes_excluent_non_demande(self):
        self.politique()
        self.client.force_login(self.u)
        page=self.client.get(reverse('dossiers:prise',args=['menage',self.m.pk,self.a.pk]))
        self.assertEqual(page.status_code,200)
        groupes=page.context['condition_personnes'][0]['groupes']
        self.assertNotIn('ressources',[g['code'] for g in groupes])
        self.assertLess(page.context['condition_reperes']['total'],18)
    def test_formulaire_hors_collecte_refuse_meme_en_get(self):
        self.politique();self.client.force_login(self.u)
        url=reverse('dossiers:fait_a_nouveau',args=[self.p.pk,'ressources'])
        self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.post(url,{}).status_code,403)
    def test_formulaire_configuration_valide_sans_modifier_prestations(self):
        self.politique()
        d={'attendu':organisation.jeton(self.service),'profil':'detail'}
        for code,r in profil('detail').items():
            for cle,v in r.items():d[code+'_'+cle]=v
            d[code+'_active']='on'
        f=CollecteForm(d,service=self.service)
        self.assertTrue(f.is_valid(),f.errors)
        self.assertEqual(f.cleaned_data['regles'],profil('detail'))

    def test_composition_configurable_sans_changer_les_prestations_individuelles(self):
        from django.contrib.auth.models import Permission

        self.service.profil_collectif = {}
        self.service.save(update_fields=['profil_collectif'])
        self.u.user_permissions.add(Permission.objects.get(
            content_type__app_label='acteurs', codename='gerer_organisation',
        ))
        self.client.force_login(self.u)
        url = reverse('acteurs:composition', args=[self.service.pk])
        page = self.client.get(reverse('acteurs:service', args=[self.service.pk]))
        self.assertContains(page, url)
        form = self.client.get(url).context['form']
        self.assertEqual(form.initial['identification'], 'tous')
        donnees = {
            nom: form.initial[nom]
            for nom, champ in form.fields.items()
            if not champ.disabled and form.initial.get(nom) is not None
        }
        donnees['identification'] = 'adultes'
        self.assertEqual(self.client.post(url, donnees).status_code, 302)
        self.service.refresh_from_db()
        regles = self.service.profil_collectif
        self.assertEqual(regles['identification'], 'adultes')
        self.assertEqual(regles['hebergement'], 'individuel')
        self.assertEqual(regles['restauration'], 'individuel')
        self.assertIn('transport', regles['aides'])
        self.assertEqual(regles['rubriques'], [])

    def test_deux_portees_ne_copient_pas_et_histoire_reste_lisible(self):
        # Un fait personnel antérieur reste présent après désactivation.
        from . import coordonnees
        coordonnees.renseigner(self.u,self.p,date(2026,1,1),'',bd6.jeton(self.p),**{k: '0102030405' if k=='telephone' else '' for k in coordonnees.CHAMPS})
        self.politique()
        self.client.force_login(self.u)
        page=self.client.get(reverse('dossiers:prise',args=['menage',self.m.pk,self.a.pk]))
        self.assertContains(page,'0102030405')
        groupe=next(g for g in page.context['condition_personnes'][0]['groupes'] if g['code']=='coordonnees')
        self.assertTrue(groupe['hors_collecte'])
        self.assertEqual(groupe['fiches'][0]['corriger'],'')
        self.assertEqual(self.comp.revenu,1500)
        self.assertEqual(m.CoordonneesPersonnelles.objects.count(),1)

    def test_service_different_conserve_sa_politique(self):
        from acteurs.models import Service
        self.politique()
        autre=Service.objects.create(etablissement=self.service.etablissement,libelle='Autre service',collecte_rubriques=profil('detail'))
        with perimetre(self.u,self.service):
            with self.assertRaises(PermissionDenied):collecte.exiger(self.p,'ressources',date(2026,1,10))
        with perimetre(self.u,autre):collecte.exiger(self.p,'ressources',date(2026,1,10))

    def test_configuration_ne_donne_pas_de_droits(self):
        self.client.force_login(self.u)
        url=reverse('acteurs:collecte',args=[self.service.pk])
        self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.post(url,{'appliquer_profil':'1','profil':'menage'}).status_code,403)

    def test_regle_reference_suit_la_composition_datee(self):
        self.politique()
        autre=m.Personne.objects.create(designation='Autre référence fictive',cree_par=self.u)
        m.Appartenance.objects.create(menage=self.m,personne=autre,debut=date(2026,1,1))
        self.a.beneficiaires.add(autre)
        self.declarer(debut=date(2026,1,5),reference=autre,identifies=[autre])
        with perimetre(self.u,self.service):
            collecte.exiger(self.p,'emploi',date(2026,1,4),self.a)
            with self.assertRaises(PermissionDenied):collecte.exiger(self.p,'emploi',date(2026,1,5),self.a)
            collecte.exiger(autre,'emploi',date(2026,1,5),self.a)
