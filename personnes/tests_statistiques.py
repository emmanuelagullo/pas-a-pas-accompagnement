from datetime import date
from django.test import TestCase
from django.urls import reverse
from .tests_navigation import NavigationTests
from .models import Personne, Sejour, AccordHebergement, RepasDistribue
from . import repas
from .statistiques import bilan


class StatistiquesTests(TestCase):
    def setUp(self):
        NavigationTests.setUp(self)

    def test_periode_et_dedoublonnage(self):
        accord = AccordHebergement.objects.create(accompagnement=self.a, debut=date(2026, 1, 1), cree_par=self.u)
        accord.beneficiaires.add(self.p)
        for debut, fin in [(date(2026, 1, 1), date(2026, 1, 4)),
                           (date(2026, 1, 3), date(2026, 1, 6))]:
            sejour = Sejour.objects.create(accord=accord, debut=debut, fin=fin, cree_par=self.u)
            sejour.beneficiaires.add(self.p)
        resultat = bilan(date(2026, 1, 2), date(2026, 1, 5))
        self.assertEqual(resultat['personnes_avec_sejour'], 1)
        self.assertEqual(resultat['sejours'], 2)
        # Deux séjours contribuent chacun deux nuits sur [2, 5[.
        # La nuit commune du 3 janvier est comptée deux fois par définition.
        self.assertEqual(resultat['nuitees_theoriques'], 4)
        self.assertEqual(resultat['admissions'], 1)
        self.assertEqual(resultat['sorties'], 1)
        self.assertEqual(resultat['menages_accompagnes'], 1)

    def test_distributions_non_annulees_et_frontiere(self):
        accord = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), None, 'dejeuner')
        RepasDistribue.objects.create(accord=accord, beneficiaire=self.p, date=date(2026, 1, 2), quantite=2, cree_par=self.u)
        self.assertEqual(bilan(date(2026, 1, 2), date(2026, 1, 3))['repas_distribues'], 2)
        self.assertEqual(bilan(date(2026, 1, 3), date(2026, 1, 4))['repas_distribues'], 0)

    def test_consultation_droits_et_validation(self):
        url = reverse('statistiques')
        self.assertEqual(self.client.get(url, {'debut': '2026-01-02', 'fin': '2026-01-02'}).status_code, 200)
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_periode_invalide(self):
        with self.assertRaises(ValueError):
            bilan(date(2026, 1, 2), date(2026, 1, 2))

    def test_nuits_distinctes_et_absences(self):
        from .models import Absence
        accord = AccordHebergement.objects.create(
            accompagnement=self.a, debut=date(2026, 1, 1), cree_par=self.u)
        accord.beneficiaires.add(self.p)
        for debut, fin in [(date(2026, 1, 1), date(2026, 1, 4)),
                           (date(2026, 1, 3), date(2026, 1, 6))]:
            sejour = Sejour.objects.create(accord=accord, debut=debut, fin=fin, cree_par=self.u)
            sejour.beneficiaires.add(self.p)
            if debut.day == 1:
                Absence.objects.create(sejour=sejour, debut=date(2026, 1, 2),
                                       fin=date(2026, 1, 3))
        resultat = bilan(date(2026, 1, 2), date(2026, 1, 5))
        self.assertEqual(resultat['nuitees_theoriques'], 4)
        self.assertEqual(resultat['nuits_distinctes'], 3)
        self.assertEqual(resultat['nuits_hors_absences_declarees'], 2)

    def test_export_csv_et_permissions(self):
        url = reverse('statistiques')
        params = {'debut': '2026-01-02', 'fin': '2026-01-05', 'format': 'csv'}
        reponse = self.client.get(url, params)
        self.assertEqual(reponse.status_code, 200)
        self.assertIn('text/csv', reponse['Content-Type'])
        self.assertIn(b'nuits_distinctes', reponse.content)
        self.assertIn(b'2026-01-02,2026-01-05', reponse.content)
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(url, params).status_code, 403)


class VentilationsTests(TestCase):
    def setUp(self):
        NavigationTests.setUp(self)

    def test_mois_partiels_et_frontiere(self):
        from .statistiques import evolution_mensuelle
        accord = AccordHebergement.objects.create(accompagnement=self.a,
            debut=date(2026, 1, 30), cree_par=self.u)
        accord.beneficiaires.add(self.p)
        sejour = Sejour.objects.create(accord=accord, debut=date(2026, 1, 30),
            fin=date(2026, 2, 3), cree_par=self.u)
        sejour.beneficiaires.add(self.p)
        lignes = evolution_mensuelle(date(2026, 1, 31), date(2026, 2, 2))
        self.assertEqual([l['nuitees_theoriques'] for l in lignes], [1, 1])
        self.assertEqual([l['admissions'] for l in lignes], [0, 0])
        self.assertEqual([l['mois'] for l in lignes], ['2026-01', '2026-02'])

    def test_services_distribues(self):
        from .statistiques import ventilation_repas
        from django.utils import timezone
        accord = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), None, 'dejeuner')
        ligne = RepasDistribue.objects.create(accord=accord, beneficiaire=self.p,
            date=date(2026, 1, 2), quantite=2, cree_par=self.u)
        self.assertEqual(ventilation_repas(date(2026, 1, 1), date(2026, 2, 1))['dejeuner'], 2)
        ligne.annule_le = timezone.now()
        ligne.save(update_fields=['annule_le'])
        self.assertEqual(ventilation_repas(date(2026, 1, 1), date(2026, 2, 1))['dejeuner'], 0)

    def test_limite_de_mois(self):
        from .statistiques import evolution_mensuelle
        with self.assertRaises(ValueError):
            evolution_mensuelle(date(2020, 1, 1), date(2026, 1, 1))


class RapportsTests(TestCase):
    def setUp(self):
        NavigationTests.setUp(self)

    def test_exports_par_rapport(self):
        url = reverse('statistiques')
        params = {'debut': '2026-01-01', 'fin': '2026-02-01', 'format': 'csv'}
        for rapport, entete in (
            ('synthese', b'indicateur,valeur'),
            ('hebergement', b'indicateur,valeur'),
            ('repas', b'service,quantite_distribuee'),
            ('mensuel', b'mois,debut,fin,admissions'),
        ):
            with self.subTest(rapport=rapport):
                reponse = self.client.get(url, {**params, 'rapport': rapport})
                self.assertEqual(reponse.status_code, 200)
                self.assertIn(entete, reponse.content)

    def test_export_mensuel_trop_long_refuse(self):
        reponse = self.client.get(reverse('statistiques'), {
            'debut': '2020-01-01', 'fin': '2026-01-01',
            'rapport': 'mensuel', 'format': 'csv'})
        self.assertEqual(reponse.status_code, 400)

    def test_rapport_inconnu_et_permissions(self):
        url = reverse('statistiques')
        reponse = self.client.get(url, {'rapport': 'inconnu',
                                         'debut': '2026-01-01', 'fin': '2026-02-01'})
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, 'Synthèse de l’activité')
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(url, {'rapport': 'repas', 'format': 'csv'}).status_code, 403)

class PeriodesRapportsTests(TestCase):
    def setUp(self):
        NavigationTests.setUp(self)

    def test_bornes_periodes_annee_bissextile(self):
        from .vues_statistiques import bornes_periode
        self.assertEqual(bornes_periode('mois_precedent', date(2024, 3, 15)),
                         (date(2024, 2, 1), date(2024, 3, 1)))
        self.assertEqual(bornes_periode('annee_precedente', date(2026, 3, 15)),
                         (date(2025, 1, 1), date(2026, 1, 1)))

    def test_periode_rapide_et_comparaison(self):
        from unittest.mock import patch
        with patch('personnes.vues_statistiques.timezone.localdate', return_value=date(2026, 3, 15)):
            reponse = self.client.get(reverse('statistiques'), {
                'periode': 'mois_precedent', 'comparer': '1', 'rapport': 'hebergement'})
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, 'Comparaison avec la période précédente')
        self.assertContains(reponse, '2026-02-01')
        self.assertContains(reponse, '2026-03-01')

    def test_periode_inconnue_ne_remplace_pas_dates_saisies(self):
        reponse = self.client.get(reverse('statistiques'), {
            'periode': 'inconnue', 'debut': '2026-01-02', 'fin': '2026-01-05'})
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, '2026-01-02')


class QualificationStatistiquesTests(TestCase):
    """Contrats transversaux entre agrégats, ventilations et exports."""

    def setUp(self):
        NavigationTests.setUp(self)

    def test_reconciliation_mensuelle_des_flux_et_nuitees(self):
        from .statistiques import evolution_mensuelle
        accord = AccordHebergement.objects.create(
            accompagnement=self.a, debut=date(2026, 1, 1), cree_par=self.u)
        accord.beneficiaires.add(self.p)
        sejour = Sejour.objects.create(
            accord=accord, debut=date(2026, 1, 30),
            fin=date(2026, 3, 2), cree_par=self.u)
        sejour.beneficiaires.add(self.p)
        accord_repas = repas.accorder(self.u, self.a, [self.p],
                                     date(2026, 1, 1), None, 'dejeuner')
        for jour, quantite in ((date(2026, 1, 31), 2),
                               (date(2026, 2, 1), 3)):
            RepasDistribue.objects.create(accord=accord_repas,
                beneficiaire=self.p, date=jour, quantite=quantite, cree_par=self.u)
        debut, fin = date(2026, 1, 31), date(2026, 3, 1)
        total = bilan(debut, fin)
        lignes = evolution_mensuelle(debut, fin)
        self.assertEqual([l['mois'] for l in lignes], ['2026-01', '2026-02'])
        for cle in ('admissions', 'sorties', 'nuitees_theoriques',
                    'repas_distribues'):
            with self.subTest(indicateur=cle):
                self.assertEqual(sum(l[cle] for l in lignes), total[cle])
        self.assertEqual(total['nuitees_theoriques'], 29)
        self.assertEqual(total['repas_distribues'], 5)

    def test_exactement_24_mois_autorises_fin_exclue(self):
        from .statistiques import evolution_mensuelle
        debut = date(2024, 1, 1)
        fin = date(2026, 1, 1)
        self.assertEqual(len(evolution_mensuelle(debut, fin)), 24)
        with self.assertRaises(ValueError):
            evolution_mensuelle(debut, date(2026, 1, 2))

    def test_export_csv_mensuel_correspond_aux_calculs(self):
        import csv
        from io import StringIO
        from .statistiques import evolution_mensuelle
        params = {'debut': '2026-01-31', 'fin': '2026-03-01',
                  'rapport': 'mensuel', 'format': 'csv'}
        reponse = self.client.get(reverse('statistiques'), params)
        self.assertEqual(reponse.status_code, 200)
        lignes = list(csv.DictReader(StringIO(reponse.content.decode('utf-8'))))
        attendues = evolution_mensuelle(date(2026, 1, 31), date(2026, 3, 1))
        self.assertEqual([l['mois'] for l in lignes],
                         [l['mois'] for l in attendues])
        for ligne, attendue in zip(lignes, attendues):
            for cle in ('admissions', 'sorties', 'nuitees_theoriques',
                        'repas_distribues'):
                self.assertEqual(int(ligne[cle]), attendue[cle])

    def test_populations_mensuelles_non_additives(self):
        from .statistiques import evolution_mensuelle
        accord = AccordHebergement.objects.create(
            accompagnement=self.a, debut=date(2026, 1, 1), cree_par=self.u)
        accord.beneficiaires.add(self.p)
        sejour = Sejour.objects.create(
            accord=accord, debut=date(2026, 1, 30),
            fin=date(2026, 2, 3), cree_par=self.u)
        sejour.beneficiaires.add(self.p)
        debut, fin = date(2026, 1, 1), date(2026, 3, 1)
        lignes = evolution_mensuelle(debut, fin)
        self.assertEqual(bilan(debut, fin)['personnes_avec_sejour'], 1)
        self.assertEqual(sum(l['personnes_avec_sejour'] for l in lignes), 2)


class ExplorationRepasTests(TestCase):
    def setUp(self):
        NavigationTests.setUp(self)

    def test_regroupement_filtre_annulation_et_mois_vide(self):
        from .statistiques import exploration_repas
        from django.utils import timezone
        accord = repas.accorder(self.u, self.a, [self.p], date(2026, 1, 1), None, 'dejeuner')
        RepasDistribue.objects.create(accord=accord, beneficiaire=self.p,
            date=date(2026, 1, 15), quantite=2, cree_par=self.u)
        annule = RepasDistribue.objects.create(accord=accord, beneficiaire=self.p,
            date=date(2026, 2, 1), quantite=3, cree_par=self.u, annule_le=timezone.now())
        lignes = exploration_repas(date(2026, 1, 1), date(2026, 3, 1), service='dejeuner')
        self.assertEqual([(x['mois'], x['quantite']) for x in lignes],
                         [('2026-01', 2), ('2026-02', 0)])
        self.assertIsNotNone(annule.pk)

    def test_csv_filtre_et_permissions(self):
        url = reverse('statistiques')
        params = {'debut': '2026-01-01', 'fin': '2026-03-01',
                  'rapport': 'exploration_repas', 'service': 'dejeuner'}
        page = self.client.get(url, params)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'Repas par mois et service')
        export = self.client.get(url, {**params, 'format': 'csv'})
        self.assertEqual(export.status_code, 200)
        self.assertIn(b'mois,service,quantite_distribuee', export.content)
        self.assertIn(b'2026-02,dejeuner,0', export.content)
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(url, {**params, 'format': 'csv'}).status_code, 403)

    def test_periode_trop_longue_refusee_en_csv(self):
        response = self.client.get(reverse('statistiques'), {
            'debut': '2020-01-01', 'fin': '2026-01-01',
            'rapport': 'exploration_repas', 'format': 'csv'})
        self.assertEqual(response.status_code, 400)
