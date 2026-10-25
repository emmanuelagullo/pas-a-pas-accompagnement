"""Arrivées erronées : conserver les preuves et retirer seulement les faits actifs."""
from datetime import date
from io import StringIO
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase
from django.urls import reverse
from . import models as m, suivi, hebergement as h, annulations_arrivees as s, accords, continuite_hebergement as ch

D=date(2026,1,1)
class ArriveesErronees(TestCase):
    def setUp(self):
        self.u=get_user_model().objects.create_user('arrivees-fictives')
        for commande in ('autoriser_chrs7','autoriser_solenne','autoriser_bd3'):call_command(commande,self.u.username,stdout=StringIO())
        self.p=m.Personne.objects.create(designation='Personne fictive I',cree_par=self.u)
        self.p2=m.Personne.objects.create(designation='Autre personne fictive I',cree_par=self.u)
        self.m=suivi.creer_menage(self.u,'Ménage fictif I',[self.p,self.p2],D)
        self.a=suivi.ouvrir(self.u,self.m,[self.p,self.p2],D)
        self.ac=h.accorder(self.u,self.a,[self.p,self.p2],D,None)
        self.s=h.admettre(self.u,self.ac,[self.p],D)
        self.l=h.creer_lieu(self.u,'Chambre fictive I')
        self.per=h.ajouter_periode(self.u,self.s,D,None,self.l)
        self.client.force_login(self.u)
    def annuler(self,**kw):return s.annuler(self.u,self.s,s.jeton(self.s),'Erreur de cible fictive',**kw)
    def test_conservation_et_compteurs_actifs_distincts(self):
        j=self.annuler();self.s.refresh_from_db()
        self.assertIsNotNone(self.s.annule_le);self.assertIsNone(self.s.fin)
        self.assertEqual(m.Sejour.objects.count(),1);self.assertEqual(m.Sejour.objects.non_annules().count(),0)
        self.assertEqual(self.s.affectations.get().pk,self.per.pk)
        self.assertEqual(j.avant[0]['lieux'][0]['lieu_id'],self.l.pk)
        self.assertFalse(j.apres);self.assertFalse(self.ac.annule_le)
        from .continuite_hebergement import episodes
        self.assertEqual(list(episodes()),[])
    def test_rejeu_et_formulaire_perime_sans_ecriture(self):
        token=s.jeton(self.s);h.ajouter_periode(self.u,self.s,D,date(2026,1,2),absence=True)
        with self.assertRaises(ValidationError):s.annuler(self.u,self.s,token,'Erreur fictive')
        self.assertFalse(m.AnnulationArrivee.objects.exists());self.annuler()
        with self.assertRaises(ValidationError):self.annuler()
        self.assertEqual(m.AnnulationArrivee.objects.count(),1)
    def test_anciens_points_entree_refusent_les_mutations(self):
        self.annuler()
        for f in (lambda:h.sortir(self.u,self.s,date(2026,1,3)),lambda:h.terminer_periode(self.u,self.per,date(2026,1,3)),lambda:h.ajouter_periode(self.u,self.s,date(2026,1,3),None,absence=True),lambda:ch.individualiser(self.u,self.s,date(2026,1,2),'Erreur fictive','invalide')):
            with self.subTest(f=f),self.assertRaises(ValidationError):f()
        self.per.refresh_from_db();self.assertIsNone(self.per.fin)
    def test_accord_annulable_apres_retrait_et_histoire_conservee(self):
        self.annuler();self.ac.refresh_from_db();accords.annuler(self.u,self.ac,'Autorisation erronée',accords.jeton(self.ac))
        self.ac.refresh_from_db();self.assertIsNotNone(self.ac.annule_le);self.assertEqual(self.ac.sejours.count(),1)
    def test_remplacement_explicitement_individuel_sans_deplacer_les_lieux(self):
        ac=h.accorder(self.u,self.a,[self.p2],D,None)
        j=self.annuler(accord_correct=ac,beneficiaires=[self.p2])
        nouveau=ac.sejours.get();self.assertEqual(list(nouveau.beneficiaires.all()),[self.p2])
        self.assertEqual(nouveau.remplace_sejour,self.s);self.assertFalse(nouveau.affectations.exists())
        self.assertEqual(j.apres[0]['mouvements_repris'],False);self.assertTrue(self.s.affectations.exists())
    def test_reprise_expresse_et_sortie_conservee(self):
        h.sortir(self.u,self.s,date(2026,1,4));ac=h.accorder(self.u,self.a,[self.p2],D,None)
        self.annuler(accord_correct=ac,beneficiaires=[self.p2],reprendre_mouvements=True)
        nouveau=ac.sejours.get();self.assertEqual(nouveau.fin,date(2026,1,4));self.assertEqual(nouveau.affectations.get().lieu,self.l)
    def test_echec_remplacement_annule_toute_la_transaction(self):
        ac=h.accorder(self.u,self.a,[self.p2],date(2026,2,1),None)
        with self.assertRaises(ValidationError):self.annuler(accord_correct=ac,beneficiaires=[self.p2])
        self.s.refresh_from_db();self.assertIsNone(self.s.annule_le);self.assertFalse(ac.sejours.exists());self.assertFalse(m.AnnulationArrivee.objects.exists())
    def test_reprise_ouverte_refuse_prise_destination_close(self):
        cible=suivi.ouvrir(self.u,self.m,[self.p2],D)
        ac=h.accorder(self.u,cible,[self.p2],D,date(2026,1,4))
        m.Accompagnement.objects.filter(pk=cible.pk).update(fin=date(2026,1,4))
        with self.assertRaises(ValidationError):self.annuler(accord_correct=ac,beneficiaires=[self.p2])
        self.assertFalse(ac.sejours.exists());self.assertFalse(m.AnnulationArrivee.objects.exists())
    def test_continuations_retirees_ensemble(self):
        self.s.beneficiaires.add(self.p2)
        ch.individualiser(self.u,self.s,date(2026,1,2),'Individualisation fictive',ch.jeton(self.s))
        self.annuler();self.assertFalse(m.Sejour.objects.non_annules().exists());self.assertGreater(m.Sejour.objects.count(),1)
    def test_actualisation_ne_confirme_jamais(self):
        url=reverse('dossiers:annuler_arrivee',args=[self.s.pk])
        r=self.client.post(url,dict(attendu=s.jeton(self.s),motif='Erreur fictive',confirmer='on',action='actualiser'))
        self.assertEqual(r.status_code,200);self.assertFalse(m.AnnulationArrivee.objects.exists())
        r=self.client.post(url,dict(attendu=s.jeton(self.s),motif='Erreur fictive',confirmer='on',accord_correct='mauvais UUID'))
        self.assertEqual(r.status_code,200);self.assertFalse(m.AnnulationArrivee.objects.exists())
    def test_consultation_historique_et_refus_sans_droit(self):
        url=reverse('dossiers:annuler_arrivee',args=[self.s.pk]);self.annuler()
        self.assertContains(self.client.get(url),'Erreur de cible fictive')
        autre=get_user_model().objects.create_user('sans-droits-i');self.client.force_login(autre)
        self.assertEqual(self.client.get(url).status_code,403)
        with self.assertRaises(PermissionDenied):s.annuler(autre,self.s,s.jeton(self.s),'Erreur fictive')

    def test_lecture_activite_html_et_propositions_financieres(self):
        from . import statistiques, financements
        self.annuler()
        b=statistiques.bilan(D,date(2026,2,1))
        for k in ('personnes_avec_sejour','sejours','admissions','sorties','nuitees_theoriques','nuits_distinctes'):
            self.assertEqual(b[k],0,k)
        self.assertEqual(financements.quantites_documentees(self.u,self.ac,D,date(2026,2,1)),[])
        url=reverse('suivi:accord_hebergement',args=[self.ac.pk])
        r=self.client.get(url);self.assertContains(r,'Erreur de cible fictive')
        self.assertNotContains(r,'Enregistrer la sortie')
    def test_document_emis_bloque_sans_reecriture(self):
        from . import financements as f
        financement=f.enregistrer(self.u,self.ac,attendu=f.jeton(self.ac),motif='Calcul fictif',action='definition',lignes=[dict(phase='autorise',date=D,libelle='Nuit fictive',unite='personne-nuit',categorie='',quantite=1,prix=10,tarif=None,justification='Convention fictive')],imputations=[],emetteur=None,mentions='',debut=D,fin=None,devise='EUR',prestataire=None,prescripteur=None,facturation=None,signataire=None,reference='',source='Convention fictive')
        doc=f.emettre(self.u,self.ac,attendu=f.jeton(self.ac),modele='engagement',phase='autorise',date=D)
        contenu=doc.contenu;empreinte=doc.empreinte
        with self.assertRaises(ValidationError):self.annuler()
        self.assertFalse(m.AnnulationArrivee.objects.exists())
        f.annuler_document(self.u,self.ac,doc,f.jeton(self.ac),'Erreur de cible fictive')
        self.annuler();doc.refresh_from_db()
        self.assertEqual(doc.contenu,contenu);self.assertEqual(doc.empreinte,empreinte)
        self.assertEqual(financement.versions.count(),1)


from django.test import TransactionTestCase
class ArriveesTransactions(TransactionTestCase):
    setUp=ArriveesErronees.setUp
    annuler=ArriveesErronees.annuler
    def test_deux_confirmations_un_seul_retrait(self):
        from threading import Thread, Barrier
        from django.db import connections, OperationalError
        barriere=Barrier(2);resultats=[];erreurs=[];token=s.jeton(self.s)
        def executer():
            try:
                u=get_user_model().objects.get(pk=self.u.pk)
                u.has_perms(['personnes.annuler_sejour'])
                sejour=m.Sejour.objects.select_related('accord__accompagnement').get(pk=self.s.pk)
                barriere.wait(timeout=10)
                try:s.annuler(u,sejour,token,'Erreur fictive concurrente');resultats.append(True)
                except (ValidationError,OperationalError):resultats.append(False)
            except Exception as e:erreurs.append(repr(e))
            finally:connections.close_all()
        ts=[Thread(target=executer) for _ in range(2)]
        for t in ts:t.start()
        for t in ts:t.join(20)
        self.assertFalse(any(t.is_alive() for t in ts));self.assertFalse(erreurs,erreurs)
        self.assertEqual(sum(resultats),1,resultats);self.assertEqual(m.AnnulationArrivee.objects.count(),1)
    def test_copie_sqlite_conserve_annulation_periodes_et_reprise(self):
        import sqlite3,tempfile,json
        from contextlib import closing
        from pathlib import Path
        from django.db import connection
        if connection.vendor!='sqlite':self.skipTest('Recette SQLite')
        ac=h.accorder(self.u,self.a,[self.p2],D,None)
        self.annuler(accord_correct=ac,beneficiaires=[self.p2],reprendre_mouvements=True)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'copie.sqlite3'
            with closing(sqlite3.connect(path)) as db,db:connection.connection.backup(db)
            with closing(sqlite3.connect(path)) as db,db:
                self.assertEqual(db.execute('SELECT count(*) FROM personnes_annulationarrivee').fetchone()[0],1)
                self.assertEqual(db.execute('SELECT count(*) FROM personnes_affectation').fetchone()[0],2)
                self.assertEqual(db.execute('SELECT count(*) FROM personnes_sejour WHERE remplace_sejour_id IS NOT NULL').fetchone()[0],1)
                avant=json.loads(db.execute('SELECT avant FROM personnes_annulationarrivee').fetchone()[0]);self.assertEqual(avant[0]['id'],str(self.s.pk))
            with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
