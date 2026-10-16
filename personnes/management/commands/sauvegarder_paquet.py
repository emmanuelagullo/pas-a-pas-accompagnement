import os
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from pas_communs.paquets import creer_sauvegarde
from pas_communs.local import verrouiller
from pas_a_pas_accompagnement.paquets import PROFIL


class Command(BaseCommand):
    help = "Créer un ZIP privé de l’espace fictif local, sans remplacer de fichier."

    def add_arguments(self, parser):
        parser.add_argument("destination", type=Path)

    def handle(self, *args, **options):
        destination = options["destination"].resolve()
        # Ne jamais inclure le ZIP en cours dans ses propres médias.
        if destination.is_relative_to(settings.LOCAL_DIR):
            raise CommandError("Choisissez une destination hors du dossier de données.")
        cree = False
        try:
            fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            cree = True
            with os.fdopen(fd, "wb") as sortie, verrouiller(settings.LOCAL_DIR):
                creer_sauvegarde(settings.LOCAL_DIR, sortie, profil=PROFIL)
        except (Exception, SystemExit) as erreur:
            if cree:
                destination.unlink(missing_ok=True)
            raise CommandError("Sauvegarde impossible : " + str(erreur)) from erreur
        self.stdout.write("ZIP privé créé. Conservez une copie hors appareil et vérifiez sa restauration.")
