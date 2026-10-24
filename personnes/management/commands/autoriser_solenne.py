from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

DROITS = {'view_declarationfamiliale', 'add_declarationfamiliale', 'change_declarationfamiliale',
    'view_revisiondeclarationfamiliale', 'corriger_prevision_accompagnement', 'view_evolutionpriseencharge',
    'view_coordonneespersonnelles', 'add_coordonneespersonnelles', 'change_coordonneespersonnelles',
    'view_revisioncoordonneespersonnelles', 'view_contactmenage', 'add_contactmenage',
    'change_contactmenage', 'view_revisioncontactmenage'}


class Command(BaseCommand):
    help = 'Attribuer volontairement les droits livrés de reprise Solenne à un compte existant ; les droits CHRS restent indépendants.'

    def add_arguments(self, parser):
        parser.add_argument('identifiant')

    @transaction.atomic
    def handle(self, *args, **options):
        permissions = list(Permission.objects.filter(content_type__app_label='personnes', codename__in=DROITS))
        if len(permissions) != len(DROITS):
            raise CommandError('Appliquez les migrations avant cette attribution.')
        try:
            compte = get_user_model().objects.get(username=options['identifiant'])
        except get_user_model().DoesNotExist as erreur:
            raise CommandError('Compte inconnu ; aucun compte créé.') from erreur
        compte.user_permissions.add(*permissions)
        self.stdout.write('Droits Solenne attribués explicitement, sans administration ni suppression.')
