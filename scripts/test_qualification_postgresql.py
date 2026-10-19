"""Les réglages de qualification ne s’activent jamais implicitement."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent

class ActivationPostgresqlTests(unittest.TestCase):
    def lancer(self, code, **variables):
        env = {k:v for k,v in os.environ.items() if not k.startswith('PG') and k != 'ACCOMPAGNEMENT_PG_QUALIFICATION'}
        return subprocess.run([sys.executable, '-c', code], cwd=ROOT,
                              env={**env, **variables}, capture_output=True, text=True)

    def test_reglages_refusent_activation_implicite_et_nom_non_jetable(self):
        code = 'import pas_a_pas_accompagnement.settings_tests_postgresql'
        for variables, message in [({}, 'réservé à la qualification'),
                ({'ACCOMPAGNEMENT_PG_QUALIFICATION':'oui', 'PGDATABASE':'base-existante'}, 'base jetable')]:
            with self.subTest(variables=variables):
                resultat = self.lancer(code, **variables)
                self.assertNotEqual(resultat.returncode, 0)
                self.assertIn(message, resultat.stderr)

    def test_recette_refuse_activation_implicite(self):
        resultat = self.lancer("import runpy; runpy.run_path('scripts/qualifier-postgresql.py', run_name='__main__')")
        self.assertNotEqual(resultat.returncode, 0)
        self.assertIn('Activer explicitement', resultat.stderr)
