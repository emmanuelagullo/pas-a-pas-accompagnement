from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MigrationDepuisSoc4a(TransactionTestCase):
    def test_comptes_et_personnes_conserves_sans_activation_implicite(self):
        executer=MigrationExecutor(connection)
        cibles=executer.loader.graph.leaf_nodes()
        try:
            executer.migrate([("identites","0001_initial"),("personnes","0001_initial")])
            ancien=executer.loader.project_state([("identites","0001_initial"),("personnes","0001_initial")]).apps
            user=ancien.get_model("identites","Utilisateur").objects.create(username="avant-soc4b",password="empreinte-fictive-conservee")
            personne=ancien.get_model("personnes","Personne").objects.create(designation="Personne fictive avant migration",cree_par_id=user.pk)
            executer=MigrationExecutor(connection);executer.migrate(cibles)
            from .models import Utilisateur,DoubleFacteur
            from personnes.models import Personne
            self.assertEqual(Utilisateur.objects.get(pk=user.pk).password,"empreinte-fictive-conservee")
            self.assertEqual(Personne.objects.get(pk=personne.pk).cree_par_id,user.pk)
            self.assertFalse(DoubleFacteur.objects.exists())
        finally:
            MigrationExecutor(connection).migrate(cibles)
