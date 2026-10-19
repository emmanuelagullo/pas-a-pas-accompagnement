"""Exécuter le bootstrap Pages sans réseau ni variables de setup historiques."""
import io
import os
from pathlib import Path
import tempfile
import textwrap
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent


def bootstrap():
    source=(ROOT/'pwa/publication/pages.yml').read_text()
    bloc=source.split("python3 - <<'PY'\n",1)[1].split('\n      PY',1)[0]
    return textwrap.dedent(bloc)


class BootstrapPagesTests(unittest.TestCase):
    def test_fichiers_pris_au_commit_source_sans_variable_supplementaire(self):
        sha='a'*40;urls=[]
        def ouvrir(url,timeout):
            urls.append(url)
            return io.BytesIO(b'contenu fictif')
        env={'PWA_SOURCE_SHA':sha,'CI_API_V4_URL':'https://forge.invalid/api/v4'}
        ancien=Path.cwd()
        with tempfile.TemporaryDirectory() as t:
            try:
                os.chdir(t)
                with patch.dict(os.environ,env,clear=True),patch('urllib.request.urlopen',side_effect=ouvrir):
                    exec(compile(bootstrap(),'<bootstrap Pages>','exec'),{})
                self.assertEqual({p.name for p in Path(t).iterdir()},
                    {'preparer-publication-pwa.py','requirements-communs.txt'})
                self.assertEqual(len(urls),2)
                for url in urls:
                    self.assertIn('pas-a-pas-accompagnement%2Fpas-a-pas-accompagnement/',url)
                    self.assertTrue(url.endswith('/raw?ref='+sha))
            finally:os.chdir(ancien)

    def test_sha_invalide_refuse_avant_telechargement(self):
        with patch.dict(os.environ,{'PWA_SOURCE_SHA':'main'},clear=True),patch('urllib.request.urlopen') as ouvrir:
            with self.assertRaises(SystemExit):
                exec(compile(bootstrap(),'<bootstrap Pages>','exec'),{})
        ouvrir.assert_not_called()


if __name__=='__main__':unittest.main()
