"""Distinguer préparation lente, arrêt et refus HTTP dans la recette réelle."""
import importlib.util
from pathlib import Path
from unittest import TestCase,main
from unittest.mock import Mock,patch

spec=importlib.util.spec_from_file_location('captures',Path(__file__).with_name('capturer-site-chrs.py'))
captures=importlib.util.module_from_spec(spec);spec.loader.exec_module(captures)


class AttenteTests(TestCase):
    def test_arret_detecte_avant_epuisement_du_delai(self):
        processus=Mock(returncode=17);processus.poll.return_value=17
        with patch.object(captures.urllib.request,'urlopen') as requete:
            with self.assertRaisesRegex(RuntimeError,'code 17'):captures.attendre('http://127.0.0.1',300,processus)
            requete.assert_not_called()

    def test_preparation_lente_suivie_de_connexion(self):
        reponse=Mock();reponse.__enter__=Mock(return_value=Mock(status=200));reponse.__exit__=Mock(return_value=False)
        with patch.object(captures.urllib.request,'urlopen',side_effect=[OSError('préparation'),reponse]),patch.object(captures.time,'sleep'):
            captures.attendre('http://127.0.0.1',300)

    def test_expiration_conserve_le_dernier_diagnostic(self):
        with patch.object(captures.time,'monotonic',side_effect=[0,0,301]),patch.object(captures.time,'sleep'),patch.object(captures.urllib.request,'urlopen',side_effect=OSError('connexion refusée')):
            with self.assertRaisesRegex(RuntimeError,'300 s : connexion refusée'):captures.attendre('http://127.0.0.1',300)


if __name__=='__main__':main()
