from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Attribuer volontairement les décisions BD3 au compte choisi, sans administration ni suppression.'

    def add_arguments(self, parser):
        parser.add_argument('identifiant')

    @transaction.atomic
    def handle(self, *args, **options):
        droits = {'prolonger_accordrepas', 'annuler_accordrepas', 'prolonger_accordhebergement',
                  'annuler_accordhebergement', 'view_evolutionaccord'}
        permissions = list(Permission.objects.filter(content_type__app_label='personnes', codename__in=droits))
        if len(permissions) != len(droits):
            raise CommandError('Appliquez les migrations avant cette attribution.')
        try:
            compte = get_user_model().objects.get(username=options['identifiant'])
        except get_user_model().DoesNotExist as exc:
            raise CommandError('Compte inconnu ; aucune création de compte ni attribution effectuée.') from exc
        # Deliberately do not widen any consultation or creation rights.
        compte.user_permissions.add(*permissions)
        self.stdout.write('Décisions BD3 attribuées ; les droits de consultation requis restent indépendants.')
