"""Python du constructeur et Python WASM : contrats distincts, sans réseau."""
import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('constructeur_pwa', Path(__file__).with_name('construire-pwa.py'))
constructeur = importlib.util.module_from_spec(spec)
spec.loader.exec_module(constructeur)


class PythonConstructionTests(unittest.TestCase):
    def test_python_trop_ancien_refuse_avant_toute_construction(self):
        with patch.object(constructeur.sys, 'version_info', (3, 11)), self.assertRaisesRegex(SystemExit, '3.12'):
            constructeur.construire(Path('/sortie-non-utilisee'))

    def test_journal_distingue_interpreteur_hote_et_runtime(self):
        sortie = io.StringIO()
        with redirect_stdout(sortie):
            constructeur.verifier_python_construction()
        self.assertIn('Python constructeur :', sortie.getvalue())
        self.assertIn(constructeur.sys.executable, sortie.getvalue())
        self.assertIn('Python embarqué : ' + constructeur.RUNTIME.python, sortie.getvalue())
        self.assertIn('Pyodide ' + constructeur.RUNTIME.version, sortie.getvalue())
