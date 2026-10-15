import uuid
from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator


class Personne(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    designation = models.CharField(
        "Nom d’usage ou identifiant provisoire", max_length=160,
        validators=[RegexValidator(r"\S", "Indiquez un nom d’usage ou un identifiant provisoire.")],
    )
    prenom = models.CharField("Prénom", max_length=100, blank=True)
    cree_le = models.DateTimeField("Créée le", auto_now_add=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, editable=False)

    class Meta:
        ordering = ["designation", "prenom", "id"]
        verbose_name = "personne"
        verbose_name_plural = "personnes"

    def __str__(self):
        return " ".join(partie for partie in [self.prenom, self.designation] if partie)
