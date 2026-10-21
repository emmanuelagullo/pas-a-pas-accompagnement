from io import StringIO
from unittest.mock import patch
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from . import tests_navigation, informations_suivi as service
from .models import InformationsAccompagnement


class InformationsTests(TestCase):
    def setUp(self):
        tests_navigation.NavigationTests.setUp(self)
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        self.u = type(self.u).objects.get(pk=self.u.pk)
        self.client.force_login(self.u)

    def donnees(self, **kw):
        valeurs = {champ: '' for champ in service.CHAMPS}
        valeurs.update(referent='Référente extérieure fictive', provenance='Famille fictive', motif_entree='Mise à l’abri')
        valeurs.update(kw)
        return valeurs

    def enregistrer(self, **kw):
        return service.enregistrer(self.u, self.a, service.jeton(self.a, self.a.informations.first()),
            'Information précisée', **self.donnees(**kw))

    def test_versions_distinctes_sans_changer_auteur_du_suivi(self):
        ancien_auteur = self.a.cree_par_id
        premiere = self.enregistrer()
        seconde = self.enregistrer(orientation_sortie='Relais fictif', destination_sortie='Logement fictif')
        self.assertEqual(list(self.a.informations.values_list('version', flat=True)), [2, 1])
        premiere.refresh_from_db()
        self.assertEqual(premiere.orientation_sortie, '')
        self.assertEqual(seconde.referent, 'Référente extérieure fictive')
        self.a.refresh_from_db()
        self.assertEqual(self.a.cree_par_id, ancien_auteur)
        self.assertIsNone(self.a.fin)
        self.assertEqual(self.a.beneficiaires.count(), 1)

    def test_perime_aucun_changement_et_rollback(self):
        attendu = service.jeton(self.a, None)
        self.enregistrer()
        with self.assertRaises(ValidationError):
            service.enregistrer(self.u, self.a, attendu, 'Périmé', **self.donnees(referent='Autre'))
        with self.assertRaises(ValidationError): self.enregistrer()
        with patch.object(InformationsAccompagnement, 'save', side_effect=RuntimeError('échec fictif')):
            with self.assertRaises(RuntimeError): self.enregistrer(referent='À annuler')
        self.assertEqual(self.a.informations.count(), 1)

    def test_formulaire_et_droits_historique(self):
        url = reverse('suivi:informations', args=[self.a.pk])
        self.assertContains(self.client.get(url), 'Référent professionnel')
        valeurs = self.donnees(motif='Accueil fictif', attendu=service.jeton(self.a, None))
        self.assertRedirects(self.client.post(url, valeurs), reverse('suivi:accompagnement', args=[self.a.pk]))
        page = self.client.get(reverse('suivi:accompagnement', args=[self.a.pk]))
        self.assertContains(page, 'Référente extérieure fictive')
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, valeurs).status_code, 403)
        with self.assertRaises(PermissionDenied):
            service.enregistrer(type(self.u).objects.get(pk=self.u.pk), self.a, '', 'Refus', **self.donnees())

    def test_informations_inaccessibles_sans_droit_specifique(self):
        self.enregistrer(objectifs_courts='<script>fictif</script>')
        url = reverse('suivi:accompagnement', args=[self.a.pk])
        self.assertNotContains(self.client.get(url), '<script>fictif</script>')
        self.u.user_permissions.remove(*self.u.user_permissions.filter(codename='view_informationsaccompagnement'))
        self.assertNotContains(self.client.get(url), 'Référente extérieure fictive')


from django.test import TransactionTestCase


class ConcurrenceInformations(TransactionTestCase):
    def test_une_seule_version_pour_deux_formulaires_identiques(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections, OperationalError
        InformationsTests.setUp(self)
        attendu = service.jeton(self.a, None)
        barriere = Barrier(2)
        def ecrire(referent):
            close_old_connections()
            try:
                acteur = type(self.u).objects.get(pk=self.u.pk)
                acteur.get_all_permissions()
                barriere.wait(10)
                valeurs = {champ: '' for champ in service.CHAMPS}
                valeurs['referent'] = referent
                try:
                    service.enregistrer(acteur, self.a, attendu, 'Fictif concurrent', **valeurs)
                    return True
                except (ValidationError, OperationalError):
                    return False
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultats = list(pool.map(ecrire, ['Référent A', 'Référent B']))
        self.assertEqual(sum(resultats), 1)
        self.assertEqual(InformationsAccompagnement.objects.count(), 1)
