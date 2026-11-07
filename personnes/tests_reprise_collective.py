"""Contrats COL4b : sous-groupes, offres, calculs, historique et droits."""
from datetime import date,timedelta
from decimal import Decimal
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError,PermissionDenied
from django.urls import reverse
from acteurs.models import OffrePrestataire,TarifOffre
from . import models as m,collectifs as c
from .forms_collectifs import PrestationForm
from .tests_collectifs import CollectifsTests

class RepriseCollectiveTests(CollectifsTests):
    # The inherited scenarios also run against the new models and views.
    def offre(self,midi=True,soir=True):
        lieu=m.Partenaire.objects.create(libelle='Table fictive',cree_par=self.u)
        offre=OffrePrestataire.objects.create(libelle='Table',lieu=lieu,nature='restauration',dejeuner=midi,diner=soir)
        offre.services.add(self.service)
        self.service.catalogue_prestations=True;self.service.save()
        self.a=m.Accompagnement.objects.select_related('menage').get(pk=self.a.pk)
        return offre

    def donnees(self,**kw):
        d={'debut':'2026-01-10','fin_prevue':'2026-01-11','dejeuner':'on','diner':'on','premier':'dejeuner','dernier':'diner','devise':'EUR','attendu':c.jeton(self.a)}
        for code,n in c.effectifs(self.comp).items():d.update({'couverts_'+code:str(n),'prix_'+code:'5'})
        d.update(kw);return d

    def test_nouvelle_prise_pour_un_sejour_collectif(self):
        self.a.fin = date(2026, 1, 5)
        self.a.save(update_fields=['fin'])
        self.a.refresh_from_db()
        self.client.force_login(self.u)
        url = reverse('dossiers:collectif_action', args=['prise', self.a.pk, 'creation']) + '?nature=hebergement'
        donnees = {'debut': '2026-01-10', 'fin_prevue': '2026-01-11', 'devise': 'EUR', 'attendu': c.jeton(self.a)}
        apercu = self.client.post(url, donnees, headers={'X-Verifier-Prestation': '1'})
        self.assertIn('Créer une prise en charge pour ce séjour', apercu.json()['commandes'])
        self.assertEqual(m.Accompagnement.objects.count(), 1)
        page = self.client.post(url, {**donnees, 'nouvelle_prise': '1'})
        self.assertEqual(page.status_code, 302, page.context['formctx']['form'].errors if page.context else '')
        prestation = m.PrestationCollective.objects.get()
        self.assertNotEqual(prestation.accompagnement_id, self.a.pk)
        self.assertEqual(prestation.courante.composition.accompagnement_id, prestation.accompagnement_id)
        self.assertEqual(prestation.courante.composition.complements, self.comp.complements)
        self.assertEqual(m.Accompagnement.objects.get(pk=self.a.pk).fin, date(2026, 1, 5))

    def test_mono_repas_sans_bornes_transmises(self):
        d=self.donnees();d.pop('diner');d.pop('premier');d.pop('dernier')
        f=PrestationForm(d,prise=self.a,nature='restauration',comp=self.comp,acteur=self.u)
        self.assertTrue(f.is_valid(),f.errors)
        self.assertEqual((f.cleaned_data['premier'],f.cleaned_data['dernier']),('dejeuner','dejeuner'))

    def test_tarif_diner_et_prix_inconnus(self):
        p=self.restaurer();v=p.courante
        c.modifier(self.u,p,c.jeton(p),'correction',couverts=[{'categorie':'adulte','nombre':2,'prix':Decimal('8'),'prix_diner':Decimal('10')}])
        r=c.bilan(p.courante,date(2026,1,10),date(2026,1,14))
        self.assertEqual(r['cout'],Decimal('108'))
        self.assertEqual(v.couverts.get(categorie='adulte').prix,Decimal('8'))

    def test_groupe_anonyme_hors_effectif_refuse(self):
        with self.assertRaises(ValidationError):c.creer(self.u,self.a,'hebergement',self.comp,c.jeton(self.a),[],selection=[],selection_complements={'enfant':3},debut=date(2026,1,10))
        self.assertFalse(m.PrestationCollective.objects.exists())

    def test_offre_midi_seul_refuse_diner_et_autre_service(self):
        offre=self.offre(soir=False)
        with self.assertRaises(ValidationError):self.restaurer(offre=offre)
        p=self.restaurer(offre=offre,diner=False,premier='dejeuner',dernier='dejeuner')
        self.assertEqual(p.courante.libelle_offre,'Table')
        offre.services.clear()
        with self.assertRaises(PermissionDenied):self.restaurer(offre=offre,diner=False,premier='dejeuner',dernier='dejeuner')

    def test_retrait_offre_conserve_histoire_et_corrections(self):
        offre=self.offre();p=self.restaurer(offre=offre)
        offre.actif=False;offre.libelle='Nouveau nom';offre.save()
        c.modifier(self.u,p,c.jeton(p),'prolongation',fin_prevue=date(2026,1,15))
        self.assertEqual(p.courante.libelle_offre,'Table')
        with self.assertRaises(PermissionDenied):self.restaurer(offre=offre)

    def test_famille_desactivee_refuse_creation(self):
        self.service.profil_collectif['prestations']=['hebergement'];self.service.save()
        self.a=m.Accompagnement.objects.select_related('menage').get(pk=self.a.pk)
        with self.assertRaises(PermissionDenied):self.restaurer()

    def test_apercu_json_et_html_ne_creent_rien(self):
        self.client.force_login(self.u)
        url=reverse('dossiers:collectif_action',args=['prise',self.a.pk,'creation'])+'?nature=restauration'
        r=self.client.post(url+'&apercu=1',self.donnees())
        self.assertEqual(r.status_code,200);self.assertIn('80.00 EUR',r.json()['message'])
        r=self.client.post(url,self.donnees(calculer='1'))
        self.assertContains(r,'80.00 EUR');self.assertContains(r,'data-prestation-form')
        self.assertFalse(m.PrestationCollective.objects.exists())

    def test_tarifs_offre_projection_explicite_et_datee(self):
        offre=self.offre()
        tarif=m.TarifPrestation.objects.create(libelle='Adulte',cree_par=self.u)
        for i,(jour,prix) in enumerate([(date(2026,1,1),8),(date(2026,2,1),9)],1):
            m.VersionTarif.objects.create(tarif=tarif,version=i,debut=jour,libelle='Adulte',unite='repas',categorie='ancien libellé',montant=prix,devise='EUR',prestataire=offre.lieu,source='Catalogue fictif',action='definition' if i==1 else 'changement',auteur=self.u)
        TarifOffre.objects.create(offre=offre,categorie='adulte',libelle='Adulte',tarif=tarif)
        self.assertEqual(c.tarifs_offre(self.u,offre,date(2026,1,10),'EUR'),{})
        self.u.user_permissions.add(Permission.objects.get(content_type__app_label='acteurs',codename='view_tarifoffre'))
        self.u=type(self.u).objects.get(pk=self.u.pk)
        self.assertEqual(c.tarifs_offre(self.u,offre,date(2026,1,10),'EUR')[('adulte','commun')].montant,8)
        self.assertEqual(c.tarifs_offre(self.u,offre,date(2026,2,10),'EUR')[('adulte','commun')].montant,9)

    def test_parametrage_et_prix_diner_versionnes(self):
        self.u.user_permissions.add(Permission.objects.get(content_type__app_label='acteurs',codename='gerer_organisation'))
        self.u=type(self.u).objects.get(pk=self.u.pk);self.client.force_login(self.u)
        r=self.client.get(reverse('acteurs:organisation'));self.assertContains(r,'id="parametrage"');self.assertContains(r,'Prestataires')
        offre=self.offre()
        from acteurs import services
        url=reverse('acteurs:prestataire_prix',args=[offre.pk])
        r=self.client.post(url,{'attendu':services.jeton(offre),'categorie':'adulte','debut':'2026-01-01','prix':'8','prix_diner':'10','devise':'EUR'})
        self.assertEqual(r.status_code,302)
        self.assertEqual(offre.tarifs.count(),2)
        offre.refresh_from_db()
        r=self.client.post(url,{'attendu':services.jeton(offre),'categorie':'adulte','debut':'2026-02-01','prix':'9','prix_diner':'','devise':'EUR'})
        self.assertEqual(r.status_code,302)
        self.assertEqual(offre.tarifs.get(repas='diner').tarif.versions.count(),2)
        self.assertFalse(offre.tarifs.get(repas='diner').tarif.versions.first().actif)

    def test_correction_conserve_reference_tarif_historique(self):
        offre=self.offre()
        self.u.user_permissions.add(Permission.objects.get(content_type__app_label='acteurs',codename='view_tarifoffre'))
        self.u=type(self.u).objects.get(pk=self.u.pk)
        tarif=m.TarifPrestation.objects.create(libelle='Adulte',cree_par=self.u)
        t=m.VersionTarif.objects.create(tarif=tarif,version=1,debut=date(2026,1,1),libelle='Adulte',unite='repas',categorie='Adulte',montant=8,devise='EUR',prestataire=offre.lieu,source='Catalogue',action='definition',auteur=self.u)
        TarifOffre.objects.create(offre=offre,categorie='adulte',libelle='Adulte',tarif=tarif)
        p=c.creer(self.u,self.a,'restauration',self.comp,c.jeton(self.a),[{'categorie':'adulte','nombre':2,'prix':Decimal('8'),'tarif':t}],offre=offre,debut=date(2026,1,10),fin_prevue=date(2026,1,11))
        m.VersionTarif.objects.create(tarif=tarif,version=2,debut=date(2026,1,1),libelle='Adulte',unite='repas',categorie='Adulte',montant=9,devise='EUR',prestataire=offre.lieu,source='Catalogue',action='correction',auteur=self.u)
        form=PrestationForm(self.donnees(offre=str(offre.pk),prix_adulte='8'),prise=self.a,nature='restauration',comp=self.comp,acteur=self.u,prestation=p)
        self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.cleaned_data['couverts'][0]['tarif'],t)


    def test_liste_sans_barre_actions_et_depart_dans_editeur(self):
        p=self.restaurer();self.client.force_login(self.u)
        url=reverse('dossiers:prise',args=['menage',self.m.pk,self.a.pk])
        page=self.client.get(url)
        _, section, suite = page.content.decode().partition('id="repas" data-dossier-boite="repas"')
        self.assertTrue(section)
        self.assertNotIn('Enregistrer le départ', suite.split('</section>', 1)[0])
        self.assertNotContains(page,'>Corriger</a>')
        self.assertContains(page,'data-prestation-carte="commun:')
        operation=reverse('dossiers:collectif_action',args=['prise',self.a.pk,'correction'])+'?pk='+str(p.pk)
        page=self.client.get(url,{'prestation':'commun:'+str(p.pk),'operation':operation})
        self.assertContains(page,'Modifier la période de repas')
        self.assertContains(page,'name="fin"')

    def test_fin_constatee_depuis_editeur_unique(self):
        p=self.restaurer();self.client.force_login(self.u)
        url=reverse('dossiers:collectif_action',args=['prise',self.a.pk,'correction'])+'?pk='+str(p.pk)
        r=self.client.post(url,self.donnees(attendu=c.jeton(p),fin='2026-01-11'))
        self.assertEqual(r.status_code,302)
        self.assertEqual(p.courante.fin,date(2026,1,11))
