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

    def test_raccourcis_releve_suivant_permissions(self):
        droit = Permission.objects.get(codename="view_actionrelais", content_type__app_label="personnes")
        self.u.user_permissions.add(droit)
        reponse = self.client.get(self.url)
        self.assertContains(reponse, reverse("suivi:actions_relais"))
        self.assertContains(reponse, "Consulter les actions de relève")
        self.assertNotContains(reponse, "Créer une action de relève")
        self.assertContains(reponse, 'id="situation-date"')
        self.assertContains(reponse, 'id="repas-du-jour"')
        self.u.user_permissions.add(Permission.objects.get(codename="add_actionrelais", content_type__app_label="personnes"))
        self.assertContains(self.client.get(self.url), "Créer une action de relève")
        self.u.user_permissions.remove(droit)
        self.assertNotContains(self.client.get(self.url), reverse("suivi:actions_relais"))

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
        # Le profil de navigation ne reçoit pas automatiquement le droit CHRS8.
        droit = Permission.objects.get(codename="view_transmission", content_type__app_label="personnes")
        self.u.user_permissions.add(droit)
        message = Transmission.objects.create(auteur=self.u, contenu="Relais de nuit fictif")
        self.assertContains(self.client.get(self.url), message.contenu)
        self.u.user_permissions.remove(*list(self.u.user_permissions.filter(codename="view_transmission")))
        reponse = self.client.get(self.url)
        self.assertEqual(reponse.status_code, 200)
        self.assertNotContains(reponse, message.contenu)
        self.assertNotContains(reponse, "Relais entre équipes")

    def test_actions_relais_permissions_et_cloture(self):
        from .models import ActionRelais
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        consulter = Permission.objects.get(codename="view_actionrelais", content_type__app_label="personnes")
        creer = Permission.objects.get(codename="add_actionrelais", content_type__app_label="personnes")
        terminer = Permission.objects.get(codename="change_actionrelais", content_type__app_label="personnes")
        url = reverse("suivi:actions_relais")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.u.user_permissions.add(consulter)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {"libelle": "Vérifier le relais"}).status_code, 403)
        self.u.user_permissions.add(creer)
        self.assertRedirects(self.client.post(url, {"libelle": "Vérifier le relais", "echeance": ""}), url)
        action = ActionRelais.objects.get()
        self.assertContains(self.client.get(self.url), "Vérifier le relais")
        fin = reverse("suivi:terminer_action_relais", args=[action.pk])
        self.assertEqual(self.client.get(fin).status_code, 405)
        self.assertEqual(self.client.post(fin).status_code, 403)
        self.u.user_permissions.add(terminer)
        self.assertRedirects(self.client.post(fin), url)
        action.refresh_from_db()
        self.assertIsNotNone(action.terminee_le)
        self.assertEqual(action.terminee_par, self.u)
        self.assertNotContains(self.client.get(self.url), "Vérifier le relais")
        self.u.user_permissions.remove(consulter)
        self.assertNotContains(self.client.get(self.url), "Actions explicitement en attente")


class QualificationTransversaleTests(TestCase):
    """Relève actuelle, indépendamment de la date métier consultée."""

    def setUp(self):
        JourTests.setUp(self)

    def test_releve_actuelle_et_regroupement_des_echeances(self):
        from datetime import timedelta
        from django.utils import timezone
        from .models import ActionRelais
        droits = Permission.objects.filter(content_type__app_label="personnes", codename__in=[
            "view_actionrelais", "view_transmission"])
        self.u.user_permissions.add(*droits)
        aujourd_hui = timezone.localdate()
        ActionRelais.objects.create(libelle="Action en retard fictive", auteur=self.u, echeance=aujourd_hui-timedelta(days=1))
        ActionRelais.objects.create(libelle="Action du jour fictive", auteur=self.u, echeance=aujourd_hui)
        ActionRelais.objects.create(libelle="Action future fictive", auteur=self.u, echeance=aujourd_hui+timedelta(days=2))
        ActionRelais.objects.create(libelle="Action sans date fictive", auteur=self.u)
        Transmission.objects.create(auteur=self.u, contenu="Transmission actuelle fictive")
        reponse = self.client.get(self.url)
        self.assertContains(reponse, "La date choisie concerne uniquement")
        self.assertContains(reponse, "Relève actuelle")
        self.assertContains(reponse, "Transmission actuelle fictive")
        for libelle in ("Action en retard fictive", "Action du jour fictive", "Action future fictive", "Action sans date fictive"):
            self.assertContains(reponse, libelle)
        self.assertContains(reponse, "En retard")
        self.assertContains(reponse, "À traiter aujourd’hui")
        self.assertContains(reponse, "À venir ou sans échéance")
        self.u.user_permissions.remove(*droits)
        reponse = self.client.get(self.url)
        for libelle in ("Action en retard fictive", "Transmission actuelle fictive"):
            self.assertNotContains(reponse, libelle)
        self.assertNotContains(reponse, "Relève actuelle —")


class RepriseServiceTests(TestCase):
    """Repères de relève, sans exposer de contrôles de clôture non autorisés."""

    def setUp(self):
        JourTests.setUp(self)

    def test_priorites_et_cloture_selon_les_droits(self):
        from .models import ActionRelais
        from django.utils import timezone
        from datetime import timedelta
        consultation = Permission.objects.get(codename="view_actionrelais", content_type__app_label="personnes")
        cloture = Permission.objects.get(codename="change_actionrelais", content_type__app_label="personnes")
        self.u.user_permissions.add(consultation)
        ActionRelais.objects.create(libelle="Relève urgente fictive", auteur=self.u, echeance=timezone.localdate()-timedelta(days=1))
        reponse = self.client.get(self.url)
        self.assertContains(reponse, "En retard (1)")
        self.assertContains(reponse, "À traiter aujourd’hui (0)")
        self.assertContains(reponse, "Relève urgente fictive")
        self.assertNotContains(reponse, "Consulter et clôturer les actions")
        self.u.user_permissions.add(cloture)
        self.assertContains(self.client.get(self.url), "Consulter et clôturer les actions")
        self.u.user_permissions.remove(consultation)
        self.assertNotContains(self.client.get(self.url), "Relève urgente fictive")
