from datetime import date
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from . import bd6, intervenants, interventions, partenaires, suivi, hebergement, corrections
from .models import Intervenant, FicheIntervenant, AffectationIntervenant, RevisionAffectationIntervenant, RevisionFicheIntervenant
from .tests_hebergement import Donnees


def valeurs(**kwargs):
    d = dict(nom='Professionnelle fictive', fonction='Travail social', organisme=None,
        telephone='+00 123 fictif', courriel='professionnel@example.invalid', fax='')
    d.update(kwargs)
    return d


class MissionsTests(Donnees, TestCase):
    def setUp(self):
        self.preparer()
        call_command('autoriser_solenne', self.u.username, stdout=StringIO())
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        self.u = get_user_model().objects.get(pk=self.u.pk)
        self.client.force_login(self.u)
        self.prof = intervenants.creer(self.u, date(2026, 1, 1), 'Source fictive', intervenants.jeton_creation(), **valeurs())

    def affecter(self, **kwargs):
        d = dict(debut=date(2026, 1, 1), fin=None, role='referent', intervenant=self.prof,
            organisme=None, source='Décision fictive', attendu=bd6.jeton(self.a))
        d.update(kwargs)
        return interventions.affecter(self.u, self.a, **d)

    def test_professionnel_distinct_des_comptes_personnes_et_contact_menage(self):
        from .models import Personne, ContactMenage
        self.affecter()
        self.assertEqual(Intervenant.objects.count(), 1)
        self.assertEqual(Personne.objects.count(), 1)
        self.assertFalse(ContactMenage.objects.exists())
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(list(interventions.a_date(self.a, date(2026, 1, 2)).values_list('intervenant_id', flat=True)), [self.prof.pk])

    def test_fiche_professionnelle_datee_rejeu_et_correction(self):
        token = intervenants.jeton_creation()
        autre = intervenants.creer(self.u, date(2026, 1, 1), 'Fictif', token, **valeurs())
        with self.assertRaises(ValidationError):
            intervenants.creer(self.u, date(2026, 1, 1), 'Fictif', token, **valeurs())
        f = intervenants.renseigner(self.u, autre, date(2026, 3, 1), 'Fictif', bd6.jeton(autre), **valeurs(fonction='Autre fonction fictive'))
        intervenants.renseigner(self.u, autre, date(2026, 2, 1), 'Document corrigé fictif', bd6.jeton(autre),
            motif='Erreur de date fictive', correction=f.pk, **valeurs(fonction='Fonction corrigée fictive'))
        self.assertEqual(intervenants.a_date([autre], date(2026, 2, 15)).get().fonction, 'Fonction corrigée fictive')
        self.assertEqual(RevisionFicheIntervenant.objects.first().action, 'correction')

    def test_co_referents_sans_cloture_implicite_et_doublon_refuse(self):
        x = self.affecter()
        with self.assertRaises(ValidationError): self.affecter()
        autre = intervenants.creer(self.u, date(2026, 1, 1), 'Fictif', intervenants.jeton_creation(), **valeurs(nom='Autre professionnel fictif'))
        self.affecter(intervenant=autre, debut=date(2026, 2, 1))
        x.refresh_from_db(); self.assertIsNone(x.fin)
        self.assertEqual(interventions.a_date(self.a, date(2026, 2, 2)).count(), 2)

    def test_fin_de_mission_distincte_correction_et_conflit(self):
        x = self.affecter(); ancien = bd6.jeton(self.a)
        self.affecter(correction=x.pk, cloture=True, fin=date(2026, 2, 1), motif='Relais fictif')
        x.refresh_from_db(); self.assertEqual(x.fin, date(2026, 2, 1))
        self.assertEqual(RevisionAffectationIntervenant.objects.first().action, 'cloture')
        with self.assertRaises(ValidationError): self.affecter(correction=x.pk, fin=date(2026, 3, 1), motif='Fictif', attendu=ancien)
        self.affecter(correction=x.pk, fin=date(2026, 1, 20), motif='Erreur de date fictive')
        self.assertEqual(RevisionAffectationIntervenant.objects.first().avant['fin'], '2026-02-01')
        self.assertEqual(RevisionAffectationIntervenant.objects.first().apres['fin'], '2026-01-20')

    def test_annulation_erreur_conserve_trace_et_autorise_remplacement(self):
        x = self.affecter()
        ancien = bd6.jeton(self.a)
        with self.assertRaises(ValidationError):
            interventions.annuler(self.u, self.a, x, '', ancien)
        interventions.annuler(self.u, self.a, x, 'Mauvaise prise fictive', bd6.jeton(self.a))
        x.refresh_from_db()
        self.assertEqual(x.annule_par, self.u)
        self.assertFalse(interventions.a_date(self.a, date(2026, 1, 2)).exists())
        self.assertEqual(RevisionAffectationIntervenant.objects.first().action, 'annulation')
        with self.assertRaises(ValidationError): self.affecter(attendu=ancien)
        with self.assertRaises(ValidationError): self.affecter(correction=x.pk, motif='Fictif')
        self.affecter()
        self.assertEqual(AffectationIntervenant.objects.count(), 2)
        self.assertEqual(interventions.a_date(self.a, date(2026, 1, 2)).count(), 1)
        self.assertContains(self.client.get(reverse('dossiers:interventions', args=[self.a.pk])), 'Mauvaise prise fictive')

    def test_annulation_http_motivee_et_droit_propre(self):
        x = self.affecter()
        url = reverse('dossiers:intervention_annuler', args=[self.a.pk, x.pk])
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        attendu = page.context['form'].fields['attendu'].initial
        self.assertEqual(self.client.post(url, {'motif':'Erreur fictive', 'attendu':attendu}).status_code, 302)
        x.refresh_from_db()
        self.assertIsNotNone(x.annule_le)
        self.u.user_permissions.remove(Permission.objects.get(codename='annuler_affectationintervenant'))
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_dates_cible_etrangere_et_rollback_journal(self):
        x = self.affecter()
        for kw in [dict(debut=date(2025, 12, 1)), dict(fin=date(9999, 1, 1)), dict(intervenant=None, organisme=None), dict(role='inconnu')]:
            with self.assertRaises(ValidationError): self.affecter(**kw)
        autre = suivi.ouvrir(self.u, self.m, [self.p], date(2026, 1, 1))
        with self.assertRaises(ValidationError):
            interventions.affecter(self.u, autre, date(2026, 1, 1), None, 'referent', self.prof, None, 'Fictif', bd6.jeton(autre), correction=x.pk, motif='Fictif')
        with patch.object(RevisionAffectationIntervenant.objects, 'create', side_effect=RuntimeError('Fictif')):
            with self.assertRaises(RuntimeError): self.affecter(role='suivi_exterieur')
        self.assertEqual(AffectationIntervenant.objects.count(), 1)

    def test_cloture_et_correction_prise_protegent_missions_datees(self):
        self.affecter(debut=date(2026, 2, 1), fin=date(2026, 3, 1))
        hebergement.sortir(self.u, self.s, date(2026, 1, 20))
        with self.assertRaises(ValidationError): suivi.clore(self.u, self.a, date(2026, 2, 15))
        with self.assertRaises(ValidationError):
            corrections.periode(self.u, self.a, date(2026, 2, 10), None, 'Fictif', corrections.jeton(self.a))
        suivi.clore(self.u, self.a, date(2026, 3, 1))
        self.a.refresh_from_db()
        self.assertFalse(interventions.a_date(self.a, date(2026, 3, 1)).exists())

    def test_mission_ouverte_bornee_par_cloture_parent_sans_reecriture(self):
        x = self.affecter()
        hebergement.sortir(self.u, self.s, date(2026, 1, 20)); suivi.clore(self.u, self.a, date(2026, 2, 1))
        self.a.refresh_from_db(); x.refresh_from_db()
        self.assertIsNone(x.fin)
        self.assertEqual(interventions.a_date(self.a, date(2026, 1, 31)).count(), 1)
        self.assertFalse(interventions.a_date(self.a, date(2026, 2, 1)).exists())

    def test_bd_csv_resume_et_legacy_non_converti(self):
        self.affecter()
        page = self.client.get(reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk]))
        self.assertContains(page, 'Professionnels et organismes')
        self.assertContains(page, 'Professionnelle fictive')
        self.assertContains(self.client.get(reverse('suivi:resume', args=[self.a.pk])), 'Professionnelle fictive')
        csv = self.client.get(reverse('dossiers:interventions', args=[self.a.pk]), {'date':'2026-01-02','format':'csv'})
        self.assertEqual(csv.status_code, 200); self.assertIn('Professionnelle fictive', csv.content.decode())
        self.assertFalse(self.a.informations.exists())

    def test_http_affectation_retour_signe_et_csrf(self):
        from urllib.parse import urlencode
        page = self.client.get(reverse('dossiers:prise', args=['menage', self.m.pk, self.a.pk]), {'q':'Fictif','sejour':self.s.pk})
        token = page.context['prise'].navigation['contexte_dossier']
        url = reverse('dossiers:intervention_nouvelle', args=[self.a.pk]) + '?' + urlencode({'contexte_dossier':token,'date':'2026-01-02'})
        form = self.client.get(url).context['form']
        data = dict(role='referent', intervenant=self.prof.pk, organisme='', debut='2026-01-01', fin='', source='Fictif', attendu=form.initial['attendu'])
        protege=Client(enforce_csrf_checks=True); protege.force_login(self.u)
        self.assertEqual(protege.post(url,data).status_code,403)
        r=self.client.post(url,data); self.assertEqual(r.status_code,302)
        self.assertIn('/prises/' + str(self.a.pk),self.client.get(r.url).context['retour'])

    def test_droits_distincts(self):
        self.u.user_permissions.remove(Permission.objects.get(codename='view_affectationintervenant'))
        self.assertEqual(self.client.get(reverse('dossiers:interventions', args=[self.a.pk])).status_code,403)
        self.assertNotContains(self.client.get(reverse('dossiers:prise', args=['menage',self.m.pk,self.a.pk])), 'Professionnels et organismes de cette prise')

    def test_annuaire_professionnel_organisme_et_coordonnees_restituees_a_date(self):
        from .tests_partenaires import valeurs as valeurs_organisme
        org=partenaires.creer(self.u,date(2026,1,1),'Fictif',partenaires.jeton_creation(),**valeurs_organisme())
        intervenants.renseigner(self.u,self.prof,date(2026,2,1),'Nouveau service fictif',bd6.jeton(self.prof),
            **valeurs(organisme=org,telephone='+00 NOUVEAU fictif'))
        self.affecter()
        avant=interventions.presentation(self.u,self.a,date(2026,1,31))[0]
        apres=interventions.presentation(self.u,self.a,date(2026,2,1))[0]
        self.assertEqual(avant.fiche_professionnelle.telephone,'+00 123 fictif')
        self.assertIsNone(avant.fiche_professionnelle.organisme)
        self.assertEqual(apres.fiche_professionnelle.organisme,org)
        url=reverse('dossiers:intervenants')
        self.assertContains(self.client.get(url,{'date':'2026-02-01','q':'Travail'}),'Professionnelle fictive')
        page=self.client.get(reverse('dossiers:intervenant',args=[self.prof.pk]),{'date':'2026-02-01'})
        self.assertContains(page,'Association fictive')
        csv=self.client.get(reverse('dossiers:interventions',args=[self.a.pk]),{'date':'2026-01-31','format':'csv'}).content.decode()
        self.assertIn('+00 123 fictif',csv); self.assertNotIn('NOUVEAU',csv)
        self.affecter(role='prescripteur',intervenant=None,organisme=org)
        page=self.client.get(reverse('dossiers:interventions',args=[self.a.pk]),{'date':'2026-02-01','role':'prescripteur'})
        self.assertEqual(len(page.context['actifs']),1)
        self.assertEqual(page.context['actifs'][0].organisme,org)


class ConcurrenceMissions(Donnees, TransactionTestCase):
    def test_copie_restauree_conserve_profils_missions_et_journaux(self):
        import sqlite3,json
        from contextlib import closing
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.db import connection
        from pas_communs.paquets import creer_sauvegarde
        from pas_a_pas_accompagnement import paquets
        if connection.vendor!='sqlite':self.skipTest('Copie locale SQLite uniquement.')
        self.preparer();call_command('autoriser_solenne',self.u.username,stdout=StringIO())
        self.u=get_user_model().objects.get(pk=self.u.pk)
        from . import propositions
        proposition=propositions.enregistrer(self.u,'ville','Ville fictive de copie',True,'Création fictive')
        propositions.enregistrer(self.u,'ville',proposition.valeur,False,'Retrait fictif',objet=proposition,attendu=propositions.jeton(proposition))
        prof=intervenants.creer(self.u,date(2026,1,1),'Fictif',intervenants.jeton_creation(),**valeurs())
        x=interventions.affecter(self.u,self.a,date(2026,1,1),None,'referent',prof,None,'Fictif',bd6.jeton(self.a))
        interventions.affecter(self.u,self.a,date(2026,1,1),date(2026,2,1),'referent',prof,None,'Fictif',bd6.jeton(self.a),correction=x.pk,cloture=True,motif='Relais fictif')
        with TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir();(source/'secret-key').write_text('cle-fictive-missions')
            with closing(sqlite3.connect(source/paquets.PROFIL.base)) as copie:connection.connection.backup(copie)
            archive=root/'missions.zip';creer_sauvegarde(source,archive,profil=paquets.PROFIL)
            preparation=paquets.verifier(archive,root,'preparation');destination=root/'restauree';paquets.installer_copie(preparation,destination)
            with closing(sqlite3.connect(destination/paquets.PROFIL.base)) as db:
                self.assertEqual(db.execute('SELECT intervenant_id,fin FROM personnes_affectationintervenant').fetchone(),(prof.pk.hex,'2026-02-01'))
                self.assertEqual(db.execute('SELECT action FROM personnes_revisionaffectationintervenant ORDER BY id').fetchall(),[('ajout',),('cloture',)])
                self.assertEqual(db.execute('SELECT nom FROM personnes_ficheintervenant').fetchone(),('Professionnelle fictive',))
                self.assertEqual(db.execute('SELECT valeur,active FROM personnes_propositionsaisie').fetchone(),('Ville fictive de copie',0))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM personnes_revisionpropositionsaisie').fetchone(),(2,))

    def test_deux_affectations_concurrentes_un_seul_fait(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections, OperationalError
        from .models import Accompagnement
        self.preparer(); call_command('autoriser_solenne',self.u.username,stdout=StringIO())
        self.u=get_user_model().objects.get(pk=self.u.pk)
        prof=intervenants.creer(self.u,date(2026,1,1),'Fictif',intervenants.jeton_creation(),**valeurs())
        token=bd6.jeton(self.a); depart=Barrier(2)
        def ecrire(_):
            close_old_connections()
            try:
                u=get_user_model().objects.get(pk=self.u.pk); u.get_all_permissions()
                a=Accompagnement.objects.select_related('menage').get(pk=self.a.pk)
                p=Intervenant.objects.get(pk=prof.pk); depart.wait(timeout=10)
                try:
                    interventions.affecter(u,a,date(2026,1,1),None,'referent',p,None,'Fictif',token)
                    return True
                except (ValidationError,OperationalError): return False
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool: r=list(pool.map(ecrire,range(2)))
        self.assertEqual(sum(r),1,r); self.assertEqual(AffectationIntervenant.objects.count(),1)
        self.assertEqual(RevisionAffectationIntervenant.objects.count(),1)
