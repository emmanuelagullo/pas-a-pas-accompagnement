from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

class Command(BaseCommand):
    help='Accorder explicitement les permissions du parcours collectif à un compte existant.'
    def add_arguments(self,parser):parser.add_argument('compte')
    def handle(self,compte,**options):
        try:u=get_user_model().objects.get(username=compte,is_active=True)
        except get_user_model().DoesNotExist:raise CommandError('Compte actif introuvable.')
        noms=('compositioncollective','prestationcollective','versionprestationcollective','couvertcollectif','mouvementcollectif','journalcollectif')
        permissions=Permission.objects.filter(content_type__app_label='personnes',content_type__model__in=noms)
        u.user_permissions.add(*permissions)
        u.user_permissions.add(*Permission.objects.filter(content_type__app_label='acteurs',codename='view_tarifoffre'))
        self.stdout.write('Permissions collectives ajoutées ; les habilitations et portées par service restent nécessaires si le contrôle est actif.')
