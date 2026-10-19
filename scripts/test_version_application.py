"""Même politique que Petits Pas : tag exact, développement et version embarquée."""
import os
import runpy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from pas_a_pas_accompagnement import version
from publication import release_notes, identity

SHA='a'*40


class VersionTests(unittest.TestCase):
    def test_tag_exact_et_pas_ancetre(self):
        self.assertEqual(version.version_pour_commit(SHA,{'0.2.0':SHA}),'0.2.0')
        self.assertEqual(version.version_pour_commit(SHA,{'0.1.0':'b'*40}),'dev.aaaaaaaa')
        with self.assertRaises(ValueError):version.version_pour_commit(SHA,{'0.1':SHA,'0.2':SHA})

    def test_tag_annote_render(self):
        sortie=f"{'b'*40}\trefs/tags/0.2.0\n{SHA}\trefs/tags/0.2.0^{{}}\n"
        with patch.object(version,'git',return_value=sortie):
            self.assertEqual(version.tags_distants(),{'0.2.0':SHA})
        with patch.dict(os.environ,{'RENDER_GIT_COMMIT':SHA},clear=True),patch.object(version,'tags_distants',return_value={'0.2.0':SHA}):
            self.assertEqual(version.version_application(),'0.2.0')

    def test_ci_tag_et_branche_coherents_avec_manifestes(self):
        for env,attendu in [({'CI_COMMIT_SHA':SHA,'CI_COMMIT_TAG':'0.2.0'},'0.2.0'),
                            ({'CI_COMMIT_SHA':SHA},'dev.aaaaaaaa'),
                            ({'GITHUB_SHA':SHA,'GITHUB_REF_TYPE':'branch'},'dev.aaaaaaaa'),
                            ({'GITHUB_SHA':SHA,'GITHUB_REF_TYPE':'tag','GITHUB_REF_NAME':'0.2.0'},'0.2.0')]:
            with self.subTest(env=env),patch.dict(os.environ,env,clear=True):
                self.assertEqual(version.version_application(),attendu)
                self.assertEqual(identity()['application_version'],attendu)

    def test_version_embarquee_sans_git(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'version-application.txt').write_text('0.2.0\n')
            with patch.object(version.sys,'frozen',True,create=True),patch.object(version.sys,'_MEIPASS',t,create=True),patch.object(version,'git') as git:
                self.assertEqual(version.version_application(),'0.2.0');git.assert_not_called()
            with patch.object(version.sys,'platform','emscripten'),patch.object(version,'RACINE',root),patch.object(version,'git') as git:
                self.assertEqual(version.version_application(),'0.2.0');git.assert_not_called()

    def test_notes_du_tag_ou_a_venir_sans_melange(self):
        texte='# Historique\n\n## À venir\nFutur.\n\n## 0.2.0 — date fictive\nVersion publiée.\n\n## 0.1.0\nAncien.\n'
        self.assertEqual(release_notes(None,texte),'Futur.\n')
        self.assertEqual(release_notes('0.2.0',texte),'Version publiée.\n')
        for mauvais in ['## 0.2.0\n','## 0.1.0\nAutre.','## 0.2.0\nA.\n## 0.2.0\nB.']:
            with self.subTest(mauvais=mauvais),self.assertRaises(ValueError):release_notes('0.2.0',mauvais)

    def test_construction_native_genere_et_embarque_la_version(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'scripts').mkdir();(root/'scripts/lancer-local.py').touch()
            with patch.dict(os.environ,{},clear=True),patch('publication.identity',return_value={'tag':'0.2.0','application_version':'0.2.0'}),patch('publication.release_notes'),patch('pas_communs.construction.assembler') as assembler:
                runpy.run_path(str(Path(__file__).parent/'PasAPasAccompagnement.spec'),init_globals={'SPECPATH':str(root/'scripts')})
            self.assertEqual((root/'version-application.txt').read_bytes(),b'0.2.0\n')
            self.assertIn(('version-application.txt','.'),assembler.call_args.kwargs['ressources'])
