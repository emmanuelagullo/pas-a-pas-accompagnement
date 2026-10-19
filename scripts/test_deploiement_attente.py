"""Horloge simulée : démarrage lent, expiration et sortie prématurée."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

p=Path(__file__).with_name('exercer-deploiement.py')
spec=importlib.util.spec_from_file_location('deploiement',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class AttenteTests(unittest.TestCase):
    def test_demarrage_apres_vingt_secondes_reste_accepte(self):
        processus=Mock();processus.poll.return_value=None
        journal=Mock()
        with patch.object(m.time,'monotonic',side_effect=[0,0,21]),patch.object(m.time,'sleep'),patch.object(m,'requete',side_effect=[OSError('pas encore prêt'),(200,{},json.dumps({'status':'ok'}).encode())]):
            m.attendre_demarrage(processus,1234,journal,180)
        journal.read_text.assert_not_called()

    def test_expiration_bornee_et_journal_conserve(self):
        journal=Mock();journal.read_text.return_value='migration fictive encore en cours'
        with patch.object(m.time,'monotonic',side_effect=[0,181]),patch.object(m,'requete') as requete:
            with self.assertRaisesRegex(RuntimeError,'180 s.*migration fictive'):
                m.attendre_demarrage(Mock(),1234,journal,180)
        requete.assert_not_called()

    def test_sortie_immediate_nattend_pas_le_delai(self):
        processus=Mock();processus.poll.return_value=17
        journal=Mock();journal.read_text.return_value='échec fictif'
        with patch.object(m.time,'monotonic',side_effect=[0,0]),patch.object(m.time,'sleep') as pause:
            with self.assertRaisesRegex(RuntimeError,'code 17'):
                m.attendre_demarrage(processus,1234,journal,180)
        pause.assert_not_called()


if __name__=='__main__':unittest.main()
