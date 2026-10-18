"""Tests du CLI de candidats ; fichiers fictifs temporaires, aucune publication."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
SCRIPT=ROOT/'scripts/manifeste-publication.py'


class CandidatsTests(unittest.TestCase):
    def lancer(self,*args):
        return subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],cwd=ROOT,
            env={**os.environ,'CI_COMMIT_SHA':'a'*40,'CI_COMMIT_TAG':''},
            capture_output=True,text=True)

    def test_archive_alteree_ou_format_etranger_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);f=root/'programme.zip';f.write_bytes(b'archive fictive')
            m=root/'candidat.json'
            self.assertEqual(self.lancer('--destination',m,'--mode','programme','--target','linux',f).returncode,0)
            self.assertEqual(self.lancer('--verifier',m,'--target','linux').returncode,0)
            r=json.loads(m.read_text());r['format']='petits-pas-publication';m.write_text(json.dumps(r))
            self.assertNotEqual(self.lancer('--verifier',m).returncode,0)
            r['format']='pas-a-pas-accompagnement-publication';m.write_text(json.dumps(r));f.write_bytes(b'altere')
            self.assertNotEqual(self.lancer('--verifier',m).returncode,0)

    def test_bundle_test_ou_non_marque_jamais_archive(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);bundle=root/'bundle';bundle.mkdir()
            assets=[]
            for nom in ['index.html','worker.js','sw.js','application.zip']:
                data=b'fictif';(bundle/nom).write_bytes(data)
                assets.append({'url':'/'+nom,'sha256':hashlib.sha256(data).hexdigest()})
            c={'application':'pas-a-pas-accompagnement','version':'chrs.pwa.'+'a'*16,'assets':assets}
            for mode in [None,True,False]:
                if mode is not None:c['testMode']=mode
                (bundle/'config.json').write_text(json.dumps(c))
                resultat=self.lancer('--destination',root/'candidat.json','--mode','navigateur','--target','chromium','--bundle',bundle)
                self.assertEqual(resultat.returncode==0,mode is False,resultat.stderr)
                self.assertEqual((root/'PasAPasAccompagnement-pwa.zip').exists(),mode is False)
            self.assertEqual(self.lancer('--verifier',root/'candidat.json','--target','chromium').returncode,0)


if __name__=='__main__':unittest.main()
