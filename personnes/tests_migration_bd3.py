"""Reprise des accords et des journaux antérieurs, sans attribution de droits."""
from datetime import date
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MigrationBD3Tests(TransactionTestCase):
    def test_depuis_bd1_bd2_conserve_identites_et_realisations(self):
        executor = MigrationExecutor(connection)
        courant = executor.loader.graph.leaf_nodes()
        try:
            ancien = [('personnes', '0011_informations_accompagnement')]
            executor.migrate(ancien)
            apps = executor.loader.project_state(ancien).apps
            User = apps.get_model('identites', 'Utilisateur')
            u = User.objects.create(username='migration-bd3-fictive', password='!fictif')
            p = apps.get_model('personnes', 'Personne').objects.create(designation='Identité fictive conservée', cree_par_id=u.pk)
            m = apps.get_model('personnes', 'Menage').objects.create(libelle='Ménage fictif', cree_par_id=u.pk)
            a = apps.get_model('personnes', 'Accompagnement').objects.create(menage_id=m.pk, debut=date(2026,1,1), cree_par_id=u.pk)
            a.beneficiaires.add(p)
            r = apps.get_model('personnes', 'AccordRepas').objects.create(accompagnement_id=a.pk, debut=date(2026,1,1), fin=date(2026,2,1), service='dejeuner', cree_par_id=u.pk)
            r.beneficiaires.add(p)
            repas = apps.get_model('personnes', 'RepasDistribue').objects.create(accord_id=r.pk, beneficiaire_id=p.pk, date=date(2026,1,5), quantite=1, cree_par_id=u.pk)
            trace = apps.get_model('personnes', 'OperationRepas').objects.create(accord_id=r.pk, repas_id=repas.pk, action='distribue', auteur_id=u.pk, date_effet=repas.date)
            executor = MigrationExecutor(connection)
            executor.migrate(courant)
            from .models import AccordRepas, OperationRepas, EvolutionAccord
            from django.contrib.auth import get_user_model
            actuel = AccordRepas.objects.get(pk=r.pk)
            self.assertEqual(actuel.fin, date(2026,2,1))
            self.assertEqual(actuel.revision, 0)
            self.assertIsNone(actuel.annule_le)
            self.assertEqual(actuel.beneficiaires.get().pk, p.pk)
            self.assertEqual(OperationRepas.objects.get(pk=trace.pk).repas_id, repas.pk)
            self.assertFalse(EvolutionAccord.objects.exists())
            self.assertFalse(get_user_model().objects.get(pk=u.pk).user_permissions.exists())
        finally:
            MigrationExecutor(connection).migrate(courant)
