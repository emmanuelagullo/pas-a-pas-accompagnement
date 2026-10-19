"""Garanties SQL déjà utilisées, sans inventer de modèle CHRS."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.contrib.auth import get_user_model
from django.db import connection, connections, close_old_connections, IntegrityError, transaction
from django.test import TransactionTestCase, RequestFactory, override_settings
from identites.models import LimiteAuthentification
from identites import limites


@skipUnless(connection.vendor == 'postgresql', 'Qualification PostgreSQL dédiée')
class ContraintesPostgresql(TransactionTestCase):
    def parallele(self, action):
        depart = Barrier(2)
        def lancer(_):
            close_old_connections()
            try:
                depart.wait(10)
                return action()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(lancer, range(2)))

    def test_unicite_concurrente_du_compte_et_rollback(self):
        def creer():
            try:
                with transaction.atomic():
                    get_user_model().objects.create_user('meme-compte-fictif')
                return True
            except IntegrityError:
                return False
        self.assertEqual(sum(self.parallele(creer)), 1)
        self.assertEqual(get_user_model().objects.filter(username='meme-compte-fictif').count(), 1)

    @override_settings(AUTH_TENTATIVES_COMPTE=1, AUTH_TENTATIVES_IP=100)
    def test_plafond_concurrent_persistant(self):
        def demander():
            request = RequestFactory().get('/', REMOTE_ADDR='192.0.2.1')
            return limites.autoriser(request, 'qualification', 'compte-fictif')
        self.assertEqual(sum(self.parallele(demander)), 1)
        self.assertEqual(sorted(LimiteAuthentification.objects.values_list('tentatives', flat=True)), [1, 2])
