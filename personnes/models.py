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


class Menage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    libelle = models.CharField("Libellé", max_length=160, validators=[RegexValidator(r"\S", "Indiquez un libellé.")])
    cree_le = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ["libelle", "id"]
        verbose_name = "ménage"

    def __str__(self):
        return self.libelle


class Periode(models.Model):
    debut = models.DateField("Début inclus")
    fin = models.DateField("Fin exclue", null=True, blank=True)

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if self.fin and self.debut and self.fin <= self.debut:
            from django.core.exceptions import ValidationError
            raise ValidationError({"fin": "La fin doit être postérieure au début."})


class Appartenance(Periode):
    menage = models.ForeignKey(Menage, on_delete=models.PROTECT, related_name="appartenances")
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT, related_name="appartenances")

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("debut")), name="appartenance_periode_valide")]


class Accompagnement(Periode):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menage = models.ForeignKey(Menage, on_delete=models.PROTECT, related_name="accompagnements")
    beneficiaires = models.ManyToManyField(Personne, related_name="accompagnements")
    cree_le = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-debut", "id"]
        constraints = [models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("debut")), name="accompagnement_periode_valide")]


class EvenementSuivi(models.Model):
    """Audit applicatif limité, sans copie des textes ni des identités."""
    TYPES = [("menage_cree", "Ménage créé"), ("appartenance_ajoutee", "Appartenance ajoutée"), ("appartenance_close", "Appartenance close"), ("accompagnement_ouvert", "Accompagnement ouvert"), ("accompagnement_clos", "Accompagnement clos")]
    menage = models.ForeignKey(Menage, on_delete=models.PROTECT, related_name="evenements")
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, null=True)
    appartenance = models.ForeignKey(Appartenance, on_delete=models.PROTECT, null=True)
    type = models.CharField(max_length=40, choices=TYPES)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)
    date_effet = models.DateField()

    class Meta:
        ordering = ["enregistre_le", "pk"]
