"""Attribution explicite des droits du parcours fictif CHRS1."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError

DROITS = {
    "view_personne", "view_menage", "add_menage", "add_appartenance",
    "change_appartenance", "view_accompagnement", "add_accompagnement",
    "change_accompagnement", "view_evenementsuivi",
}


class Command(BaseCommand):
    help = "Autoriser explicitement un compte existant au parcours fictif CHRS1."

    def add_arguments(self, parser):
        parser.add_argument("identifiant")

    def handle(self, *args, **options):
        try:
            compte = get_user_model().objects.get(username=options["identifiant"])
        except get_user_model().DoesNotExist as erreur:
            raise CommandError("Compte introuvable.") from erreur
        droits = list(Permission.objects.filter(content_type__app_label="personnes", codename__in=DROITS))
        if len(droits) != len(DROITS):
            raise CommandError("Appliquez les migrations avant cette attribution.")
        compte.user_permissions.add(*droits)
        self.stdout.write("Droits du parcours fictif CHRS1 attribués explicitement.")
