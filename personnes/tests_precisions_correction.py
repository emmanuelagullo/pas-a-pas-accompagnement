"""Même règle pour les corrections ordinaires, sans affaiblir les autres contrôles."""
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from . import models as m, bd6, suivi, social, corrections, transmissions, financements
from . import pieces_dossier, precisions_correction as precision
from . import tests_meta_d as finance_tests


class PrecisionsCorrectionTests(TestCase):
    def setUp(self):
        finance_tests.MetaDTests.setUp(self)
        self.u.is_superuser=True
        self.u.save(update_fields=['is_superuser'])
        self.client.force_login(self.u)
    tarif=finance_tests.MetaDTests.tarif
    ligne=finance_tests.MetaDTests.ligne
    imputation=finance_tests.MetaDTests.imputation
    enregistrer=finance_tests.MetaDTests.enregistrer
    nouvelle=finance_tests.MetaDTests.nouvelle

    def test_dates_et_textes_rectifies_sans_precision_avec_histoire_et_conflits(self):
        a=suivi.ouvrir(self.u,self.m,[self.p],date(2026,1,1))
        token=corrections.jeton(a)
        corrections.periode(self.u,a,date(2026,1,2),None,'',token)
        journal=m.CorrectionPeriode.objects.get(accompagnement=a)
        self.assertEqual(journal.motif,'')
        with self.assertRaises(ValidationError):corrections.periode(self.u,a,date(2026,1,3),None,'',token)
        e=social.evenement(self.u,a,self.p,date(2026,1,4),'Fait fictif','Source fictive')
        corrections.texte(self.u,e,date(2026,1,5),'Fait rectifié fictif','',corrections.jeton(e),'Source fictive')
        e.refresh_from_db()
        self.assertEqual(e.date_effet,date(2026,1,5))
        self.assertEqual(m.RevisionTexteSocial.objects.get(evenement=e).motif,'')
        self.assertEqual(m.RevisionTexteSocial.objects.get(evenement=e).ancien_texte,'Fait fictif')

    def test_commentaire_et_note_conservent_leurs_versions_sans_precision(self):
        bd6.commenter(self.u,self.m,'Premier commentaire fictif','',bd6.jeton(self.m))
        bd6.commenter(self.u,self.m,'Commentaire rectifié fictif','',bd6.jeton(self.m))
        self.assertEqual(m.CommentaireDossier.objects.filter(menage=self.m).count(),2)
        note=transmissions.noter(self.u,'Note fictive',personne=self.p)
        attendu=transmissions.jeton(note)
        transmissions.rectifier(self.u,note,'Note rectifiée fictive','',etat_attendu=attendu)
        self.assertEqual(m.RevisionContribution.objects.get(note=note).motif,'')
        with self.assertRaises(ValidationError):transmissions.rectifier(self.u,note,'Autre','',etat_attendu=attendu)

    def test_tarif_correction_sans_motif_decision_toujours_justifiee(self):
        tarif=self.tarif();v=tarif.versions.first()
        valeurs={c:getattr(v,c) for c in financements.TARIF};valeurs['montant']=Decimal('27')
        token=bd6.jeton(tarif)
        financements.definir_tarif(self.u,token,'',tarif=tarif,action='correction',**valeurs)
        tarif.refresh_from_db()
        self.assertEqual(tarif.versions.first().motif,'')
        self.assertEqual(v.montant,Decimal('25.1250'))
        with self.assertRaises(ValidationError):financements.definir_tarif(self.u,token,'',tarif=tarif,action='correction',**valeurs)
        valeurs['debut']=date(2026,1,6)
        with self.assertRaises(ValidationError):financements.definir_tarif(self.u,bd6.jeton(tarif),'',tarif=tarif,action='changement',**valeurs)

    def test_calcul_correction_sans_precision_et_ancienne_version_intacte(self):
        f=self.enregistrer();v=f.versions.first()
        self.nouvelle(motif='',reference='Correction fictive')
        f.refresh_from_db()
        self.assertEqual(f.versions.count(),2)
        self.assertEqual(f.versions.first().motif,'')
        v.refresh_from_db();self.assertEqual(v.reference,'FICTIF')

    def test_http_operation_determine_exigence_meme_sans_javascript(self):
        tarif=self.tarif();v=tarif.versions.first()
        url=reverse('dossiers:tarif',args=[tarif.pk])
        page=self.client.get(url)
        self.assertEqual(page.status_code,200)
        form=page.context['form']
        d={c:getattr(v,c) for c in financements.TARIF}
        d.update(attendu=bd6.jeton(tarif),action='correction',motif='',montant='28',prestataire=self.org.pk,actif='on',fin='')
        d['debut']='2026-01-01'
        rep=self.client.post(url,d)
        self.assertEqual(rep.status_code,302,rep.content[:500])
        self.assertEqual(tarif.versions.first().motif,'')
        d.update(action='changement',debut='2026-01-10',attendu=bd6.jeton(tarif))
        rep=self.client.post(url,d)
        self.assertContains(rep,'Justification de l’opération')
        self.assertIn('motif',rep.context['form'].errors)

    def test_document_corrige_sans_precision_et_octets_anciens_conserves(self):
        contenu=b'Texte fictif initial'
        p=pieces_dossier.ajouter(self.u,self.m,bd6.jeton(self.m),titre='Document fictif',date_document=date(2026,1,1),source='Fictif',fichier=SimpleUploadedFile('fictif.txt',contenu))
        ancienne=p.versions.first()
        pieces_dossier.ajouter(self.u,self.m,bd6.jeton(self.m),titre='Titre rectifié fictif',date_document=date(2026,1,1),source='Fictif',fichier=None,piece=p,motif='')
        ancienne.refresh_from_db()
        self.assertEqual(bytes(ancienne.contenu),contenu)
        self.assertEqual(p.versions.first().motif,'')

    def test_confirmation_et_longueur_ne_sont_pas_remplacees_par_le_motif(self):
        with self.assertRaises(ValidationError):precision.valider('x'*241)
        from . import accords
        token=accords.jeton(self.accord)
        with self.assertRaises(ValidationError):accords.annuler(self.u,self.accord,'',token)
        self.accord.refresh_from_db();self.assertIsNone(self.accord.annule_le)
