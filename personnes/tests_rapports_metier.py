from datetime import date
from decimal import Decimal
from io import StringIO
import csv
from django.test import TestCase
from django.urls import reverse
from . import tests_navigation, rapports_metier as rapports
from .models import Personne, AccordHebergement, Sejour
from .statistiques import bilan


class RapportsMetierTests(TestCase):
    def setUp(self):
        tests_navigation.NavigationTests.setUp(self)
        self.accord = AccordHebergement.objects.create(accompagnement=self.a, debut=date(2025,1,1), cree_par=self.u)

    def personne(self, precision='', naissance=None, annee=None):
        return Personne.objects.create(designation='Identité fictive', precision_naissance=precision,
            date_naissance=naissance, annee_naissance=annee, cree_par=self.u)

    def sejour(self, personnes, debut=date(2026,1,1), fin=date(2026,1,4)):
        s = Sejour.objects.create(accord=self.accord, debut=debut, fin=fin, cree_par=self.u)
        s.beneficiaires.set(personnes)
        return s

    def test_mouvements_collectifs_individuels_et_reentre_sans_recompter_personnes(self):
        enfant = self.personne()
        self.sejour([self.p, enfant])
        self.sejour([self.p], date(2026,1,6), date(2026,1,8))
        resultat = rapports.mouvements(date(2026,1,1), date(2026,2,1))
        self.assertEqual(resultat['admissions_sejours'], 2)
        self.assertEqual(resultat['beneficiaires_admissions'], 3)
        self.assertEqual(resultat['personnes_admises_distinctes'], 2)
        self.assertEqual(resultat['beneficiaires_sorties'], 3)
        self.assertEqual(resultat['nuits_sejours_clos_total'], 5)
        self.assertEqual(resultat['nuits_sejours_clos_moyenne'], Decimal('2.5'))
        self.assertEqual(bilan(date(2026,1,1), date(2026,2,1))['admissions'], 2)

    def test_durees_completes_des_sorties_et_borne_exclue(self):
        self.sejour([self.p], date(2025,12,30), date(2026,1,2))
        self.sejour([self.p], date(2026,1,1), date(2026,2,1))
        self.sejour([self.p], date(2026,1,1), None)
        resultat = rapports.mouvements(date(2026,1,1), date(2026,2,1))
        self.assertEqual(resultat['sorties_sejours'], 1)
        self.assertEqual(resultat['nuits_sejours_clos_total'], 3)
        vide = rapports.mouvements(date(2024,1,1), date(2024,2,1))
        self.assertEqual(vide['nuits_sejours_clos_total'], 0)
        self.assertIsNone(vide['nuits_sejours_clos_min'])
        self.assertIsNone(vide['nuits_sejours_clos_moyenne'])

    def test_ages_reference_anniversaire_dedoublonnage_et_precision(self):
        exacte = self.personne('exacte', date(2000,1,31))
        estimee = self.personne('estimee', date(1990,1,1))
        annee = self.personne('annee', annee=1980)
        annee_estimee = self.personne('annee_estimee', annee=1970)
        apres = self.personne('exacte', date(2026,2,1))
        self.sejour([exacte, estimee, annee, annee_estimee, apres, self.p])
        self.sejour([exacte])
        reference, ages, qualite = rapports.ages(date(2026,1,1), date(2026,2,1))
        self.assertEqual(reference, date(2026,1,31))
        self.assertEqual(dict(ages), {26: 1})
        self.assertEqual(sum(qualite.values()), 5)
        self.assertTrue(all(qualite[code] == 1 for code in qualite))
        self.assertEqual(sum(ages.values()) + sum(qualite.values()), 6)

    def test_naissance_bissextile_convention_calendrier(self):
        p = self.personne('exacte', date(2000,2,29))
        self.sejour([p], date(2025,1,1), None)
        self.assertEqual(dict(rapports.ages(date(2025,2,1), date(2025,3,1))[1]), {24: 1})
        self.assertEqual(dict(rapports.ages(date(2025,2,1), date(2025,3,2))[1]), {25: 1})

    def test_ecran_csv_et_modele_de_rapport(self):
        p = self.personne('exacte', date(2000,1,31))
        self.sejour([p])
        url = reverse('statistiques')
        params = {'debut':'2026-01-01', 'fin':'2026-02-01', 'rapport':'ages'}
        self.assertContains(self.client.get(url, params), '26 ans')
        params['format'] = 'csv'
        lignes = list(csv.reader(StringIO(self.client.get(url, params).content.decode())))
        self.assertIn(['2026-01-01','2026-02-01','2026-01-31','age_exact','26','1'], lignes)
        params.update(rapport='mouvements', comparer='1')
        lignes = list(csv.reader(StringIO(self.client.get(url, params).content.decode())))
        self.assertIn(['2026-01-01','2026-02-01','nuits_sejours_clos_total','3'], lignes)
        del params['format']
        self.assertContains(self.client.get(url, params), 'Période précédente de même durée')
        params['nom'] = 'Rapport fictif'
        self.assertEqual(self.client.post(reverse('statistiques_modele_ajouter'), params).status_code, 302)

    def test_ages_exigent_consultation_personnes(self):
        self.u.user_permissions.remove(*self.u.user_permissions.filter(codename='view_personne'))
        url = reverse('statistiques')
        params = {'debut':'2026-01-01', 'fin':'2026-02-01', 'rapport':'ages'}
        self.assertEqual(self.client.get(url, params).status_code, 403)
        params['rapport'] = 'synthese'
        self.assertEqual(self.client.get(url, params).status_code, 200)

    def test_periodes_invalides(self):
        for fonction in (rapports.ages, rapports.mouvements):
            with self.assertRaises(ValueError): fonction(date(2026,1,1), date(2026,1,1))


    def test_comparaison_borne_minimale_et_pas_de_calcul_nuitees_inutile(self):
        from unittest.mock import patch
        url = reverse('statistiques')
        with patch('personnes.vues_statistiques.bilan', side_effect=AssertionError('Bilan non requis')):
            page = self.client.get(url, {'debut':'0001-01-01', 'fin':'0001-01-02', 'rapport':'mouvements', 'comparer':'1'})
            self.assertContains(page, 'La période précédente dépasserait')
            self.assertEqual(self.client.get(url, {'debut':'2026-01-01', 'fin':'2026-02-01', 'rapport':'ages'}).status_code, 200)


    def test_lieux_et_export_inaccessibles_sans_leurs_droits(self):
        from .models import LieuHebergement
        LieuHebergement.objects.create(libelle='Lieu réservé fictif', cree_par=self.u)
        self.u.user_permissions.remove(*self.u.user_permissions.filter(codename='view_lieuhebergement'))
        params = {'debut':'2026-01-01', 'fin':'2026-02-01', 'rapport':'synthese'}
        url = reverse('statistiques')
        self.assertNotContains(self.client.get(url, params), 'Lieu réservé fictif')
        params['rapport'] = 'exploration_hebergement'
        self.assertEqual(self.client.get(url, params).status_code, 403)
        params['format'] = 'csv'
        self.assertEqual(self.client.get(url, params).status_code, 403)


    def test_arrondi_arithmetique_moyenne(self):
        for nuits in [1, 1, 1, 2]:
            self.sejour([self.p], date(2026,1,1), date(2026,1,1 + nuits))
        self.assertEqual(rapports.mouvements(date(2026,1,1), date(2026,2,1))['nuits_sejours_clos_moyenne'], Decimal('1.3'))
