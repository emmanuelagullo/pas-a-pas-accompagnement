from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

DROITS = {'view_situationpersonnelle', 'add_situationpersonnelle', 'change_situationpersonnelle',
          'view_revisionsituationpersonnelle', 'view_commentairedossier', 'add_commentairedossier',
          'prolonger_accompagnement', 'view_evolutionpriseencharge'}


class Command(BaseCommand):
    help = 'Attribuer volontairement les droits BD6 ; les droits métier existants restent indépendants.'

    def add_arguments(self, parser):
        parser.add_argument('identifiant')

    @transaction.atomic
    def handle(self, *args, **options):
        permissions = list(Permission.objects.filter(content_type__app_label='personnes', codename__in=DROITS))
        if len(permissions) != len(DROITS):
            raise CommandError('Appliquez les migrations avant cette attribution.')
        try:
            compte = get_user_model().objects.get(username=options['identifiant'])
        except get_user_model().DoesNotExist as exc:
            raise CommandError('Compte inconnu ; aucun compte créé.') from exc
        compte.user_permissions.add(*permissions)
        self.stdout.write('Droits BD6 attribués explicitement, sans suppression ni droits d’administration.')
