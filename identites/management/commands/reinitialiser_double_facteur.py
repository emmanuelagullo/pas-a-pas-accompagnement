import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pas_communs.authentification.sessions import fermer_sessions_compte
from identites.double_facteur import reinitialiser
from identites.configuration import disponible

logger = logging.getLogger("identites.securite")


class Command(BaseCommand):
    help = "Révoquer le second facteur et les sessions après vérification humaine du compte."

    def add_arguments(self,parser):
        parser.add_argument("nom_utilisateur")
        parser.add_argument("--confirmer",action="store_true")
        parser.add_argument("--profil-sans-2fa",action="store_true",
            help="Retirer explicitement le 2FA pour un profil local ou désactivé, sans réinscription.")

    def handle(self,*args,**options):
        if not options["confirmer"]:
            raise CommandError("Vérifier l’identité hors application, puis ajouter --confirmer.")
        retirer = options["profil_sans_2fa"]
        if retirer and not (settings.MODE_LOCAL or settings.DOUBLE_FACTEUR_POLITIQUE == "desactive"):
            raise CommandError("--profil-sans-2fa est réservé aux profils locaux ou désactivés.")
        if not retirer and not disponible():
            raise CommandError("Activez d’abord un profil 2FA utilisable, ou choisissez explicitement --profil-sans-2fa dans un profil autorisé.")
        modele=get_user_model()
        try:
            utilisateur=modele._default_manager.get_by_natural_key(options["nom_utilisateur"])
        except modele.DoesNotExist as exc:
            raise CommandError("Compte introuvable.") from exc
        with transaction.atomic():
            reinitialiser(utilisateur,a_reinscrire=not retirer)
            nombre=fermer_sessions_compte(utilisateur)
        logger.warning("auth.recuperation_terminal compte=%s reinscription=%s sessions=%s",utilisateur.pk,not retirer,nombre)
        self.stdout.write("Second facteur et secours révoqués ; sessions fermées. " +
            ("Protection 2FA explicitement retirée dans ce profil." if retirer else "Réinscription obligatoire à la prochaine connexion."))
