from datetime import date
from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from django.core.exceptions import ValidationError,PermissionDenied
from django.urls import reverse
from . import tests_navigation,corrections as c, social,repas,hebergement as h
from .models import CorrectionPeriode,RevisionTexteSocial,OperationSociale


class CorrectionsTests(TestCase):
    def setUp(self):
        tests_navigation.NavigationTests.setUp(self)
        call_command('autoriser_chrs7',self.u.username,stdout=StringIO())
        self.u=type(self.u).objects.get(pk=self.u.pk)
        self.client.force_login(self.u)

    def corriger(self,objet,debut,fin,**kw):
        return c.periode(self.u,objet,debut,fin,'Erreur fictive',c.jeton(objet),**kw)

    def test_accord_preserve_distributions(self):
        accord=repas.accorder(self.u,self.a,[self.p],date(2026,1,1),date(2026,2,1),'dejeuner')
        repas.distribuer(self.u,accord,self.p,date(2026,1,5),1)
        with self.assertRaises(ValidationError):self.corriger(accord,date(2026,1,6),date(2026,2,1))
        accord.refresh_from_db();self.assertEqual(accord.debut,date(2026,1,1))
        self.assertFalse(CorrectionPeriode.objects.exists())
        self.corriger(accord,date(2026,1,2),date(2026,2,1))
        trace=CorrectionPeriode.objects.get()
        self.assertEqual(trace.ancien_debut,date(2026,1,1))
        self.assertEqual(trace.nouveau_debut,date(2026,1,2))

    def test_chevauchement_et_sortie(self):
        accord=h.accorder(self.u,self.a,[self.p],date(2026,1,1),None)
        sejour=h.admettre(self.u,accord,[self.p],date(2026,1,2))
        lieu=h.creer_lieu(self.u,'Lieu fictif')
        premiere=h.ajouter_periode(self.u,sejour,date(2026,1,2),date(2026,1,10),lieu)
        h.ajouter_periode(self.u,sejour,date(2026,1,10),date(2026,1,15),lieu)
        with self.assertRaises(ValidationError):self.corriger(premiere,date(2026,1,2),date(2026,1,11))
        with self.assertRaises(ValidationError):self.corriger(sejour,date(2026,1,3),None)
        self.corriger(premiere,date(2026,1,3),date(2026,1,10))
        h.sortir(self.u,sejour,date(2026,1,20))
        sejour.refresh_from_db()
        with self.assertRaises(ValidationError):self.corriger(sejour,date(2026,1,2),None)

    def test_source_et_dates_sociales_sans_reordonner(self):
        precedent=social.renseigner(self.u,self.a,self.p,'emploi','sans_emploi',date(2026,1,1),'Source fictive')
        valeur=social.renseigner(self.u,self.a,self.p,'emploi','emploi',date(2026,2,1),'Source fictive')
        self.corriger(valeur,date(2026,2,3),None,source='Source rectifiée')
        precedent.refresh_from_db();valeur.refresh_from_db()
        self.assertEqual(precedent.fin,date(2026,2,3))
        self.assertEqual(valeur.source,'Source rectifiée')
        self.assertEqual(CorrectionPeriode.objects.count(),2)
        with self.assertRaises(ValidationError):self.corriger(valeur,date(2026,1,1),None,source='Autre source')
        self.assertEqual(CorrectionPeriode.objects.count(),2)

    def test_texte_source_date_et_ancien_formulaire(self):
        e=social.evenement(self.u,self.a,self.p,date(2026,1,3),'Texte initial fictif','Source fictive')
        attendu=c.jeton(e)
        c.texte(self.u,e,date(2026,1,4),'Texte corrigé fictif','Erreur',attendu,source='Source corrigée')
        with self.assertRaises(ValidationError):c.texte(self.u,e,date(2026,1,5),'Texte périmé','Erreur',attendu,source='Source fictive')
        e.refresh_from_db();self.assertEqual(e.texte,'Texte corrigé fictif')
        self.assertEqual(RevisionTexteSocial.objects.get().ancien_texte,'Texte initial fictif')
        self.assertEqual(OperationSociale.objects.count(),1)

    def test_refus_dependances_de_accompagnement(self):
        social.bilan(self.u,self.a,date(2026,1,3),'Bilan fictif')
        with self.assertRaises(ValidationError):self.corriger(self.a,date(2026,1,4),None)
        self.a.refresh_from_db();self.assertEqual(self.a.debut,date(2026,1,1))

    def test_vue_et_droits_explicites(self):
        cible=reverse('suivi:corriger_saisie',args=['accompagnement',self.a.pk])
        self.assertContains(self.client.get(cible),'Précisions facultatives')
        reponse=self.client.post(cible,{'debut':'2026-01-02','fin':'','motif':'Erreur fictive','attendu':c.jeton(self.a)})
        self.assertRedirects(reponse,reverse('suivi:accompagnement',args=[self.a.pk]))
        self.assertContains(self.client.get(reverse('suivi:corrections',args=[self.a.pk])),'Erreur fictive')
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(cible).status_code,403)
        self.assertEqual(self.client.post(cible,{}).status_code,403)
        with self.assertRaises(PermissionDenied):self.corriger(self.a,date(2026,1,3),None)

    def test_journal_echappe_les_textes(self):
        b=social.bilan(self.u,self.a,date(2026,1,3),'<script>fictif</script>')
        c.texte(self.u,b,date(2026,1,4),'Texte fictif','Correction',c.jeton(b))
        reponse=self.client.get(reverse('suivi:corrections',args=[self.a.pk]))
        self.assertContains(reponse,'&lt;script&gt;fictif&lt;/script&gt;')
        self.assertNotContains(reponse,'<script>fictif</script>')

    def test_correction_evenement_simple_et_bilan_enrichi(self):
        evenement=social.evenement(self.u,self.a,self.p,date(2026,1,3),'Événement fictif','Source fictive')
        bilan=social.bilan(self.u,self.a,date(2026,1,3),'Bilan fictif')
        page=self.client.get(reverse('suivi:corriger_saisie',args=['evenementsocial',evenement.pk]))
        self.assertEqual(page.status_code,200)
        self.assertContains(page,'name="texte"')
        self.assertNotContains(page,'data-texte-riche="1"')
        self.assertNotContains(page,'name="texte_document"')
        page=self.client.get(reverse('suivi:corriger_saisie',args=['bilansocial',bilan.pk]))
        self.assertEqual(page.status_code,200)
        self.assertContains(page,'data-texte-riche="1"')
        self.assertContains(page,'name="texte_document"')


from django.test import TransactionTestCase


class CorrectionConcurrente(TransactionTestCase):
    def test_formulaires_concurrents_un_seul_avant_apres(self):
        CorrectionsTests.setUp(self)
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections,close_old_connections,OperationalError
        depart=Barrier(2)
        attendu=c.jeton(self.a)
        def ecrire(jour):
            close_old_connections()
            try:
                acteur=type(self.u).objects.get(pk=self.u.pk)
                acteur.get_all_permissions()
                depart.wait(10)
                try:
                    c.periode(acteur,self.a,date(2026,1,jour),None,'Correction concurrente fictive',attendu)
                    return True
                except (ValidationError,OperationalError):return False
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:resultats=list(pool.map(ecrire,[2,3]))
        self.assertEqual(sum(resultats),1)
        self.assertEqual(CorrectionPeriode.objects.count(),1)
