"""Préparation unique d'une base neuve du profil jetable."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from personnes.models import Personne
from pas_a_pas_accompagnement.demo import IDENTIFIANT, MOT_DE_PASSE


class Command(BaseCommand):
    help = 'Préparer une démonstration fictive neuve, sans modifier une base existante.'

    @transaction.atomic
    def handle(self, **options):
        if not getattr(settings, 'DEMONSTRATION_PUBLIQUE', False):
            raise CommandError('Commande réservée au profil de démonstration jetable.')
        if get_user_model().objects.exists() or Personne.objects.exists():
            raise CommandError('Base non vide : aucune donnée modifiée.')
        droits = list(Permission.objects.filter(content_type__app_label='personnes',
            content_type__model='personne', codename__in=['view_personne', 'add_personne']))
        if len(droits) != 2:
            raise CommandError('Appliquer les migrations avant la préparation.')
        compte = get_user_model().objects.create_user(IDENTIFIANT, password=MOT_DE_PASSE)
        compte.user_permissions.set(droits)
        Personne.objects.create(designation='Personne fictive A', cree_par=compte)
        self.stdout.write('Démonstration fictive préparée ; identifiants publics sur la connexion.')
