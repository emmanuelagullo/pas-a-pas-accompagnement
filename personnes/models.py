import uuid
from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator


class Personne(models.Model):
    PRECISIONS_NAISSANCE = [("", "Non renseignée"), ("exacte", "Date exacte"),
        ("estimee", "Date estimée"), ("annee", "Année connue seulement"),
        ("annee_estimee", "Année estimée seulement")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    designation = models.CharField(
        "Nom d’usage ou identifiant provisoire", max_length=160,
        validators=[RegexValidator(r"\S", "Indiquez un nom d’usage ou un identifiant provisoire.")],
    )
    prenom = models.CharField("Prénom", max_length=100, blank=True)
    date_naissance = models.DateField("Date de naissance", null=True, blank=True)
    annee_naissance = models.PositiveSmallIntegerField("Année de naissance seule", null=True, blank=True)
    precision_naissance = models.CharField("Précision de la naissance", max_length=20,
        choices=PRECISIONS_NAISSANCE, blank=True, default="")
    revision_sociale = models.PositiveIntegerField(default=0, editable=False)
    revision_identite = models.PositiveIntegerField(default=0, editable=False)
    cree_le = models.DateTimeField("Créée le", auto_now_add=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, editable=False)

    class Meta:
        ordering = ["designation", "prenom", "id"]
        verbose_name = "personne"
        verbose_name_plural = "personnes"
        constraints = [models.CheckConstraint(
            condition=(models.Q(precision_naissance="", date_naissance__isnull=True, annee_naissance__isnull=True) |
                models.Q(precision_naissance__in=["exacte", "estimee"], date_naissance__isnull=False, annee_naissance__isnull=True) |
                models.Q(precision_naissance__in=["annee", "annee_estimee"], date_naissance__isnull=True,
                    annee_naissance__isnull=False, annee_naissance__gte=1, annee_naissance__lte=9999)),
            name="personne_naissance_coherente")]

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        erreurs = {}
        if self.date_naissance and self.date_naissance > timezone.localdate():
            erreurs["date_naissance"] = "La naissance ne peut pas être future."
        if self.annee_naissance is not None and not 1 <= self.annee_naissance <= timezone.localdate().year:
            erreurs["annee_naissance"] = "Indiquez une année passée ou l’année courante."
        if self.precision_naissance in ("exacte", "estimee"):
            if not self.date_naissance or self.annee_naissance is not None:
                erreurs["date_naissance"] = "Renseignez une date seule pour cette précision."
        elif self.precision_naissance in ("annee", "annee_estimee"):
            if self.date_naissance or self.annee_naissance is None:
                erreurs["annee_naissance"] = "Renseignez une année seule pour cette précision."
        elif self.date_naissance or self.annee_naissance is not None:
            erreurs["precision_naissance"] = "Précisez si la date ou l’année est connue ou estimée."
        if erreurs:
            raise ValidationError(erreurs)

    @property
    def naissance_affichee(self):
        if self.date_naissance:
            valeur = self.date_naissance.strftime("%d/%m/%Y")
        elif self.annee_naissance is not None:
            valeur = str(self.annee_naissance)
        else:
            return "Non renseignée"
        return f"{valeur} ({self.get_precision_naissance_display()})"

    def __str__(self):
        return " ".join(partie for partie in [self.prenom, self.designation] if partie)


class RevisionIdentite(models.Model):
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT, related_name="revisions_identite")
    ancienne_designation = models.CharField(max_length=160)
    nouvelle_designation = models.CharField(max_length=160)
    ancien_prenom = models.CharField(max_length=100, blank=True)
    nouveau_prenom = models.CharField(max_length=100, blank=True)
    ancienne_date_naissance = models.DateField(null=True, blank=True)
    nouvelle_date_naissance = models.DateField(null=True, blank=True)
    ancienne_annee_naissance = models.PositiveSmallIntegerField(null=True, blank=True)
    nouvelle_annee_naissance = models.PositiveSmallIntegerField(null=True, blank=True)
    ancienne_precision_naissance = models.CharField(max_length=20, blank=True, choices=Personne.PRECISIONS_NAISSANCE)
    nouvelle_precision_naissance = models.CharField(max_length=20, blank=True, choices=Personne.PRECISIONS_NAISSANCE)
    motif = models.CharField(max_length=240)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enregistre_le", "-pk"]


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
    fin_prevue = models.DateField("Fin prévue exclue", null=True, blank=True)
    revision_sociale = models.PositiveIntegerField(default=0, editable=False)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menage = models.ForeignKey(Menage, on_delete=models.PROTECT, related_name="accompagnements")
    beneficiaires = models.ManyToManyField(Personne, related_name="accompagnements")
    cree_le = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-debut", "id"]
        constraints = [models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("debut")), name="accompagnement_periode_valide"), models.CheckConstraint(condition=models.Q(fin_prevue__isnull=True) | models.Q(fin_prevue__gt=models.F("debut")), name="prise_fin_prevue_valide")]
        permissions = [("prolonger_accompagnement", "Prolonger la fin prévue d’une prise en charge"),
            ("corriger_prevision_accompagnement", "Corriger une prévision erronée de prise en charge")]


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
    revision = models.PositiveIntegerField(default=0, editable=False)
    annule_le = models.DateTimeField(null=True, blank=True, editable=False)
    annule_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+', editable=False)
    motif_annulation = models.CharField(max_length=240, blank=True, editable=False)
    SERVICES = [("petit_dejeuner", "Petit déjeuner"), ("dejeuner", "Déjeuner"), ("diner", "Dîner")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name="accords_repas")
    beneficiaires = models.ManyToManyField(Personne, related_name="accords_repas")
    service = models.CharField("Service de repas", max_length=20, choices=SERVICES)
    prestataire = models.CharField("Prestataire (facultatif)", max_length=160, blank=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ('prolonger_accordrepas', 'Prolonger un accord de repas'),
            ('annuler_accordrepas', 'Annuler un accord saisi par erreur'),
        ]
        ordering = ["-debut", "id"]
        verbose_name = "accord de repas"
        constraints = [models.CheckConstraint(condition=(
            models.Q(annule_le__isnull=True, annule_par__isnull=True, motif_annulation='') |
            (models.Q(annule_le__isnull=False, annule_par__isnull=False) & ~models.Q(motif_annulation=''))),
            name='accord_repas_annulation_coherente'), models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("debut")), name="accord_repas_periode_valide")]


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
    revision = models.PositiveIntegerField(default=0, editable=False)
    annule_le = models.DateTimeField(null=True, blank=True, editable=False)
    annule_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+', editable=False)
    motif_annulation = models.CharField(max_length=240, blank=True, editable=False)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name="accords_hebergement")
    beneficiaires = models.ManyToManyField(Personne, related_name="accords_hebergement")
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ('prolonger_accordhebergement', 'Prolonger un accord d’hébergement'),
            ('annuler_accordhebergement', 'Annuler un accord saisi par erreur'),
        ]
        constraints = [models.CheckConstraint(condition=(
            models.Q(annule_le__isnull=True, annule_par__isnull=True, motif_annulation='') |
            (models.Q(annule_le__isnull=False, annule_par__isnull=False) & ~models.Q(motif_annulation=''))),
            name='accord_hebergement_annulation_coherente'), models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("debut")), name="accord_hebergement_periode")]


class EvolutionAccord(models.Model):
    """Décision datée, distincte de la correction d'une erreur de saisie."""
    accord_repas = models.ForeignKey(AccordRepas, on_delete=models.PROTECT, null=True, blank=True, related_name='evolutions')
    accord_hebergement = models.ForeignKey(AccordHebergement, on_delete=models.PROTECT, null=True, blank=True, related_name='evolutions')
    action = models.CharField(max_length=20, choices=[('prolongation', 'Accord prolongé'), ('annulation', 'Accord annulé')])
    ancienne_fin = models.DateField(null=True, blank=True)
    nouvelle_fin = models.DateField(null=True, blank=True)
    motif = models.CharField(max_length=240)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['enregistre_le', 'pk']
        default_permissions = ('view',)
        constraints = [models.CheckConstraint(condition=(
            models.Q(accord_repas__isnull=False, accord_hebergement__isnull=True) |
            models.Q(accord_repas__isnull=True, accord_hebergement__isnull=False)),
            name='evolution_accord_cible_unique')]


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
    organisme = models.ForeignKey('Partenaire', on_delete=models.PROTECT, null=True, blank=True,
        related_name='lieux', verbose_name='Organisme du répertoire (facultatif)')

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(organisme__isnull=True) | models.Q(partenaire=''), name='lieu_operateur_non_ambigu')]

    def clean(self):
        super().clean()
        if self.organisme_id and self.partenaire.strip():
            from django.core.exceptions import ValidationError
            raise ValidationError({'partenaire': 'Choisissez l’organisme du répertoire ou le libellé libre, pas les deux.'})

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
    texte_document = models.JSONField(null=True, blank=True, editable=False)
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
    ancien_texte_document = models.JSONField(null=True, blank=True, editable=False)
    nouveau_texte = models.TextField(max_length=2000)
    nouveau_texte_document = models.JSONField(null=True, blank=True, editable=False)
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
    contenu_document = models.JSONField(null=True, blank=True, editable=False)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-cree_le", "-pk"]


class NotePartagee(models.Model):
    """Contribution libre liée à un seul objet métier."""
    id = models.BigAutoField(primary_key=True)
    contenu = models.TextField()
    contenu_document = models.JSONField(null=True, blank=True, editable=False)
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
    ancien_texte_document = models.JSONField(null=True, blank=True, editable=False)
    nouveau_texte = models.TextField()
    nouveau_texte_document = models.JSONField(null=True, blank=True, editable=False)
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



class InformationsAccompagnement(models.Model):
    """Versions conservées des informations pratiques et du projet de suivi."""
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name='informations')
    version = models.PositiveIntegerField()
    referent = models.CharField('Référent professionnel', max_length=160, blank=True)
    provenance = models.CharField('Provenance à l’entrée', max_length=160, blank=True)
    motif_entree = models.CharField('Motif d’entrée', max_length=160, blank=True)
    orientation_sortie = models.CharField('Orientation à la sortie', max_length=160, blank=True)
    motif_sortie = models.CharField('Motif de sortie', max_length=160, blank=True)
    destination_sortie = models.CharField('Destination à la sortie', max_length=160, blank=True)
    objectifs_courts = models.TextField('Objectifs à court terme', max_length=1000, blank=True)
    objectifs_courts_document = models.JSONField(null=True, blank=True, editable=False)
    objectifs_longs = models.TextField('Objectifs à plus long terme', max_length=1000, blank=True)
    objectifs_longs_document = models.JSONField(null=True, blank=True, editable=False)
    animaux = models.CharField('Animaux — information pratique pour l’accueil', max_length=500, blank=True)
    motif = models.CharField('Motif de mise à jour', max_length=240)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']
        constraints = [models.UniqueConstraint(fields=['accompagnement', 'version'], name='informations_suivi_version_unique')]


class EvolutionPriseEnCharge(models.Model):
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name="evolutions_prevision")
    ancienne_fin = models.DateField(null=True)
    nouvelle_fin = models.DateField(null=True, blank=True)
    action = models.CharField(max_length=20, choices=[('prolongation', 'Prolongation'), ('correction', 'Correction de prévision')], default='prolongation')
    motif = models.CharField(max_length=240)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enregistre_le", "-pk"]


class SituationPersonnelle(Periode):
    """Fait social daté par personne, indépendant des prises en charge."""
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT, related_name="situations_personnelles")
    dimension = models.CharField(max_length=20, choices=SituationSociale.DIMENSIONS)
    valeur = models.CharField(max_length=30)
    source = models.CharField(max_length=160)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["debut", "pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("debut")), name="situation_personnelle_periode"),
            models.UniqueConstraint(fields=["personne", "dimension", "debut"], name="situation_personnelle_date_unique"),
            models.UniqueConstraint(fields=["personne", "dimension"], condition=models.Q(fin__isnull=True), name="situation_personnelle_ouverte_unique"),
        ]

    def clean(self):
        super().clean()
        if self.valeur not in dict(SituationSociale.VALEURS.get(self.dimension, [])):
            from django.core.exceptions import ValidationError
            raise ValidationError({"valeur": "Choisissez une valeur de cette dimension."})

    @property
    def libelle_valeur(self):
        return dict(SituationSociale.VALEURS.get(self.dimension, [])).get(self.valeur, self.valeur)


class RevisionSituationPersonnelle(models.Model):
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT)
    situation = models.ForeignKey(SituationPersonnelle, on_delete=models.PROTECT, related_name="revisions")
    action = models.CharField(max_length=20, choices=[("changement", "Changement réel"), ("insertion", "Fait antérieur oublié"), ("correction", "Correction d’une erreur")])
    avant = models.JSONField(default=list)
    apres = models.JSONField(default=list)
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enregistre_le", "-pk"]


class CommentaireDossier(models.Model):
    """Versions immuables ; un texte vide est un effacement tracé."""
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT, null=True, blank=True, related_name="commentaires_dossier")
    menage = models.ForeignKey(Menage, on_delete=models.PROTECT, null=True, blank=True, related_name="commentaires_dossier")
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, null=True, blank=True, related_name="commentaires_dossier")
    texte = models.TextField(max_length=4000, blank=True)
    texte_document = models.JSONField(null=True, blank=True, editable=False)
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enregistre_le", "-pk"]
        constraints = [models.CheckConstraint(condition=(
            models.Q(personne__isnull=False, menage__isnull=True, accompagnement__isnull=True) |
            models.Q(personne__isnull=True, menage__isnull=False, accompagnement__isnull=True) |
            models.Q(personne__isnull=True, menage__isnull=True, accompagnement__isnull=False)), name="commentaire_cible_unique")]


class DeclarationFamiliale(Periode):
    """Déclarations individuelles, jamais déduites des appartenances au ménage."""
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT, related_name='declarations_familiales')
    situation_familiale = models.CharField('Situation familiale déclarée', max_length=160, blank=True)
    rapports_parentaux = models.CharField('Rapports avec les parents', max_length=160, blank=True)
    fratrie = models.CharField('Fratrie déclarée', max_length=160, blank=True)
    enfants_a_charge = models.PositiveSmallIntegerField('Nombre déclaré d’enfants à charge', null=True, blank=True)
    enfants_non_a_charge = models.PositiveSmallIntegerField('Nombre déclaré d’enfants non à charge', null=True, blank=True)
    grossesse = models.BooleanField('Grossesse déclarée', null=True, blank=True)
    source = models.CharField('Source de l’information', max_length=160)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-debut', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F('debut')), name='famille_periode_valide'),
            models.UniqueConstraint(fields=['personne', 'debut'], name='famille_date_unique'),
            models.UniqueConstraint(fields=['personne'], condition=models.Q(fin__isnull=True), name='famille_ouverte_unique'),
        ]

    @property
    def resume(self):
        morceaux = [self.situation_familiale] if self.situation_familiale else []
        if self.enfants_a_charge is not None:
            morceaux.append(f'{self.enfants_a_charge} enfant(s) déclaré(s) à charge')
        if self.enfants_non_a_charge is not None:
            morceaux.append(f'{self.enfants_non_a_charge} non à charge')
        return ' · '.join(morceaux) or 'Autres informations familiales renseignées'


class RevisionDeclarationFamiliale(models.Model):
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT)
    declaration = models.ForeignKey(DeclarationFamiliale, on_delete=models.PROTECT, related_name='revisions')
    action = models.CharField(max_length=20, choices=[('changement', 'Changement réel'), ('insertion', 'Fait antérieur oublié'), ('correction', 'Correction d’une erreur')])
    avant = models.JSONField(default=list)
    apres = models.JSONField(default=list)
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enregistre_le', '-pk']


class CoordonneesPersonnelles(Periode):
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT, related_name='coordonnees')
    rue = models.CharField('Adresse déclarée — rue et complément', max_length=240, blank=True)
    code_postal = models.CharField('Code postal', max_length=20, blank=True)
    ville = models.CharField('Ville', max_length=160, blank=True)
    pays = models.CharField('Pays', max_length=160, blank=True)
    telephone = models.CharField('Téléphone', max_length=80, blank=True)
    courriel = models.EmailField('Courriel', blank=True)
    fax = models.CharField('Fax (si utile)', max_length=80, blank=True)
    source = models.CharField('Source de l’information', max_length=160)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-debut', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F('debut')), name='coordonnees_periode_valide'),
            models.UniqueConstraint(fields=['personne', 'debut'], name='coordonnees_date_unique'),
            models.UniqueConstraint(fields=['personne'], condition=models.Q(fin__isnull=True), name='coordonnees_ouverte_unique'),
        ]

    @property
    def adresse(self):
        return ' · '.join(x for x in [self.rue, ' '.join(x for x in [self.code_postal, self.ville] if x), self.pays] if x)


class RevisionCoordonneesPersonnelles(models.Model):
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT)
    coordonnees = models.ForeignKey(CoordonneesPersonnelles, on_delete=models.PROTECT, related_name='revisions')
    action = models.CharField(max_length=20, choices=RevisionDeclarationFamiliale._meta.get_field('action').choices)
    avant = models.JSONField(default=list)
    apres = models.JSONField(default=list)
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enregistre_le', '-pk']


class ContactMenage(Periode):
    menage = models.ForeignKey(Menage, on_delete=models.PROTECT, related_name='contacts_designes')
    contact = models.ForeignKey(Personne, on_delete=models.PROTECT, null=True, blank=True,
        related_name='designations_contact', verbose_name='Personne de contact')
    source = models.CharField('Source de la désignation', max_length=160)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-debut', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F('debut')), name='contact_menage_periode_valide'),
            models.UniqueConstraint(fields=['menage', 'debut'], name='contact_menage_date_unique'),
            models.UniqueConstraint(fields=['menage'], condition=models.Q(fin__isnull=True), name='contact_menage_ouvert_unique'),
        ]


class RevisionContactMenage(models.Model):
    menage = models.ForeignKey(Menage, on_delete=models.PROTECT)
    designation = models.ForeignKey(ContactMenage, on_delete=models.PROTECT, related_name='revisions')
    action = models.CharField(max_length=20, choices=RevisionDeclarationFamiliale._meta.get_field('action').choices)
    avant = models.JSONField(default=list)
    apres = models.JSONField(default=list)
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enregistre_le', '-pk']


class Partenaire(models.Model):
    """Organisation ou service stable ; la fiche datée porte ses renseignements."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    libelle = models.CharField(max_length=160)
    revision = models.PositiveIntegerField(default=0, editable=False)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['libelle', 'pk']

    def __str__(self):
        return self.libelle


class FichePartenaire(Periode):
    partenaire = models.ForeignKey(Partenaire, on_delete=models.PROTECT, related_name='fiches')
    nom = models.CharField('Nom de l’organisme ou du service', max_length=160, validators=[RegexValidator(r'\S', 'Indiquez un nom.')])
    rue = models.CharField('Adresse — rue et complément', max_length=240, blank=True)
    code_postal = models.CharField('Code postal', max_length=20, blank=True)
    ville = models.CharField('Ville', max_length=160, blank=True)
    pays = models.CharField('Pays', max_length=160, blank=True)
    telephone = models.CharField('Téléphone', max_length=80, blank=True)
    courriel = models.EmailField('Courriel', blank=True)
    fax = models.CharField('Fax (si utile)', max_length=80, blank=True)
    informations = models.TextField('Informations pratiques', max_length=1000, blank=True)
    source = models.CharField('Source de l’information', max_length=160)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-debut', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F('debut')), name='fiche_partenaire_periode_valide'),
            models.UniqueConstraint(fields=['partenaire', 'debut'], name='fiche_partenaire_date_unique'),
            models.UniqueConstraint(fields=['partenaire'], condition=models.Q(fin__isnull=True), name='fiche_partenaire_ouverte_unique'),
        ]


class RevisionFichePartenaire(models.Model):
    partenaire = models.ForeignKey(Partenaire, on_delete=models.PROTECT)
    fiche = models.ForeignKey(FichePartenaire, on_delete=models.PROTECT, related_name='revisions')
    action = models.CharField(max_length=20, choices=RevisionDeclarationFamiliale._meta.get_field('action').choices)
    avant = models.JSONField(default=list)
    apres = models.JSONField(default=list)
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enregistre_le', '-pk']


class Intervenant(models.Model):
    """Professionnel stable, distinct d’un compte et d’une personne accompagnée."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    libelle = models.CharField(max_length=160)
    revision = models.PositiveIntegerField(default=0, editable=False)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['libelle', 'pk']

    def __str__(self):
        return self.libelle


class FicheIntervenant(Periode):
    intervenant = models.ForeignKey(Intervenant, on_delete=models.PROTECT, related_name='fiches')
    nom = models.CharField('Nom du professionnel', max_length=160, validators=[RegexValidator(r'\S', 'Indiquez un nom.')])
    fonction = models.CharField('Fonction', max_length=160, blank=True)
    organisme = models.ForeignKey(Partenaire, on_delete=models.PROTECT, null=True, blank=True, related_name='professionnels', verbose_name='Organisme ou service')
    telephone = models.CharField('Téléphone professionnel', max_length=80, blank=True)
    courriel = models.EmailField('Courriel professionnel', blank=True)
    fax = models.CharField('Fax (si utile)', max_length=80, blank=True)
    source = models.CharField('Source de l’information', max_length=160)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-debut', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F('debut')), name='fiche_intervenant_periode'),
            models.UniqueConstraint(fields=['intervenant', 'debut'], name='fiche_intervenant_date'),
            models.UniqueConstraint(fields=['intervenant'], condition=models.Q(fin__isnull=True), name='fiche_intervenant_ouverte')]


class RevisionFicheIntervenant(models.Model):
    intervenant = models.ForeignKey(Intervenant, on_delete=models.PROTECT)
    fiche = models.ForeignKey(FicheIntervenant, on_delete=models.PROTECT, related_name='revisions')
    action = models.CharField(max_length=20, choices=RevisionDeclarationFamiliale._meta.get_field('action').choices)
    avant = models.JSONField(default=list)
    apres = models.JSONField(default=list)
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enregistre_le', '-pk']


class AffectationIntervenant(Periode):
    ROLES = [('referent', 'Référent professionnel'), ('orienteur', 'Service orienteur'),
        ('suivi_exterieur', 'Suivi social extérieur'), ('prescripteur', 'Prescripteur')]
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name='interventions')
    role = models.CharField('Rôle dans cette prise', max_length=30, choices=ROLES)
    intervenant = models.ForeignKey(Intervenant, on_delete=models.PROTECT, null=True, blank=True)
    organisme = models.ForeignKey(Partenaire, on_delete=models.PROTECT, null=True, blank=True)
    source = models.CharField('Source de l’affectation', max_length=160)
    annule_le = models.DateTimeField(null=True, blank=True, editable=False)
    annule_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+', editable=False)
    motif_annulation = models.CharField(max_length=240, blank=True, editable=False)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-debut', '-pk']
        permissions = [('annuler_affectationintervenant', 'Annuler une affectation professionnelle saisie par erreur')]
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F('debut')), name='intervention_periode'),
            models.CheckConstraint(condition=(models.Q(intervenant__isnull=False, organisme__isnull=True) | models.Q(intervenant__isnull=True, organisme__isnull=False)), name='intervention_cible_unique'),
            models.CheckConstraint(condition=models.Q(annule_le__isnull=True,annule_par__isnull=True,motif_annulation='') | (models.Q(annule_le__isnull=False,annule_par__isnull=False) & ~models.Q(motif_annulation='')), name='intervention_annulation_coherente')]


class RevisionAffectationIntervenant(models.Model):
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT)
    affectation = models.ForeignKey(AffectationIntervenant, on_delete=models.PROTECT, related_name='revisions')
    action = models.CharField(max_length=20, choices=[('ajout', 'Affectation'), ('insertion', 'Fait antérieur oublié'), ('correction', 'Correction'), ('cloture', 'Fin de mission'), ('annulation','Annulation de saisie erronée')])
    avant = models.JSONField(default=dict)
    apres = models.JSONField(default=dict)
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enregistre_le', '-pk']
