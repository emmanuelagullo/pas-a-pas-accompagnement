from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Attribuer explicitement les droits du parcours fictif CHRS1 et CHRS2."

    def add_arguments(self, parser):
        parser.add_argument("identifiant")

    @transaction.atomic
    def handle(self, *args, **options):
        droits = {"view_accordrepas", "add_accordrepas", "view_repasdistribue", "add_repasdistribue", "change_repasdistribue", "view_operationrepas"}
        permissions = list(Permission.objects.filter(content_type__app_label="personnes", codename__in=droits))
        if len(permissions) != len(droits):
            raise CommandError("Appliquez les migrations avant cette attribution.")
        call_command("autoriser_chrs1", options["identifiant"], stdout=self.stdout)
        get_user_model().objects.get(username=options["identifiant"]).user_permissions.add(*permissions)
        self.stdout.write("Droits du parcours fictif CHRS2 attribués explicitement.")
