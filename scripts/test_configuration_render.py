"""Exercer le script réel sans hébergement, base ou secret : arrêt au premier manage.py."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
NOMS=['ACCOMPAGNEMENT_HOSTS','ACCOMPAGNEMENT_CSRF_ORIGINS','ACCOMPAGNEMENT_PROXY_HTTPS']


@unittest.skipIf(os.name=='nt','Script Bash de déploiement Unix.')
class ConfigurationRenderTests(unittest.TestCase):
    def test_domaines_automatiques_surcharges_et_hors_render(self):
        cas=[
            ({'RENDER_EXTERNAL_HOSTNAME':'essai-fictif.onrender.com'},
             ['essai-fictif.onrender.com','https://essai-fictif.onrender.com','oui']),
            ({'RENDER_EXTERNAL_HOSTNAME':'essai-fictif.onrender.com',
              'ACCOMPAGNEMENT_HOSTS':'autre.fictif.example',
              'ACCOMPAGNEMENT_CSRF_ORIGINS':'https://origine.fictif.example',
              'ACCOMPAGNEMENT_PROXY_HTTPS':'non'},
             ['autre.fictif.example','https://origine.fictif.example','non']),
            ({'RENDER_EXTERNAL_HOSTNAME':'essai-fictif.onrender.com',
              'ACCOMPAGNEMENT_HOSTS':'a.fictif.example,b.fictif.example'},
             ['a.fictif.example,b.fictif.example','https://a.fictif.example,https://b.fictif.example','oui']),
            ({},[None,None,None]),
        ]
        for valeurs,attendu in cas:
            with self.subTest(valeurs=valeurs),tempfile.TemporaryDirectory() as t:
                root=Path(t);bin=root/'bin';bin.mkdir();faux=bin/'python3'
                faux.write_text('#!'+sys.executable+'\nimport os,sys,json\n'
                    +"if len(sys.argv)>1 and sys.argv[1]=='manage.py':\n"
                    +' print(json.dumps([os.environ.get(n) for n in '+repr(NOMS)+']))\n'
                    +' sys.exit(37)\n'
                    +'os.execv(sys.executable,[sys.executable,*sys.argv[1:]])\n')
                faux.chmod(0o700)
                env={k:v for k,v in os.environ.items() if not k.startswith(('ACCOMPAGNEMENT_','RENDER_')) and k!='DATABASE_URL'}
                env.update(valeurs,TMPDIR=t,PATH=str(bin)+os.pathsep+os.environ.get('PATH',''))
                result=subprocess.run(['bash',str(ROOT/'start-render.sh')],cwd=ROOT,env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,37,result.stderr)
                self.assertEqual(json.loads(result.stdout),attendu)


if __name__=='__main__':unittest.main()
