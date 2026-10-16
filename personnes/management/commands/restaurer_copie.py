from pathlib import Path
import shutil
from django.core.management.base import BaseCommand, CommandError
from pas_a_pas_accompagnement.paquets import verifier, installer_copie


class Command(BaseCommand):
    help = "Restaurer un ZIP vers un NOUVEAU dossier, sans remplacer l’espace courant."

    def add_arguments(self, parser):
        parser.add_argument("source", type=Path)
        parser.add_argument("destination", type=Path)

    def handle(self, *args, **options):
        destination = options["destination"].absolute()
        if destination.exists() or destination.is_symlink():
            raise CommandError("La destination doit être un nouveau dossier.")
        preparation = None
        try:
            preparation = verifier(options["source"], destination.parent)
            installer_copie(preparation, destination)
        except Exception as erreur:
            if preparation is not None and preparation.etape.exists():
                shutil.rmtree(preparation.etape)
            raise CommandError("Restauration refusée : " + str(erreur)) from erreur
        self.stdout.write("Copie indépendante restaurée ; reconnexion nécessaire avec un compte de la copie.")
