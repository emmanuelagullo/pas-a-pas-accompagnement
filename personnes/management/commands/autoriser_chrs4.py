from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Attribuer explicitement tout le parcours fictif CHRS1 à CHRS4."

    def add_arguments(self,parser):parser.add_argument("identifiant")

    @transaction.atomic
    def handle(self,*args,**options):
        droits={f"{action}_{modele}" for modele,actions in {
            "situationsociale":("view","add","change"),"evenementsocial":("view","add"),
            "bilansocial":("view","add"),"operationsociale":("view",)}.items() for action in actions}
        permissions=list(Permission.objects.filter(content_type__app_label="personnes",codename__in=droits))
        if len(permissions)!=len(droits):raise CommandError("Appliquez les migrations avant cette attribution.")
        for commande in ("autoriser_chrs2","autoriser_chrs3"):
            call_command(commande,options["identifiant"],stdout=self.stdout)
        get_user_model().objects.get(username=options["identifiant"]).user_permissions.add(*permissions)
        self.stdout.write("Droits fictifs CHRS1 à CHRS4 attribués explicitement.")
