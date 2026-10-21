from datetime import date
from io import StringIO
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import sleep
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connections, close_old_connections, OperationalError
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from .models import Personne, Sejour, Affectation, Absence, OperationHebergement
from . import suivi, hebergement as h


class Donnees:
    def preparer(self):
        self.u=get_user_model().objects.create_user('hebergement-fictif')
        call_command('autoriser_chrs3',self.u.username,stdout=StringIO())
        self.u=get_user_model().objects.get(pk=self.u.pk)
        self.p=Personne.objects.create(designation='Personne fictive',cree_par=self.u)
        self.m=suivi.creer_menage(self.u,'Ménage fictif',[self.p],date(2026,1,1))
        self.a=suivi.ouvrir(self.u,self.m,[self.p],date(2026,1,1))
        self.accord=h.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,3,1))
        self.s=h.admettre(self.u,self.accord,[self.p],date(2026,1,3))
        self.lieu=h.creer_lieu(self.u,'Chambre fictive')


class HebergementTests(Donnees,TestCase):
    def setUp(self): self.preparer()

    def test_deux_affectations_absence_et_sortie(self):
        a=h.ajouter_periode(self.u,self.s,date(2026,1,3),None,self.lieu)
        h.terminer_periode(self.u,a,date(2026,1,10))
        partenaire=h.creer_lieu(self.u,'Appartement fictif','Partenaire extérieur fictif')
        h.ajouter_periode(self.u,self.s,date(2026,1,10),None,partenaire)
        absence=h.ajouter_periode(self.u,self.s,date(2026,1,12),None,absence=True)
        self.s.refresh_from_db(); self.assertIsNone(self.s.fin)
        h.sortir(self.u,self.s,date(2026,1,20))
        self.s.refresh_from_db();absence.refresh_from_db()
        self.assertEqual(self.s.fin,date(2026,1,20))
        self.assertEqual(absence.fin,self.s.fin)
        self.assertEqual(list(self.s.affectations.values_list('fin',flat=True)),[date(2026,1,10),date(2026,1,20)])
        self.assertEqual(self.s.beneficiaires.get(),self.p)
        self.assertEqual(OperationHebergement.objects.filter(action='Sortie effective').count(),1)

    def test_refus_chevauchement_et_hors_sejour(self):
        h.ajouter_periode(self.u,self.s,date(2026,1,3),date(2026,1,10),self.lieu)
        for debut,fin in [(date(2026,1,2),date(2026,1,5)),(date(2026,1,4),None),(date(2026,1,10),date(2026,1,10)),(date(2026,3,1),None)]:
            with self.assertRaises(ValidationError): h.ajouter_periode(self.u,self.s,debut,fin,self.lieu)
        self.assertEqual(Affectation.objects.count(),1)
        h.sortir(self.u,self.s,date(2026,1,12))
        with self.assertRaises(ValidationError):h.ajouter_periode(self.u,self.s,date(2026,1,10),None,self.lieu)

    def test_sortie_rollback_et_cloture_suivi(self):
        h.ajouter_periode(self.u,self.s,date(2026,1,3),None,self.lieu)
        h.ajouter_periode(self.u,self.s,date(2026,1,12),date(2026,1,15),absence=True)
        with self.assertRaises(ValidationError):h.sortir(self.u,self.s,date(2026,1,10))
        self.assertIsNone(Affectation.objects.get().fin)
        with self.assertRaises(ValidationError):suivi.clore(self.u,self.a,date(2026,2,1))
        h.sortir(self.u,self.s,date(2026,1,20))
        suivi.clore(self.u,self.a,date(2026,2,1))

    def test_parcours_http_et_droits(self):
        self.client.force_login(self.u)
        self.assertEqual(self.client.post(reverse('suivi:affecter',args=[self.s.pk]),{'debut':'2026-01-03','fin':'','lieu':self.lieu.pk}).status_code,302)
        self.assertContains(self.client.get(reverse('suivi:accord_hebergement',args=[self.accord.pk])),'Chambre fictive')
        self.assertEqual(self.client.post(reverse('suivi:sortir',args=[self.s.pk]),{'fin':'2026-01-20'}).status_code,302)
        nu=get_user_model().objects.create_user('sans-hebergement')
        self.client.force_login(nu)
        for cible in [reverse('suivi:accorder_hebergement',args=[self.a.pk]),reverse('suivi:accord_hebergement',args=[self.accord.pk]),reverse('suivi:affecter',args=[self.s.pk]),reverse('suivi:absence',args=[self.s.pk]),reverse('suivi:sortir',args=[self.s.pk]),reverse('suivi:creer_lieu')]:
            self.assertEqual(self.client.get(cible).status_code,403)

    def test_admission_et_beneficiaires(self):
        autre=Personne.objects.create(designation='Autre fictif',cree_par=self.u)
        with self.assertRaises(ValidationError):h.admettre(self.u,self.accord,[autre],date(2026,1,3))
        with self.assertRaises(ValidationError):h.admettre(self.u,self.accord,[self.p],date(2026,3,1))
        with self.assertRaises(ValidationError):h.accorder(self.u,self.a,[],date(2026,1,1),None)
        self.assertEqual(Sejour.objects.count(),1)


class ConcurrenceHebergement(Donnees,TransactionTestCase):
    def test_affectations_concurrentes_ne_se_chevauchent_pas(self):
        self.preparer()
        depart=Barrier(2)
        def essayer(_):
            close_old_connections()
            try:
                u=get_user_model().objects.get(pk=self.u.pk)
                # Charger les droits avant le départ des transactions métier.
                u.get_all_permissions()
                depart.wait(10)
                # SQLite peut refuser les deux écritures simultanées avec
                # « database table is locked ». Rejouer uniquement ce conflit
                # transitoire, après rollback de la transaction métier.
                for tentative in range(6):
                    try:
                        h.ajouter_periode(u,self.s,date(2026,1,3),None,self.lieu)
                        return (True, None)
                    except ValidationError as erreur:
                        return (False, f"ValidationError: {erreur}")
                    except OperationalError as erreur:
                        if connections['default'].vendor != 'sqlite' or 'locked' not in str(erreur).lower() or tentative == 5:
                            return (False, f"OperationalError: {erreur}")
                        sleep(0.01 * (tentative + 1))
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            tentatives = list(pool.map(essayer, range(2)))
        resultats = [reussite for reussite, _ in tentatives]
        self.assertEqual(sum(resultats), 1, f"Échecs concurrents : {tentatives}")
        self.assertEqual(Affectation.objects.count(),1)
        self.assertEqual(OperationHebergement.objects.filter(action='Affectation enregistrée').count(),1)


class AdmissionHttpTests(Donnees, TestCase):
    def test_admission_et_accord(self):
        self.preparer()
        self.client.force_login(self.u)
        reponse=self.client.post(reverse('suivi:admettre',args=[self.accord.pk]),{'beneficiaires':[self.p.pk],'debut':'2026-01-05'})
        self.assertEqual(reponse.status_code,302)
        self.assertEqual(Sejour.objects.count(),2)
        reponse=self.client.post(reverse('suivi:accorder_hebergement',args=[self.a.pk]),{'beneficiaires':[self.p.pk],'debut':'2026-01-01','fin':'2026-03-01'})
        self.assertEqual(reponse.status_code,302)
