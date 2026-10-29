from datetime import date
from io import StringIO
from unittest.mock import patch
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from . import tests_social, social, corrections, suivi
from .models import SituationSociale, CorrectionPeriode, OperationSociale


class RetroactiviteTests(TestCase):
    def setUp(self):
        tests_social.SocialTests.setUp(self)
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        self.u = type(self.u).objects.get(pk=self.u.pk)

    def ajouter(self, jour, valeur='emploi', motif='Situation oubliée'):
        self.a.refresh_from_db()
        return social.renseigner(self.u, self.a, self.p, 'emploi', valeur, date(2026,1,jour),
            'Source fictive', motif, social.jeton_situations(self.a))

    def test_insertion_entre_deux_valeurs_et_avant_premiere(self):
        premiere = self.ajouter(5)
        derniere = self.ajouter(20, 'formation')
        inseree = self.ajouter(10, 'sans_emploi')
        premiere.refresh_from_db()
        self.assertEqual(premiere.fin, inseree.debut)
        self.assertEqual(inseree.fin, derniere.debut)
        self.assertEqual(social.etat_date(self.a, date(2026,1,15)).get(), inseree)
        trace = CorrectionPeriode.objects.get()
        self.assertEqual(trace.ancienne_fin, date(2026,1,20))
        self.assertEqual(trace.nouvelle_fin, date(2026,1,10))
        avant = self.ajouter(2)
        self.assertEqual(avant.fin, premiere.debut)
        self.assertEqual(CorrectionPeriode.objects.count(), 1)
        self.assertEqual(OperationSociale.objects.filter(action='Situation insérée').count(), 2)

    def test_insertion_exige_motif_et_droits_et_refuse_meme_date(self):
        self.ajouter(20)
        self.ajouter(10, motif='')
        self.assertEqual(OperationSociale.objects.filter(action='Situation insérée').get().motif, '')
        with self.assertRaises(ValidationError): self.ajouter(20, motif='Doublon')
        self.u.user_permissions.remove(*self.u.user_permissions.filter(codename='view_correctionperiode'))
        self.u = type(self.u).objects.get(pk=self.u.pk)
        with self.assertRaises(PermissionDenied): self.ajouter(5)
        self.assertEqual(SituationSociale.objects.count(), 2)

    def test_perime_et_echec_journal_ne_modifient_pas_bornes(self):
        premiere = self.ajouter(5)
        self.a.refresh_from_db()
        attendu = social.jeton_situations(self.a)
        self.ajouter(20)
        with self.assertRaises(ValidationError):
            social.renseigner(self.u, self.a, self.p, 'emploi', 'formation', date(2026,1,10),
                'Source fictive', 'Oubli', attendu)
        with patch.object(OperationSociale.objects, 'create', side_effect=RuntimeError('échec fictif')):
            with self.assertRaises(RuntimeError): self.ajouter(10)
        premiere.refresh_from_db()
        self.assertEqual(premiere.fin, date(2026,1,20))
        self.assertFalse(CorrectionPeriode.objects.exists())
        self.assertEqual(SituationSociale.objects.count(), 2)

    def test_histoire_anterieure_ne_deplace_pas_suivi(self):
        with self.assertRaises(ValidationError):
            social.evenement(self.u, self.a, self.p, date(2025,5,1), 'Fait historique fictif', 'Source fictive')
        e = social.evenement(self.u, self.a, self.p, date(2025,5,1), 'Fait historique fictif', 'Source fictive', anterieur=True)
        corrections.texte(self.u, e, date(2025,6,1), e.texte, 'Date précisée', corrections.jeton(e), source=e.source)
        self.a.refresh_from_db()
        self.assertEqual(self.a.debut, date(2026,1,1))
        self.assertFalse(social.etat_date(self.a, date(2025,6,1)).exists())
        corrections.periode(self.u, self.a, date(2026,1,2), None, 'Début rectifié', corrections.jeton(self.a))
        suivi.clore(self.u, self.a, date(2026,2,1))
        self.client.force_login(self.u)
        self.assertContains(self.client.get(reverse('suivi:social', args=[self.a.pk])), 'Histoire antérieure au suivi')

    def test_http_insertion_avec_jeton_et_motif(self):
        self.ajouter(20)
        self.a.refresh_from_db()
        self.client.force_login(self.u)
        url = reverse('suivi:situation_sociale', args=[self.a.pk, 'emploi'])
        self.assertContains(self.client.get(url), 'name="attendu"')
        response = self.client.post(url, {'beneficiaire': str(self.p.pk), 'valeur': 'formation',
            'debut': '2026-01-10', 'source': 'Source fictive', 'motif': 'Oubli fictif', 'attendu': social.jeton_situations(self.a)})
        self.assertRedirects(response, reverse('suivi:social', args=[self.a.pk]))
        self.assertEqual(SituationSociale.objects.count(), 2)


    def test_correction_valeur_perimee_necrase_pas_information(self):
        situation = self.ajouter(5)
        attendu = social.jeton_valeur(situation)
        social.corriger(self.u, situation, 'formation', 'Précision', attendu)
        with self.assertRaises(ValidationError):
            social.corriger(self.u, situation, 'sans_emploi', 'Tardif', attendu)
        situation.refresh_from_db()
        self.assertEqual(situation.valeur, 'formation')


    def test_insertion_ne_comble_pas_un_trou_historique(self):
        ancienne = SituationSociale.objects.create(accompagnement=self.a, beneficiaire=self.p,
            dimension='emploi', valeur='emploi', debut=date(2026,1,5), fin=date(2026,1,8),
            source='Archive fictive', cree_par=self.u)
        self.ajouter(20)
        inseree = self.ajouter(10, 'formation')
        ancienne.refresh_from_db()
        self.assertEqual(ancienne.fin, date(2026,1,8))
        self.assertEqual(inseree.fin, date(2026,1,20))
        self.assertFalse(social.etat_date(self.a, date(2026,1,9)).exists())
