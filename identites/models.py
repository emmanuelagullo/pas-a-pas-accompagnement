import uuid
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser


class Utilisateur(AbstractUser):
    """Compte professionnel ; distinct d'une personne accompagnée.

    Déclaré dès la première migration pour stabiliser AUTH_USER_MODEL.
    Aucun rôle CHRS ou lien à un établissement n'est encore implémenté.
    """


class DoubleFacteur(models.Model):
    utilisateur = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    cle_chiffree = models.TextField(blank=True)
    confirme_le = models.DateTimeField(null=True, blank=True)
    dernier_pas = models.BigIntegerField(default=0)
    revision = models.UUIDField(default=uuid.uuid4, editable=False)
    a_reinscrire = models.BooleanField(default=False)

    @property
    def inscrit(self):
        return bool(self.cle_chiffree) and self.confirme_le is not None


class CodeSecours(models.Model):
    compte = models.ForeignKey(DoubleFacteur, on_delete=models.CASCADE)
    empreinte = models.CharField(max_length=64)
    utilise_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["compte", "empreinte"], name="secours_unique_compte")]


class LimiteAuthentification(models.Model):
    # Identifiant HMAC d’un périmètre et d’une fenêtre, sans IP/identifiant en clair.
    cle = models.CharField(max_length=64, unique=True)
    expire_le = models.DateTimeField(db_index=True)
    tentatives = models.PositiveIntegerField(default=0)
