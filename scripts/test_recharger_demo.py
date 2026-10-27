import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
import sys

spec=importlib.util.spec_from_file_location('recharger_demo',Path(__file__).with_name('recharger-demo.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

@unittest.skipUnless(sys.platform.startswith("linux"), "Rechargement local Linux uniquement.")
class RechargeDemoTests(unittest.TestCase):
    def test_processus_etranger_refuse_et_demo_reconnue(self):
        with tempfile.TemporaryDirectory() as t:
            racine=Path(t);proc=racine/'123';proc.mkdir();data=racine/'donnees';data.mkdir()
            (proc/'cmdline').write_bytes(b'python\0autre-application')
            (proc/'environ').write_bytes(b'')
            with self.assertRaises(ValueError):module.environnement(123,racine)
            (proc/'cmdline').write_bytes(b'gunicorn: master')
            (proc/'environ').write_text('\0'.join(['DJANGO_SETTINGS_MODULE=pas_a_pas_accompagnement.settings_demo','ACCOMPAGNEMENT_DEMONSTRATION=oui','ACCOMPAGNEMENT_BIND=127.0.0.1','ACCOMPAGNEMENT_DONNEES='+str(data)]))
            self.assertEqual(module.environnement(123,racine)['ACCOMPAGNEMENT_DONNEES'],str(data))
            with self.assertRaises(ValueError):module.environnement(1,racine)
