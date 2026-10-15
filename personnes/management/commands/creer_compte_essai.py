"""Compte ordinaire pour l'espace fictif #SOC1, sans rôle métier implicite."""
from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Créer un compte d’essai avec lecture et création des personnes fictives."

    def add_arguments(self, parser):
        parser.add_argument("identifiant")

    def handle(self, *args, **options):
        utilisateur = get_user_model()(username=options["identifiant"])
        try:
            utilisateur.full_clean(exclude=["password"])
        except ValidationError as erreur:
            raise CommandError("Identifiant indisponible ou invalide.") from erreur
        mot_de_passe = getpass("Mot de passe (12 caractères minimum) : ")
        confirmation = getpass("Confirmer le mot de passe : ")
        if mot_de_passe != confirmation:
            raise CommandError("Les mots de passe ne correspondent pas.")
        try:
            validate_password(mot_de_passe, utilisateur)
        except ValidationError as erreur:
            raise CommandError(" ".join(erreur.messages)) from erreur
        with transaction.atomic():
            permissions = list(Permission.objects.filter(
                content_type__app_label="personnes", content_type__model="personne",
                codename__in=["view_personne", "add_personne"],
            ))
            if len(permissions) != 2:
                raise CommandError("Appliquez les migrations avant de créer le compte.")
            utilisateur.set_password(mot_de_passe)
            utilisateur.save()
            utilisateur.user_permissions.set(permissions)
        self.stdout.write(self.style.SUCCESS(
            "Compte d’essai créé. Il peut consulter et créer les personnes fictives."
        ))
