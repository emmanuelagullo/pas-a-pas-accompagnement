"""Contrat de sélection des espaces du lanceur (sans moteur graphique)."""
import importlib.util
from pathlib import Path
import tempfile
from django.test import SimpleTestCase

spec = importlib.util.spec_from_file_location('lanceur_espaces', Path(__file__).resolve().parents[1]/'scripts/lancer-local.py')
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)


class EspacesTests(SimpleTestCase):
    def test_essai_distinct_meme_avec_un_paquet_personnalise(self):
        with tempfile.TemporaryDirectory() as t:
            racine = Path(t).resolve()
            defaut = racine/'produit/paquet-autonome'
            habituel = racine/'personnalise'
            self.assertEqual(local.choisir_paquet(habituel, defaut), habituel)
            self.assertEqual(local.choisir_paquet(habituel, defaut, True), defaut.parent/'essai-fictif')
            self.assertFalse(habituel.exists())
            with self.assertRaises(ValueError):
                local.choisir_paquet(defaut.parent/'essai-fictif', defaut, True)
            with self.assertRaises(ValueError):
                local.choisir_paquet(defaut.parent, defaut, True)

    def test_retour_conserve_le_chemin_habituel_y_compris_depuis_environnement(self):
        habituel = Path('/espace-personnalise')
        for arguments in [['programme', '--sans-fenetre'], ['programme', '--paquet=ancien', '--essai'],
                          ['programme', '--paquet', 'ancien', '--essai']]:
            essai = local.arguments_espace(arguments, 'essai', habituel)
            self.assertEqual(essai.count('--essai'), 1)
            retour = local.arguments_espace(essai, 'habituel', habituel)
            self.assertNotIn('--essai', retour)
            self.assertEqual(retour[-2:], ['--paquet', str(habituel)])

    def test_lien_symbolique_refuse(self):
        with tempfile.TemporaryDirectory() as t:
            racine = Path(t).resolve()
            try:
                (racine/'essai-fictif').symlink_to(racine/'habituel', target_is_directory=True)
            except OSError:
                self.skipTest('Liens symboliques indisponibles')
            with self.assertRaises(ValueError):
                local.choisir_paquet(racine/'habituel', racine/'paquet-autonome', True)
