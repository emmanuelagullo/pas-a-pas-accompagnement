from pathlib import Path
import shutil
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from pas_a_pas_accompagnement.paquets import verifier


class Command(BaseCommand):
    help = "Vérifier un ZIP du prototype sans modifier les données courantes."

    def add_arguments(self, parser):
        parser.add_argument("source", type=Path)

    def handle(self, *args, **options):
        try:
            preparation = verifier(options["source"], settings.LOCAL_DIR.parent)
        except Exception as erreur:
            raise CommandError("Sauvegarde refusée : " + str(erreur)) from erreur
        try:
            self.stdout.write(f"Sauvegarde valide ; {preparation.nombre_medias} média(s). Aucune donnée courante modifiée.")
        finally:
            shutil.rmtree(preparation.etape)
