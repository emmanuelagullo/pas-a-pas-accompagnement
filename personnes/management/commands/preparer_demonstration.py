"""Préparation unique d'une base neuve du profil jetable."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from personnes.demonstration import espace_metier_vide, generer, autoriser
from pas_a_pas_accompagnement.demo import IDENTIFIANT, MOT_DE_PASSE


class Command(BaseCommand):
    help = 'Préparer une démonstration fictive neuve, sans modifier une base existante.'

    @transaction.atomic
    def handle(self, **options):
        if not getattr(settings, 'DEMONSTRATION_PUBLIQUE', False):
            raise CommandError('Commande réservée au profil de démonstration jetable.')
        if get_user_model().objects.exists() or not espace_metier_vide():
            raise CommandError('Base non vide : aucune donnée modifiée.')
        compte = get_user_model().objects.create_user(IDENTIFIANT, password=MOT_DE_PASSE)
        professionnels = {nom: get_user_model().objects.create_user(nom, password=MOT_DE_PASSE,
            first_name=prenom) for nom, prenom in [('nadia', 'Nadia'), ('remi', 'Rémi'), ('camille', 'Camille')]}
        autoriser(compte)  # Compatibilité avec l'accès public historique « essai ».
        generer(compte, professionnels=professionnels)
        self.stdout.write('Démonstration Les Passerelles préparée ; accès publics sur la connexion.')
