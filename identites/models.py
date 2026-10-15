from django.contrib.auth.models import AbstractUser


class Utilisateur(AbstractUser):
    """Compte professionnel ; distinct d'une personne accompagnée.

    Déclaré dès la première migration pour stabiliser AUTH_USER_MODEL.
    Aucun rôle CHRS ou lien à un établissement n'est encore implémenté.
    """
