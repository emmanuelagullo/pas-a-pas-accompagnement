from datetime import date
from django.urls import reverse
from . import tests_navigation
from django.test import TestCase
from django.contrib.auth.models import Permission
from . import repas
from .models import RepasDistribue, Transmission


class JourTests(TestCase):
    def setUp(self):
        tests_navigation.NavigationTests.setUp(self)
        self.accord=repas.accorder(self.u,self.a,[self.p],date(2026,1,1),None,'dejeuner')
        self.url=reverse('suivi:jour')+'?date=2026-01-03'

    def donnees(self,quantite=1):
        return {'repas-TOTAL_FORMS':'1','repas-INITIAL_FORMS':'1','repas-MIN_NUM_FORMS':'0','repas-MAX_NUM_FORMS':'500',
            'repas-0-accord':str(self.accord.pk),'repas-0-beneficiaire':str(self.p.pk),'repas-0-quantite':str(quantite)}

    def test_lot_et_double_envoi(self):
        self.assertContains(self.client.get(self.url),'Travail du jour')
        self.assertRedirects(self.client.post(self.url,self.donnees()),self.url)
        reponse=self.client.post(self.url,self.donnees())
        self.assertContains(reponse,'Aucune ligne du lot')
        self.assertEqual(RepasDistribue.objects.count(),1)

    def test_lot_invalide_et_droits(self):
        reponse=self.client.post(self.url,self.donnees(0))
        self.assertEqual(reponse.status_code,200)
        self.assertFalse(RepasDistribue.objects.exists())
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(self.url).status_code,403)
        self.assertEqual(self.client.post(self.url,self.donnees()).status_code,403)

    def test_rollback_du_lot_complet(self):
        autre=repas.accorder(self.u,self.a,[self.p],date(2026,1,1),None,'diner')
        # La deuxième ligne répète une paire : la première ne doit pas rester.
        donnees=self.donnees()
        donnees.update({'repas-TOTAL_FORMS':'2','repas-INITIAL_FORMS':'2',
            'repas-1-accord':str(self.accord.pk),'repas-1-beneficiaire':str(self.p.pk),'repas-1-quantite':'1'})
        self.assertContains(self.client.post(self.url,donnees),'Aucune ligne du lot')
        self.assertFalse(RepasDistribue.objects.exists())

    def test_actions_rapides_sans_separateur_orphelin(self):
        reponse = self.client.get(self.url)
        self.assertContains(reponse, reverse('suivi:creer'))
        self.assertNotContains(reponse, 'Créer un ménage</a> ·')
        self.assertContains(reponse, 'Actions rapides')

    def test_actions_rapides_masquees_sans_droit(self):
        # Le droit de consulter le travail du jour reste, sans droit de créer.
        self.u.user_permissions.remove(*list(self.u.user_permissions.filter(
            codename__in=['add_menage', 'add_appartenance', 'add_personne', 'view_transmission'])))
        reponse = self.client.get(self.url)
        self.assertEqual(reponse.status_code, 200)
        self.assertNotContains(reponse, 'Actions rapides')

    def test_raccourcis_du_travail_du_jour_et_permissions(self):
        # Le raccourci général reste accessible sans hébergement actif.
        reponse = self.client.get(self.url)
        self.assertNotContains(reponse, reverse('personnes:creer'))
        self.u.user_permissions.add(Permission.objects.get(codename='add_personne', content_type__app_label='personnes'))
        self.assertContains(self.client.get(self.url), reverse('personnes:creer'))
        self.assertContains(reponse, reverse('suivi:creer'))
        # Le menu ne doit pas inventer d'opérations non autorisées.
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_relais_transmissions_et_confidentialite(self):
        message = Transmission.objects.create(auteur=self.u, contenu="Relais de nuit fictif")
        self.assertContains(self.client.get(self.url), message.contenu)
        self.u.user_permissions.remove(*list(self.u.user_permissions.filter(codename="view_transmission")))
        reponse = self.client.get(self.url)
        self.assertEqual(reponse.status_code, 200)
        self.assertNotContains(reponse, message.contenu)
        self.assertNotContains(reponse, "Relais entre équipes")
