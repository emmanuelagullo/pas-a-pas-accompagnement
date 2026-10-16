"""Vraies connexions SQLite concurrentes : au plus une consommation réussie."""
from concurrent.futures import ThreadPoolExecutor
from importlib.util import find_spec
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import DatabaseError, close_old_connections, connections
from django.test import TransactionTestCase, override_settings
from pas_communs.authentification import totp
from . import double_facteur as facteur
from .tests_double_facteur import CLE, MOT, RAPIDE

DEPENDANCES=all(find_spec(n) is not None for n in ("cryptography","qrcode","django_otp"))


@skipUnless(DEPENDANCES,"requirements-2fa.txt non installé")
@override_settings(DOUBLE_FACTEUR_CLES=[CLE],PASSWORD_HASHERS=RAPIDE)
class ConsommationConcurrente(TransactionTestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user("concurrent-fictif",password=MOT)
        ligne=facteur.commencer(self.user)
        self.cle=totp.dechiffrer(ligne.cle_chiffree,cles=[CLE])
        self.instant=1800000000
        from django_otp.oath import TOTP
        t=TOTP(self.cle);t.time=self.instant-300
        _,self.codes=facteur.confirmer(self.user,f"{t.token():06d}",instant=self.instant-300)
        t.time=self.instant;self.code=f"{t.token():06d}"

    def parallele(self,code):
        depart=Barrier(2)
        def consommer():
            close_old_connections()
            try:
                user=get_user_model().objects.get(pk=self.user.pk)
                depart.wait(5)
                return bool(facteur.verifier(user,code,instant=self.instant))
            except DatabaseError:
                # SQLite peut refuser une écriture occupée ; la vue refuse aussi
                # l’accès dans ce cas, sans considérer le code comme validé.
                return False
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultats=list(pool.map(lambda _:consommer(),range(2)))
        self.assertEqual(sum(resultats),1)
        self.assertIsNone(facteur.verifier(self.user,code,instant=self.instant))

    def test_un_code_totp_ne_connecte_qu_un_client(self):
        # Synchroniser les deux calculs garantit que les deux clients ont lu
        # le même ancien pas avant de tenter l’UPDATE conditionnel.
        calcul=totp.verifier_pas;barriere=Barrier(2)
        def calculer(*args,**kwargs):
            pas=calcul(*args,**kwargs)
            barriere.wait(5)
            return pas
        with patch.object(totp,"verifier_pas",side_effect=calculer):
            depart=Barrier(2)
            def lancer():
                close_old_connections()
                try:
                    depart.wait(5)
                    return bool(facteur.verifier(self.user,self.code,instant=self.instant))
                except DatabaseError:
                    return False
                finally:
                    connections.close_all()
            with ThreadPoolExecutor(max_workers=2) as pool:
                resultats=list(pool.map(lambda _:lancer(),range(2)))
        self.assertEqual(sum(resultats),1)
        self.assertIsNone(facteur.verifier(self.user,self.code,instant=self.instant))

    def test_un_code_secours_ne_connecte_qu_un_client(self):
        self.parallele(self.codes[0])
