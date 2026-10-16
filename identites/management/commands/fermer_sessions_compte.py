"""Commande technique locale ; ne crée ni rôle ni permission."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from pas_communs.authentification.sessions import fermer_sessions_compte


class Command(BaseCommand):
    help = "Fermer les sessions ouvertes d’un compte, sans modifier ses droits."

    def add_arguments(self, parser):
        parser.add_argument("nom_utilisateur")

    def handle(self, *args, **options):
        modele = get_user_model()
        try:
            compte = modele._default_manager.get_by_natural_key(options["nom_utilisateur"])
        except modele.DoesNotExist as exc:
            raise CommandError("Compte introuvable.") from exc
        nombre = fermer_sessions_compte(compte)
        self.stdout.write(f"{nombre} session(s) fermée(s).")
