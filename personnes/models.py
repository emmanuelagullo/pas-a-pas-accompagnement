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
    revision = models.PositiveIntegerField(default=0, editable=False)
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
    revision_sociale = models.PositiveIntegerField(default=0, editable=False)
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


class AccordRepas(Periode):
    SERVICES = [("petit_dejeuner", "Petit déjeuner"), ("dejeuner", "Déjeuner"), ("diner", "Dîner")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name="accords_repas")
    beneficiaires = models.ManyToManyField(Personne, related_name="accords_repas")
    service = models.CharField("Service de repas", max_length=20, choices=SERVICES)
    prestataire = models.CharField("Prestataire (facultatif)", max_length=160, blank=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-debut", "id"]
        verbose_name = "accord de repas"
        constraints = [models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("debut")), name="accord_repas_periode_valide")]


class RepasDistribue(models.Model):
    accord = models.ForeignKey(AccordRepas, on_delete=models.PROTECT, related_name="realisations")
    beneficiaire = models.ForeignKey(Personne, on_delete=models.PROTECT)
    date = models.DateField("Date de distribution")
    quantite = models.PositiveSmallIntegerField("Nombre de repas")
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="repas_saisis")
    cree_le = models.DateTimeField(auto_now_add=True)
    annule_le = models.DateTimeField(null=True, editable=False)
    annule_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="repas_annules")
    motif_annulation = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ["-date", "-pk"]
        verbose_name = "repas distribué"
        constraints = [
            models.CheckConstraint(condition=models.Q(quantite__gt=0), name="repas_quantite_positive"),
            models.UniqueConstraint(fields=["accord", "beneficiaire", "date"], condition=models.Q(annule_le__isnull=True), name="repas_actif_unique"),
        ]


class OperationRepas(models.Model):
    accord = models.ForeignKey(AccordRepas, on_delete=models.PROTECT, related_name="operations")
    repas = models.ForeignKey(RepasDistribue, on_delete=models.PROTECT, null=True)
    action = models.CharField(max_length=20, choices=[("accorde", "Repas accordés"), ("distribue", "Repas distribués"), ("annule", "Distribution annulée")])
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)
    date_effet = models.DateField()

    class Meta:
        ordering = ["enregistre_le", "pk"]


class AccordHebergement(Periode):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name="accords_hebergement")
    beneficiaires = models.ManyToManyField(Personne, related_name="accords_hebergement")
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("debut")), name="accord_hebergement_periode")]


class Sejour(Periode):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    accord = models.ForeignKey(AccordHebergement, on_delete=models.PROTECT, related_name="sejours")
    beneficiaires = models.ManyToManyField(Personne, related_name="sejours")
    revision = models.PositiveIntegerField(default=0, editable=False)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("debut")), name="sejour_periode")]


class LieuHebergement(models.Model):
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)
    libelle = models.CharField("Lieu / unité d’hébergement", max_length=160, validators=[RegexValidator(r"\S", "Indiquez un lieu.")])
    partenaire = models.CharField("Opérateur extérieur (facultatif)", max_length=160, blank=True)

    def __str__(self):
        return self.libelle + (" — " + self.partenaire if self.partenaire else "")


class Affectation(Periode):
    sejour = models.ForeignKey(Sejour, on_delete=models.PROTECT, related_name="affectations")
    lieu = models.ForeignKey(LieuHebergement, on_delete=models.PROTECT)

    class Meta:
        ordering = ["debut", "pk"]
        constraints = [models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("debut")), name="affectation_periode")]


class Absence(Periode):
    sejour = models.ForeignKey(Sejour, on_delete=models.PROTECT, related_name="absences")

    class Meta:
        ordering = ["debut", "pk"]
        constraints = [models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("debut")), name="absence_periode")]


class OperationHebergement(models.Model):
    accord = models.ForeignKey(AccordHebergement, on_delete=models.PROTECT, related_name="operations")
    sejour = models.ForeignKey(Sejour, on_delete=models.PROTECT, null=True)
    affectation = models.ForeignKey(Affectation, on_delete=models.PROTECT, null=True)
    absence = models.ForeignKey(Absence, on_delete=models.PROTECT, null=True)
    action = models.CharField(max_length=40)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    date_effet = models.DateField()
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["enregistre_le", "pk"]


class SituationSociale(Periode):
    DIMENSIONS = [("logement", "Logement"), ("emploi", "Emploi / formation"), ("ressources", "Ressources")]
    VALEURS = {
        "logement": [("inconnu", "Non renseigné"), ("sans_solution", "Sans solution stable"), ("hebergement", "Hébergé"), ("logement_autonome", "Logement autonome"), ("autre", "Autre situation")],
        "emploi": [("inconnu", "Non renseigné"), ("sans_emploi", "Sans emploi"), ("emploi", "En emploi"), ("formation", "En formation"), ("autre", "Autre situation")],
        "ressources": [("inconnu", "Non renseigné"), ("sans_ressources", "Sans ressources déclarées"), ("ressources_declarees", "Ressources déclarées"), ("autre", "Autre situation")],
    }
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name="situations_sociales")
    beneficiaire = models.ForeignKey(Personne, on_delete=models.PROTECT)
    dimension = models.CharField(max_length=20, choices=DIMENSIONS)
    valeur = models.CharField(max_length=30)
    source = models.CharField("Source de l’information", max_length=160)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["debut", "pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("debut")), name="situation_sociale_periode"),
            models.UniqueConstraint(fields=["accompagnement", "beneficiaire", "dimension", "debut"], name="situation_sociale_date_unique"),
            models.UniqueConstraint(fields=["accompagnement", "beneficiaire", "dimension"], condition=models.Q(fin__isnull=True), name="situation_sociale_ouverte_unique"),
        ]

    def clean(self):
        super().clean()
        if self.valeur not in dict(self.VALEURS.get(self.dimension, [])):
            from django.core.exceptions import ValidationError
            raise ValidationError({"valeur": "Choisissez une valeur de cette dimension."})

    @property
    def libelle_valeur(self):
        return dict(self.VALEURS.get(self.dimension, [])).get(self.valeur, self.valeur)


class EvenementSocial(models.Model):
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name="evenements_sociaux")
    beneficiaire = models.ForeignKey(Personne, on_delete=models.PROTECT)
    date_effet = models.DateField("Date de l’événement")
    texte = models.CharField("Événement significatif", max_length=500)
    source = models.CharField("Source de l’information", max_length=160)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)


class BilanSocial(models.Model):
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name="bilans_sociaux")
    date_effet = models.DateField("Date du bilan")
    texte = models.TextField("Bilan court", max_length=2000)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)


class OperationSociale(models.Model):
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name="operations_sociales")
    situation = models.ForeignKey(SituationSociale, on_delete=models.PROTECT, null=True)
    evenement = models.ForeignKey(EvenementSocial, on_delete=models.PROTECT, null=True)
    bilan = models.ForeignKey(BilanSocial, on_delete=models.PROTECT, null=True)
    action = models.CharField(max_length=40)
    ancienne_valeur = models.CharField(max_length=30, blank=True)
    nouvelle_valeur = models.CharField(max_length=30, blank=True)
    motif = models.CharField(max_length=240, blank=True)
    date_effet = models.DateField()
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["enregistre_le", "pk"]


class CorrectionPeriode(models.Model):
    """Avant/après typé : uniquement dates et source, jamais un dossier JSON."""
    menage = models.ForeignKey(Menage, on_delete=models.PROTECT)
    suivi = models.ForeignKey(Accompagnement, null=True, on_delete=models.PROTECT, related_name="corrections_periodes")
    accompagnement = models.ForeignKey(Accompagnement, null=True, on_delete=models.PROTECT, related_name="corrections_dates")
    appartenance = models.ForeignKey(Appartenance, null=True, on_delete=models.PROTECT)
    accord_repas = models.ForeignKey(AccordRepas, null=True, on_delete=models.PROTECT)
    accord_hebergement = models.ForeignKey(AccordHebergement, null=True, on_delete=models.PROTECT)
    sejour = models.ForeignKey(Sejour, null=True, on_delete=models.PROTECT)
    affectation = models.ForeignKey(Affectation, null=True, on_delete=models.PROTECT)
    absence = models.ForeignKey(Absence, null=True, on_delete=models.PROTECT)
    situation = models.ForeignKey(SituationSociale, null=True, on_delete=models.PROTECT)
    nature = models.CharField(max_length=30)
    ancien_debut = models.DateField()
    ancienne_fin = models.DateField(null=True)
    nouveau_debut = models.DateField()
    nouvelle_fin = models.DateField(null=True)
    ancienne_source = models.CharField(max_length=160, blank=True)
    nouvelle_source = models.CharField(max_length=160, blank=True)
    motif = models.CharField(max_length=240)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["enregistre_le", "pk"]


class RevisionTexteSocial(models.Model):
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name="revisions_textes")
    evenement = models.ForeignKey(EvenementSocial, null=True, on_delete=models.PROTECT)
    bilan = models.ForeignKey(BilanSocial, null=True, on_delete=models.PROTECT)
    ancienne_date = models.DateField()
    nouvelle_date = models.DateField()
    ancien_texte = models.TextField(max_length=2000)
    nouveau_texte = models.TextField(max_length=2000)
    ancienne_source = models.CharField(max_length=160, blank=True)
    nouvelle_source = models.CharField(max_length=160, blank=True)
    motif = models.CharField(max_length=240)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["enregistre_le", "pk"]


class Transmission(models.Model):
    """Message transversal d'équipe, distinct des dossiers individuels."""
    id = models.BigAutoField(primary_key=True)
    contenu = models.TextField()
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-cree_le", "-pk"]


class NotePartagee(models.Model):
    """Contribution libre liée à un seul objet métier."""
    id = models.BigAutoField(primary_key=True)
    contenu = models.TextField()
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT, null=True, blank=True, related_name="notes")
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, null=True, blank=True, related_name="notes")
    sejour = models.ForeignKey(Sejour, on_delete=models.PROTECT, null=True, blank=True, related_name="notes")

    class Meta:
        ordering = ["-cree_le", "-pk"]
        constraints = [models.CheckConstraint(
            condition=(
                models.Q(personne__isnull=False, accompagnement__isnull=True, sejour__isnull=True)
                | models.Q(personne__isnull=True, accompagnement__isnull=False, sejour__isnull=True)
                | models.Q(personne__isnull=True, accompagnement__isnull=True, sejour__isnull=False)
            ), name="note_exactement_une_cible")]


class RevisionContribution(models.Model):
    transmission = models.ForeignKey(Transmission, on_delete=models.PROTECT, null=True, blank=True, related_name="revisions")
    id = models.BigAutoField(primary_key=True)
    note = models.ForeignKey(NotePartagee, on_delete=models.PROTECT, null=True, blank=True, related_name="revisions")
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    date = models.DateTimeField(auto_now_add=True)
    ancien_texte = models.TextField()
    nouveau_texte = models.TextField()
    motif = models.TextField()

    class Meta:
        ordering = ["date", "pk"]
        constraints = [models.CheckConstraint(condition=(
            models.Q(transmission__isnull=False, note__isnull=True)
            | models.Q(transmission__isnull=True, note__isnull=False)), name="revision_une_cible")]


class ModeleRapport(models.Model):
    """Configuration privée de statistiques, jamais une copie des résultats."""
    id = models.BigAutoField(primary_key=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='modeles_rapports')
    nom = models.CharField(max_length=100)
    parametres = models.JSONField(default=dict)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom', 'pk']


class ActionRelais(models.Model):
    id = models.BigAutoField(primary_key=True)
    """Action explicite d'équipe, distincte d'une transmission informative."""
    libelle = models.CharField(max_length=240)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="actions_relais_creees")
    cree_le = models.DateTimeField(auto_now_add=True)
    echeance = models.DateField(null=True, blank=True)
    terminee_le = models.DateTimeField(null=True, blank=True)
    terminee_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="actions_relais_terminees")

    class Meta:
        ordering = ["echeance", "cree_le", "pk"]

