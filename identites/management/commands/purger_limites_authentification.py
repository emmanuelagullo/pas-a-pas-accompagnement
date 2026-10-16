from django.core.management.base import BaseCommand
from django.utils import timezone
from identites.models import LimiteAuthentification


class Command(BaseCommand):
    help = "Supprimer les fenêtres de limitation expirées, sans lever les blocages actuels."

    def handle(self,*args,**options):
        nombre,_=LimiteAuthentification.objects.filter(expire_le__lte=timezone.now()).delete()
        self.stdout.write(f"{nombre} fenêtre(s) expirée(s) supprimée(s).")
