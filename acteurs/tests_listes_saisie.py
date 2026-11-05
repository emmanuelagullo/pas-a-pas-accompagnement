from django.test import TestCase
from django.urls import reverse

from . import services
from .listes_saisie import choix
from .tests import AccesTests


class ListesSaisieTests(TestCase):
    setUp = AccesTests.setUp
    compte = AccesTests.compte
    dossier = AccesTests.dossier

    def test_heritage_et_liste_vide(self):
        champ = 'destination_sortie'
        self.assertIn('Logement social', choix(champ, etablissement=self.etab, service=self.sa))
        self.etab.listes_saisie = {champ: ['Résidence sociale']}
        self.etab.save(update_fields=['listes_saisie'])
        self.assertEqual(choix(champ, etablissement=self.etab, service=self.sa), ['Résidence sociale'])
        url = reverse('acteurs:listes_service', args=[self.sa.pk])
        self.client.force_login(self.ua)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.admin)
        response = self.client.post(url, {
            'attendu': services.jeton(self.sa), 'motif_entree_commun': 'on', 'motif_sortie_commun': 'on',
            champ: '',
        })
        self.assertEqual(response.status_code, 302)
        self.sa.refresh_from_db()
        self.assertEqual(choix(champ, etablissement=self.etab, service=self.sa), [])
        response = self.client.post(url, {
            'attendu': services.jeton(self.sa), 'motif_entree_commun': 'on', 'motif_sortie_commun': 'on',
            champ + '_commun': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.sa.refresh_from_db()
        self.assertEqual(choix(champ, etablissement=self.etab, service=self.sa), ['Résidence sociale'])
