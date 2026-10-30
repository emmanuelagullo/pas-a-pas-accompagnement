"""Trois régressions ciblées des parcours quotidiens, sans nouvelle politique."""
from datetime import date, datetime, timedelta, timezone as tz
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from . import tests as anciens, services as s
from .contexte import perimetre
from .models import AppartenanceProfessionnelle, JournalAcces, PorteeObjet, Responsabilite
from .recherche import classer
from personnes import models as m


class ParcoursEssentielsTests(TestCase):
    setUp = anciens.AccesTests.setUp
    compte = anciens.AccesTests.compte
    dossier = anciens.AccesTests.dossier

    def test_attribution_utilise_le_jour_local_de_l_appartenance(self):
        jour = date(2026, 1, 2)
        AppartenanceProfessionnelle.objects.filter(professionnel=self.pc).update(debut=jour)
        with timezone.override('Europe/Paris'), patch('django.utils.timezone.now', return_value=datetime(2026, 1, 1, 23, 30, tzinfo=tz.utc)):
            s.ajouter_responsabilite(self.ua, self.da, self.da, self.pc, jour, 'suivi', s.jeton(self.da))
        self.assertEqual(JournalAcces.objects.get(action='ajout_responsabilite').date_effet, jour)
        # Le professionnel sorti au début du jour local n'est plus proposable.
        AppartenanceProfessionnelle.objects.filter(professionnel=self.pc).update(debut=date(2020, 1, 1), fin=jour)
        with timezone.override('Europe/Paris'), patch('django.utils.timezone.now', return_value=datetime(2026, 1, 1, 23, 35, tzinfo=tz.utc)):
            with self.assertRaisesMessage(ValidationError, 'membre de ce service'):
                s.ajouter_responsabilite(self.ua, self.da, self.a, self.pc, jour, 'suivi', s.jeton(self.da))
        self.assertEqual(JournalAcces.objects.filter(action='ajout_responsabilite').count(), 1)

    def test_relais_et_fin_conservent_la_date_metier_locale(self):
        jour = date(2026, 1, 2)
        AppartenanceProfessionnelle.objects.filter(professionnel=self.pc).update(debut=jour)
        Responsabilite.objects.create(dossier=self.da, professionnel=self.pa, cree_par=self.admin, debut=datetime(2025, 1, 1, tzinfo=tz.utc))
        with timezone.override('Europe/Paris'), patch('django.utils.timezone.now', return_value=datetime(2026, 1, 1, 23, 30, tzinfo=tz.utc)):
            _, proposition = s.proposition_relais(self.ua, self.da, self.da, descendants=False)
            ids = s.relayer(self.ua, self.da, self.pc, s.jeton(self.da), proposition)
        self.assertEqual(JournalAcces.objects.get(action='relais').date_effet, jour)
        with timezone.override('Europe/Paris'), patch('django.utils.timezone.now', return_value=datetime(2026, 1, 1, 23, 35, tzinfo=tz.utc)):
            s.terminer_responsabilite(self.uc, Responsabilite.objects.get(pk=ids[0]), jour, s.jeton(self.da))
        self.assertEqual(JournalAcces.objects.get(action='fin_responsabilite').date_effet, jour)

    def test_dossiers_en_cours_classes_par_creation_pas_par_anciennes_sorties(self):
        _, _, recent, _, _ = self.dossier(self.sa, self.ua, 'Récent')
        m.Menage.objects.filter(pk=self.ma.pk).update(cree_le=timezone.now()-timedelta(days=10))
        ancien = m.Accompagnement.objects.create(menage=self.ma, debut=date(2021, 1, 1), fin=date(2022, 1, 1), cree_par=self.ua)
        PorteeObjet.objects.create(modele=ancien._meta.label_lower, identifiant=str(ancien.pk), service=self.sa, dossier=self.da, prise=ancien)
        with perimetre(self.ua, self.sa):
            lignes = classer(self.ua, m.Menage.objects.all(), 'menage', 'tous', self.sa.pk)
        self.assertEqual([x.pk for x in lignes], [recent.pk, self.ma.pk])
