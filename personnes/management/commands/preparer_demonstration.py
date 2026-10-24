"""Préparation unique d'une base neuve du profil jetable."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from personnes.demonstration import preparer_jeu_public
from django.core.exceptions import ValidationError


class Command(BaseCommand):
    help = 'Préparer une démonstration fictive neuve, sans modifier une base existante.'

    @transaction.atomic
    def handle(self, **options):
        if not getattr(settings, 'DEMONSTRATION_PUBLIQUE', False):
            raise CommandError('Commande réservée au profil de démonstration jetable.')
        try:
            preparer_jeu_public()
        except ValidationError as erreur:
            raise CommandError(erreur.messages[0]) from erreur
        self.stdout.write('Démonstration Établissement Les Passerelles préparée ; accès publics sur la connexion.')
