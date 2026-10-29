from acteurs.managers import ModeleControle, ManagerControle, controler_manager
import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator


class TraceSaisie(ModeleControle):
    contexte_saisie = models.CharField('Contexte de saisie', max_length=240, blank=True)

    class Meta:
        abstract = True
        ordering = ['-enregistre_le', '-pk']

    def save(self, *args, **kwargs):
        if self._state.adding and not self.contexte_saisie:
            from .saisie_sociale import contexte_courant
            self.contexte_saisie = contexte_courant()
        return super().save(*args, **kwargs)


class Personne(ModeleControle):
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


class RevisionIdentite(TraceSaisie):
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
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enregistre_le", "-pk"]


class Menage(ModeleControle):
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


class Periode(ModeleControle):
    debut = models.DateField("Début inclus")
    fin = models.DateField("Fin exclue", null=True, blank=True)

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if self.fin and self.debut and self.fin <= self.debut:
            from django.core.exceptions import ValidationError
            raise ValidationError({"fin": "La fin doit être postérieure au début."})


class ChronologiesActives(models.Manager):
    """La consultation ordinaire exclut les changements retirés, jamais détruits."""
    def get_queryset(self):
        return super().get_queryset().filter(retire_le__isnull=True)


class PeriodeRetirable(Periode):
    retire_le = models.DateTimeField(null=True, blank=True, editable=False)
    objects = controler_manager(ChronologiesActives())
    tous = ManagerControle()

    class Meta:
        abstract = True


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


class EvenementSuivi(ModeleControle):
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
    jours_semaine=models.JSONField('Jours autorisés de la semaine',default=list,blank=True)
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

    def clean(self):
        super().clean()
        if not isinstance(self.jours_semaine,list) or any(type(j)!=int or j not in range(7) for j in self.jours_semaine) or len(set(self.jours_semaine))!=len(self.jours_semaine):
            raise ValidationError({'jours_semaine':'Choisissez des jours distincts de lundi à dimanche.'})

    def jours_affiches(self):
        jours=['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche']
        return ', '.join(jours[j] for j in self.jours_semaine) if self.jours_semaine else 'Tous les jours'


class RepasDistribue(ModeleControle):
    accord = models.ForeignKey(AccordRepas, on_delete=models.PROTECT, related_name="realisations")
    beneficiaire = models.ForeignKey(Personne, on_delete=models.PROTECT)
    date = models.DateField("Date de distribution")
    quantite = models.PositiveSmallIntegerField("Nombre de repas")
    categorie_declaree=models.CharField('Catégorie déclarée',max_length=80,blank=True)
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


class OperationRepas(ModeleControle):
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


class EvolutionAccord(ModeleControle):
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


class SejourQuerySet(models.QuerySet):
    def non_annules(self):return self.filter(annule_le__isnull=True)


class Sejour(Periode):
    objects=controler_manager(SejourQuerySet.as_manager())
    annule_le=models.DateTimeField(null=True,blank=True,editable=False)
    annule_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,related_name='+',editable=False)
    motif_annulation=models.CharField(max_length=240,blank=True,editable=False)
    remplace_sejour=models.ForeignKey('self',on_delete=models.PROTECT,null=True,blank=True,related_name='remplacements',editable=False)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    origine_collective=models.ForeignKey('self',null=True,blank=True,on_delete=models.PROTECT,related_name='continuations',editable=False)
    accord = models.ForeignKey(AccordHebergement, on_delete=models.PROTECT, related_name="sejours")
    beneficiaires = models.ManyToManyField(Personne, related_name="sejours")
    revision = models.PositiveIntegerField(default=0, editable=False)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions=[('annuler_sejour','Annuler une arrivée entièrement saisie par erreur')]
        constraints = [models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("debut")), name="sejour_periode"),models.CheckConstraint(condition=models.Q(annule_le__isnull=True,annule_par__isnull=True,motif_annulation='')|(models.Q(annule_le__isnull=False,annule_par__isnull=False)&~models.Q(motif_annulation='')),name='sejour_annulation_coherente')]


class AnnulationArrivee(ModeleControle):
    origine=models.OneToOneField(Sejour,on_delete=models.PROTECT,related_name='retrait_arrivee')
    motif=models.CharField(max_length=240)
    avant=models.JSONField()
    apres=models.JSONField()
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions=('view','add')
        ordering=['-pk']


class LieuHebergement(ModeleControle):
    revision_sociale=models.PositiveIntegerField(default=0,editable=False)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)
    libelle = models.CharField("Lieu / unité d’hébergement", max_length=160, validators=[RegexValidator(r"\S", "Indiquez un lieu.")])
    parent=models.ForeignKey('self',on_delete=models.PROTECT,null=True,blank=True,related_name='sous_lieux')
    niveau=models.CharField('Type de lieu',max_length=16,blank=True,choices=[('etablissement','Établissement'),('batiment','Bâtiment'),('logement','Logement'),('chambre','Chambre'),('place','Place')])
    partenaire = models.CharField("Opérateur extérieur (facultatif)", max_length=160, blank=True)
    organisme = models.ForeignKey('Partenaire', on_delete=models.PROTECT, null=True, blank=True,
        related_name='lieux', verbose_name='Organisme du répertoire (facultatif)')

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(organisme__isnull=True) | models.Q(partenaire=''), name='lieu_operateur_non_ambigu')]

    def clean(self):
        super().clean()
        self.verifier_arbre()
        if self.organisme_id and self.partenaire.strip():
            from django.core.exceptions import ValidationError
            raise ValidationError({'partenaire': 'Choisissez l’organisme du répertoire ou le libellé libre, pas les deux.'})

    def verifier_arbre(self):
        p=self.parent;vus={self.pk}
        while p:
            if p.pk in vus:raise ValidationError({'parent':'La hiérarchie ne peut pas former une boucle.'})
            vus.add(p.pk);p=p.parent

    def chemin(self):
        vals=[self.libelle];p=self.parent;vus={self.pk}
        while p and p.pk not in vus:
            vus.add(p.pk);vals.append(p.libelle);p=p.parent
        return ' / '.join(reversed(vals))

    def __str__(self):
        return self.chemin() + (" — " + self.partenaire if self.partenaire else "")


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


class OperationHebergement(ModeleControle):
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


class EvenementSocial(ModeleControle):
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name="evenements_sociaux")
    beneficiaire = models.ForeignKey(Personne, on_delete=models.PROTECT)
    date_effet = models.DateField("Date de l’événement")
    texte = models.CharField("Événement significatif", max_length=500)
    source = models.CharField("Source de l’information", max_length=160)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)


class BilanSocial(ModeleControle):
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name="bilans_sociaux")
    date_effet = models.DateField("Date du bilan")
    texte = models.TextField("Bilan court", max_length=2000)
    texte_document = models.JSONField(null=True, blank=True, editable=False)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)


class OperationSociale(ModeleControle):
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


class CorrectionPeriode(ModeleControle):
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
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["enregistre_le", "pk"]


class RevisionTexteSocial(ModeleControle):
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
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["enregistre_le", "pk"]


class Transmission(ModeleControle):
    fil_cle=models.CharField(max_length=160,blank=True,default='',db_index=True,editable=False)
    cle_envoi=models.UUIDField(null=True,blank=True,unique=True,editable=False)
    date_fait=models.DateField("Date de la contribution (si connue)",null=True,blank=True)
    """Message transversal d'équipe, distinct des dossiers individuels."""
    id = models.BigAutoField(primary_key=True)
    contenu = models.TextField()
    contenu_document = models.JSONField(null=True, blank=True, editable=False)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-cree_le", "-pk"]


class NotePartagee(ModeleControle):
    fil_cle=models.CharField(max_length=160,blank=True,default='',db_index=True,editable=False)
    cle_envoi=models.UUIDField(null=True,blank=True,unique=True,editable=False)
    accord_hebergement=models.ForeignKey('AccordHebergement',on_delete=models.PROTECT,null=True,blank=True,related_name='notes')
    accord_repas=models.ForeignKey('AccordRepas',on_delete=models.PROTECT,null=True,blank=True,related_name='notes')
    accord_aide=models.ForeignKey('AccordAide',on_delete=models.PROTECT,null=True,blank=True,related_name='notes')
    menage=models.ForeignKey(Menage,on_delete=models.PROTECT,null=True,blank=True,related_name='notes')
    date_fait=models.DateField("Date de la contribution (si connue)",null=True,blank=True)
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
        constraints = [models.CheckConstraint(condition=(
            models.Q(menage__isnull=True,personne__isnull=False,accompagnement__isnull=True,sejour__isnull=True,accord_hebergement__isnull=True,accord_repas__isnull=True,accord_aide__isnull=True) |
            models.Q(menage__isnull=True,personne__isnull=True,accompagnement__isnull=False,sejour__isnull=True,accord_hebergement__isnull=True,accord_repas__isnull=True,accord_aide__isnull=True) |
            models.Q(menage__isnull=True,personne__isnull=True,accompagnement__isnull=True,sejour__isnull=False,accord_hebergement__isnull=True,accord_repas__isnull=True,accord_aide__isnull=True) |
            models.Q(menage__isnull=True,personne__isnull=True,accompagnement__isnull=True,sejour__isnull=True,accord_hebergement__isnull=False,accord_repas__isnull=True,accord_aide__isnull=True) |
            models.Q(menage__isnull=True,personne__isnull=True,accompagnement__isnull=True,sejour__isnull=True,accord_hebergement__isnull=True,accord_repas__isnull=False,accord_aide__isnull=True) |
            models.Q(menage__isnull=True,personne__isnull=True,accompagnement__isnull=True,sejour__isnull=True,accord_hebergement__isnull=True,accord_repas__isnull=True,accord_aide__isnull=False) |
            models.Q(menage__isnull=False,personne__isnull=True,accompagnement__isnull=True,sejour__isnull=True,accord_hebergement__isnull=True,accord_repas__isnull=True,accord_aide__isnull=True)), name="note_exactement_une_cible")]


class RevisionContribution(ModeleControle):
    ancienne_date=models.DateField(null=True,blank=True)
    nouvelle_date=models.DateField(null=True,blank=True)
    transmission = models.ForeignKey(Transmission, on_delete=models.PROTECT, null=True, blank=True, related_name="revisions")
    id = models.BigAutoField(primary_key=True)
    note = models.ForeignKey(NotePartagee, on_delete=models.PROTECT, null=True, blank=True, related_name="revisions")
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    date = models.DateTimeField(auto_now_add=True)
    ancien_texte = models.TextField()
    ancien_texte_document = models.JSONField(null=True, blank=True, editable=False)
    nouveau_texte = models.TextField()
    nouveau_texte_document = models.JSONField(null=True, blank=True, editable=False)
    motif = models.TextField(blank=True)

    class Meta:
        ordering = ["date", "pk"]
        constraints = [models.CheckConstraint(condition=(
            models.Q(transmission__isnull=False, note__isnull=True)
            | models.Q(transmission__isnull=True, note__isnull=False)), name="revision_une_cible")]


class ModeleRapport(ModeleControle):
    """Configuration privée de statistiques, jamais une copie des résultats."""
    id = models.BigAutoField(primary_key=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='modeles_rapports')
    nom = models.CharField(max_length=100)
    nature = models.CharField(max_length=20, choices=[('modele','Modèle'),('personnalisation','Personnalisation')], default='modele')
    description = models.TextField(blank=True)
    modele_source = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='personnalisations')
    source_catalogue = models.CharField(max_length=80, blank=True)
    empreinte_source = models.CharField(max_length=64, blank=True)
    parametres = models.JSONField(default=dict)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom', 'pk']


class ActionRelais(ModeleControle):
    annule_le=models.DateTimeField(null=True,blank=True,editable=False)
    annule_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,related_name='+',editable=False)
    motif_annulation=models.CharField(max_length=240,blank=True,editable=False)
    revision_sociale=models.PositiveIntegerField(default=0,editable=False)
    transmission=models.ForeignKey('Transmission',on_delete=models.PROTECT,null=True,blank=True,related_name='actions')
    note=models.ForeignKey('NotePartagee',on_delete=models.PROTECT,null=True,blank=True,related_name='actions')
    appel=models.ForeignKey('Appel115',on_delete=models.PROTECT,null=True,blank=True,related_name='actions')
    id = models.BigAutoField(primary_key=True)
    """Action explicite d'équipe, distincte d'une transmission informative."""
    libelle = models.CharField(max_length=240)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="actions_relais_creees")
    cree_le = models.DateTimeField(auto_now_add=True)
    echeance = models.DateField(null=True, blank=True)
    terminee_le = models.DateTimeField(null=True, blank=True)
    terminee_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="actions_relais_terminees")

    class Meta:
        permissions=[('annuler_actionrelais','Annuler une action de relève erronée')]
        ordering = ["echeance", "cree_le", "pk"]



class InformationsAccompagnement(TraceSaisie):
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
    activite = models.CharField('Activité de la prise en charge', max_length=16, blank=True, choices=[('chrs','CHRS'),('urgence','Urgence'),('autre','Autre activité')])
    animaux = models.CharField('Animaux — information pratique pour l’accueil', max_length=500, blank=True)
    motif = models.CharField('Motif de mise à jour', max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']
        constraints = [models.UniqueConstraint(fields=['accompagnement', 'version'], name='informations_suivi_version_unique')]


class EvolutionPriseEnCharge(ModeleControle):
    accompagnement = models.ForeignKey(Accompagnement, on_delete=models.PROTECT, related_name="evolutions_prevision")
    ancienne_fin = models.DateField(null=True)
    nouvelle_fin = models.DateField(null=True, blank=True)
    action = models.CharField(max_length=20, choices=[('prolongation', 'Prolongation'), ('correction', 'Correction de prévision')], default='prolongation')
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enregistre_le", "-pk"]


class SituationPersonnelle(PeriodeRetirable):
    """Fait social daté par personne, indépendant des prises en charge."""
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT, related_name="situations_personnelles")
    dimension = models.CharField(max_length=20, choices=SituationSociale.DIMENSIONS)
    valeur = models.CharField(max_length=30)
    source = models.CharField(max_length=160, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        base_manager_name = "tous"
        default_manager_name = "objects"
        ordering = ["debut", "pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("debut")), name="situation_personnelle_periode"),
            models.UniqueConstraint(fields=["personne", "dimension", "debut"], condition=models.Q(retire_le__isnull=True), name="situation_personnelle_date_unique"),
            models.UniqueConstraint(fields=["personne", "dimension"], condition=models.Q(fin__isnull=True, retire_le__isnull=True), name="situation_personnelle_ouverte_unique"),
        ]

    def clean(self):
        super().clean()
        if self.valeur not in dict(SituationSociale.VALEURS.get(self.dimension, [])):
            from django.core.exceptions import ValidationError
            raise ValidationError({"valeur": "Choisissez une valeur de cette dimension."})

    @property
    def libelle_valeur(self):
        return dict(SituationSociale.VALEURS.get(self.dimension, [])).get(self.valeur, self.valeur)


class RevisionSituationPersonnelle(TraceSaisie):
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT)
    situation = models.ForeignKey(SituationPersonnelle, on_delete=models.PROTECT, related_name="revisions")
    action = models.CharField(max_length=20, choices=[("changement", "Changement réel"), ("insertion", "Fait antérieur oublié"), ("correction", "Correction d’une erreur"), ("retrait", "Changement retiré")])
    avant = models.JSONField(default=list)
    apres = models.JSONField(default=list)
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enregistre_le", "-pk"]


class CommentaireDossier(ModeleControle):
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


class DeclarationFamiliale(PeriodeRetirable):
    """Déclarations individuelles, jamais déduites des appartenances au ménage."""
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT, related_name='declarations_familiales')
    situation_familiale = models.CharField('Situation familiale déclarée', max_length=160, blank=True)
    rapports_parentaux = models.CharField('Rapports avec les parents', max_length=160, blank=True)
    fratrie = models.CharField('Fratrie déclarée', max_length=160, blank=True)
    enfants_a_charge = models.PositiveSmallIntegerField('Nombre déclaré d’enfants à charge', null=True, blank=True)
    enfants_non_a_charge = models.PositiveSmallIntegerField('Nombre déclaré d’enfants non à charge', null=True, blank=True)
    grossesse = models.BooleanField('Grossesse déclarée', null=True, blank=True)
    source = models.CharField('Source de l’information', max_length=160, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        base_manager_name = "tous"
        default_manager_name = "objects"
        ordering = ['-debut', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F('debut')), name='famille_periode_valide'),
            models.UniqueConstraint(fields=['personne', 'debut'], condition=models.Q(retire_le__isnull=True), name='famille_date_unique'),
            models.UniqueConstraint(fields=['personne'], condition=models.Q(fin__isnull=True, retire_le__isnull=True), name='famille_ouverte_unique'),
        ]

    @property
    def resume(self):
        morceaux = [self.situation_familiale] if self.situation_familiale else []
        if self.enfants_a_charge is not None:
            morceaux.append(f'{self.enfants_a_charge} enfant(s) déclaré(s) à charge')
        if self.enfants_non_a_charge is not None:
            morceaux.append(f'{self.enfants_non_a_charge} non à charge')
        return ' · '.join(morceaux) or 'Autres informations familiales renseignées'


class RevisionDeclarationFamiliale(TraceSaisie):
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT)
    declaration = models.ForeignKey(DeclarationFamiliale, on_delete=models.PROTECT, related_name='revisions')
    action = models.CharField(max_length=20, choices=[('changement', 'Changement réel'), ('insertion', 'Fait antérieur oublié'), ('correction', 'Correction d’une erreur'), ('retrait', 'Changement retiré')])
    avant = models.JSONField(default=list)
    apres = models.JSONField(default=list)
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enregistre_le', '-pk']


class CoordonneesPersonnelles(PeriodeRetirable):
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT, related_name='coordonnees')
    usage_adresse = models.CharField('Nature de l’adresse déclarée',max_length=20,blank=True,choices=[('','Non qualifiée'),('contact','Adresse de contact déclarée'),('domicile_fixe','Domicile fixe déclaré'),('dernier_fixe','Dernier domicile fixe déclaré'),('autre','Autre adresse déclarée')])
    rue = models.CharField('Adresse déclarée — rue et complément', max_length=240, blank=True)
    code_postal = models.CharField('Code postal', max_length=20, blank=True)
    ville = models.CharField('Ville', max_length=160, blank=True)
    pays = models.CharField('Pays', max_length=160, blank=True)
    telephone = models.CharField('Téléphone', max_length=80, blank=True)
    courriel = models.EmailField('Courriel', blank=True)
    fax = models.CharField('Fax (si utile)', max_length=80, blank=True)
    source = models.CharField('Source de l’information', max_length=160, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        base_manager_name = "tous"
        default_manager_name = "objects"
        ordering = ['-debut', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F('debut')), name='coordonnees_periode_valide'),
            models.UniqueConstraint(fields=['personne', 'debut'], condition=models.Q(retire_le__isnull=True), name='coordonnees_date_unique'),
            models.UniqueConstraint(fields=['personne'], condition=models.Q(fin__isnull=True, retire_le__isnull=True), name='coordonnees_ouverte_unique'),
        ]

    @property
    def adresse(self):
        return ' · '.join(x for x in [self.rue, ' '.join(x for x in [self.code_postal, self.ville] if x), self.pays] if x)


class RevisionCoordonneesPersonnelles(TraceSaisie):
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


class RevisionContactMenage(ModeleControle):
    menage = models.ForeignKey(Menage, on_delete=models.PROTECT)
    designation = models.ForeignKey(ContactMenage, on_delete=models.PROTECT, related_name='revisions')
    action = models.CharField(max_length=20, choices=[c for c in RevisionDeclarationFamiliale._meta.get_field('action').choices if c[0] != 'retrait'])
    avant = models.JSONField(default=list)
    apres = models.JSONField(default=list)
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enregistre_le', '-pk']


class Partenaire(ModeleControle):
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


class RevisionFichePartenaire(ModeleControle):
    partenaire = models.ForeignKey(Partenaire, on_delete=models.PROTECT)
    fiche = models.ForeignKey(FichePartenaire, on_delete=models.PROTECT, related_name='revisions')
    action = models.CharField(max_length=20, choices=[c for c in RevisionDeclarationFamiliale._meta.get_field('action').choices if c[0] != 'retrait'])
    avant = models.JSONField(default=list)
    apres = models.JSONField(default=list)
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enregistre_le', '-pk']


class Intervenant(ModeleControle):
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


class RevisionFicheIntervenant(ModeleControle):
    intervenant = models.ForeignKey(Intervenant, on_delete=models.PROTECT)
    fiche = models.ForeignKey(FicheIntervenant, on_delete=models.PROTECT, related_name='revisions')
    action = models.CharField(max_length=20, choices=[c for c in RevisionDeclarationFamiliale._meta.get_field('action').choices if c[0] != 'retrait'])
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
    role = models.CharField('Rôle dans cette prise en charge', max_length=30, choices=ROLES)
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


class RevisionAffectationIntervenant(ModeleControle):
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


class PropositionSaisie(ModeleControle):
    CHAMPS = [('motif_principal','Demande principale 115'),('lieu_appel','Lieu / origine d’appel 115'),('demande_secondaire115','Demande secondaire 115'),('reponse115','Réponse 115'),('situation_familiale', 'Situation familiale'), ('rapports_parentaux', 'Rapports parentaux'),
        ('fratrie', 'Fratrie déclarée'), ('ville', 'Ville'), ('pays', 'Pays'),
        ('code_postal', 'Code postal'), ('fonction', 'Fonction professionnelle'),
        ('nature_ressource','Nature de ressource'),('type_creancier','Type de créancier'),('type_document','Type de pièce'),
        ('nature_couverture','Nature de couverture'),('regime','Régime déclaré'),('mesure','Mesure déclarée'),
        ('groupe_demande','Groupe demandeur déclaré'),('dernier_hebergement_duree','Durée déclarée du dernier hébergement'),('motif_demande','Motif de demande'),('motif_decision','Motif de décision'),('provenance','Provenance'),('dernier_hebergement_type','Type du dernier hébergement'),('type_destination','Type de destination'),('theme','Thème d’objectif'),('motif_orientation','Motif d’orientation'),
        ('qualification','Qualification déclarée'),('droit_sejour','Situation de séjour déclarée')]
    champ = models.CharField(max_length=40, choices=CHAMPS)
    valeur = models.CharField(max_length=160, validators=[RegexValidator(r'\S', 'Indiquez une proposition.')])
    active = models.BooleanField(default=True)
    revision = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ['champ', 'valeur', 'pk']
        constraints = [models.UniqueConstraint(fields=['champ', 'valeur'], name='proposition_saisie_unique')]


class RevisionPropositionSaisie(ModeleControle):
    proposition = models.ForeignKey(PropositionSaisie, on_delete=models.PROTECT, related_name='revisions')
    avant = models.JSONField(default=dict)
    apres = models.JSONField(default=dict)
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enregistre_le', '-pk']


class ComplementIdentite(PeriodeRetirable):
    personne = models.ForeignKey(Personne, on_delete=models.PROTECT, related_name='complements_identite')
    sexe_declare = models.CharField('Sexe déclaré', max_length=80, blank=True)
    naissance_lieu = models.CharField('Lieu de naissance (complément)', max_length=160, blank=True)
    naissance_ville = models.CharField('Ville de naissance', max_length=160, blank=True)
    naissance_pays = models.CharField('Pays de naissance', max_length=160, blank=True)
    nationalites = models.JSONField('Nationalités déclarées', default=list, blank=True)
    apatridie_declaree = models.BooleanField('Apatridie déclarée', null=True, blank=True)
    source = models.CharField('Source de l’information', max_length=160, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        valeurs=self.nationalites
        if not isinstance(valeurs,list) or len(valeurs)>50 or any(not isinstance(v,str) or not v.strip() or len(v)>160 for v in valeurs):
            raise ValidationError({'nationalites':'Indiquez des libellés distincts, non vides (160 caractères chacun, 50 au maximum).'})
        if len({v.strip().casefold() for v in valeurs})!=len(valeurs):
            raise ValidationError({'nationalites':'Ne répétez pas une nationalité dans la même déclaration.'})
        if self.apatridie_declaree is True and valeurs:
            raise ValidationError({'apatridie_declaree':'Une apatridie déclarée et une nationalité déclarée sont contradictoires.'})

    class Meta:
        base_manager_name = "tous"
        default_manager_name = "objects"
        ordering=['-debut','-pk']
        constraints=[
            models.CheckConstraint(condition=models.Q(fin__isnull=True)|models.Q(fin__gt=models.F('debut')),name='identite_complement_periode'),
            models.UniqueConstraint(fields=['personne','debut'],condition=models.Q(retire_le__isnull=True), name='identite_complement_date'),
            models.UniqueConstraint(fields=['personne'],condition=models.Q(fin__isnull=True, retire_le__isnull=True),name='identite_complement_ouvert')]


class RevisionComplementIdentite(TraceSaisie):
    personne=models.ForeignKey(Personne,on_delete=models.PROTECT)
    complement=models.ForeignKey(ComplementIdentite,on_delete=models.PROTECT,related_name='revisions')
    action=models.CharField(max_length=20,choices=RevisionDeclarationFamiliale._meta.get_field('action').choices)
    avant=models.JSONField(default=list)
    apres=models.JSONField(default=list)
    motif=models.CharField(max_length=240,blank=True)
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-enregistre_le','-pk']


class RelationPersonnelle(Periode):
    # Paire ordonnée pour les verrous et les doublons ; le sens reste explicite.
    NATURES=[('parent_a','A est parent déclaré de B'),('parent_b','B est parent déclaré de A'),
        ('couple','Lien de couple déclaré'),('fratrie','Fratrie déclarée'),('proche','Lien avec un proche'),
        ('contact_a','A désigne B comme personne à contacter'),('contact_b','B désigne A comme personne à contacter')]
    personne_a=models.ForeignKey(Personne,on_delete=models.PROTECT,related_name='relations_a')
    personne_b=models.ForeignKey(Personne,on_delete=models.PROTECT,related_name='relations_b')
    nature=models.CharField(max_length=20,choices=NATURES)
    precision=models.CharField('Précision du lien',max_length=240,blank=True)
    source=models.CharField('Source de l’information',max_length=160, blank=True)
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    annule_le=models.DateTimeField(null=True,blank=True,editable=False)
    annule_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,related_name='+',editable=False)
    motif_annulation=models.CharField(max_length=240,blank=True,editable=False)

    def autre(self,personne):
        return self.personne_b if personne.pk==self.personne_a_id else self.personne_a

    def role_depuis(self,personne):
        a=personne.pk==self.personne_a_id
        return {'parent_a':'parent' if a else 'enfant','parent_b':'enfant' if a else 'parent',
            'contact_a':'contact' if a else 'contact_de','contact_b':'contact_de' if a else 'contact'}.get(self.nature,self.nature)

    def libelle_depuis(self,personne):
        return {'parent':'Parent déclaré de','enfant':'Enfant déclaré de','couple':'Lien de couple avec',
            'fratrie':'Fratrie déclarée avec','proche':'Proche de','contact':'Personne à contacter :',
            'contact_de':'Personne à contacter pour'}.get(self.role_depuis(personne),'Lien avec')

    class Meta:
        ordering=['-debut','-pk']
        permissions=[('annuler_relationpersonnelle','Annuler une relation personnelle saisie par erreur')]
        constraints=[
            models.CheckConstraint(condition=models.Q(personne_a__lt=models.F('personne_b')),name='relation_paire_ordonnee'),
            models.CheckConstraint(condition=models.Q(fin__isnull=True)|models.Q(fin__gt=models.F('debut')),name='relation_periode'),
            models.CheckConstraint(condition=models.Q(annule_le__isnull=True,annule_par__isnull=True,motif_annulation='')|(
                models.Q(annule_le__isnull=False,annule_par__isnull=False)&~models.Q(motif_annulation='')),name='relation_annulation_coherente')]


class RevisionRelationPersonnelle(TraceSaisie):
    relation=models.ForeignKey(RelationPersonnelle,on_delete=models.PROTECT,related_name='revisions')
    action=models.CharField(max_length=20,choices=[('ajout','Lien déclaré'),('insertion','Fait antérieur oublié'),
        ('changement','Changement réel'),('correction','Correction'),('cloture','Fin du lien'),('annulation','Annulation de saisie')])
    avant=models.JSONField(default=list)
    apres=models.JSONField(default=list)
    motif=models.CharField(max_length=240,blank=True)
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-enregistre_le','-pk']


class SituationAdministrative(PeriodeRetirable):
    personne=models.ForeignKey(Personne,on_delete=models.PROTECT,related_name='situations_administratives')
    numero_ss=models.CharField('Identifiant de sécurité sociale déclaré',max_length=40,blank=True)
    numero_caf=models.CharField('Identifiant allocataire déclaré',max_length=80,blank=True)
    qualification=models.CharField('Qualification déclarée',max_length=160,blank=True)
    droit_sejour=models.CharField('Situation de séjour déclarée',max_length=160,blank=True)
    echeance_sejour=models.DateField('Échéance prévue du droit de séjour',null=True,blank=True)
    sans_emploi_duree_declaree=models.CharField('Durée déclarée sans emploi (si connue)',max_length=160,blank=True)
    sans_domicile_duree_declaree=models.CharField('Durée déclarée sans domicile (si connue)',max_length=160,blank=True)
    sans_emploi_depuis=models.DateField('Sans emploi depuis',null=True,blank=True)
    precision_sans_emploi=models.CharField('Précision de cette date',max_length=10,choices=[('','Non renseignée'),('exacte','Date déclarée exacte'),('estimee','Date déclarée estimée')],blank=True)
    sans_domicile_depuis=models.DateField('Sans domicile depuis',null=True,blank=True)
    precision_sans_domicile=models.CharField('Précision de cette date',max_length=10,choices=[('','Non renseignée'),('exacte','Date déclarée exacte'),('estimee','Date déclarée estimée')],blank=True)
    source=models.CharField('Source de l’information',max_length=160, blank=True)
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        for nom in ('sans_emploi','sans_domicile'):
            date=getattr(self,nom+'_depuis');precision=getattr(self,'precision_'+nom)
            if bool(date)!=bool(precision):raise ValidationError({'precision_'+nom:'Date et précision se renseignent ensemble ; ne pas inventer de date.'})
            if date and self.debut and date>self.debut:raise ValidationError({nom+'_depuis':'Cette date ne peut pas suivre la date de la déclaration.'})
        if self.echeance_sejour and not self.droit_sejour:raise ValidationError({'droit_sejour':'Précisez la situation à laquelle se rapporte l’échéance.'})

    class Meta:
        base_manager_name = "tous"
        default_manager_name = "objects"
        ordering=['-debut','-pk']
        constraints=[models.CheckConstraint(condition=models.Q(fin__isnull=True)|models.Q(fin__gt=models.F('debut')),name='administration_periode'),
            models.UniqueConstraint(fields=['personne','debut'],condition=models.Q(retire_le__isnull=True), name='administration_date'),
            models.UniqueConstraint(fields=['personne'],condition=models.Q(fin__isnull=True, retire_le__isnull=True),name='administration_ouverte')]


class JournalPersonnel(ModeleControle):
    action=models.CharField(max_length=20,choices=[('ajout','Déclaration'),('insertion','Fait antérieur oublié'),('changement','Changement réel'),('correction','Correction'),('cloture','Fin effective'),('annulation','Annulation de saisie')])
    avant=models.JSONField(default=list)
    apres=models.JSONField(default=list)
    motif=models.CharField(max_length=240,blank=True)
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    class Meta:
        abstract=True
        ordering=['-enregistre_le','-pk']


class RevisionSituationAdministrative(TraceSaisie, JournalPersonnel):
    action = models.CharField(max_length=20, choices=[*JournalPersonnel._meta.get_field('action').choices, ('retrait', 'Changement retiré')])
    personne=models.ForeignKey(Personne,on_delete=models.PROTECT)
    situation=models.ForeignKey(SituationAdministrative,on_delete=models.PROTECT,related_name='revisions')


class FaitPersonnelDate(Periode):
    personne=models.ForeignKey(Personne,on_delete=models.PROTECT)
    etat=models.CharField('État de la déclaration',max_length=10,choices=[('detail','Renseigné'),('aucun','Absence déclarée'),('inconnu','Non connu déclaré')],default='detail')
    source=models.CharField('Source de l’information',max_length=160, blank=True)
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    annule_le=models.DateTimeField(null=True,blank=True,editable=False)
    annule_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,editable=False,related_name='+')
    motif_annulation=models.CharField(max_length=240,blank=True,editable=False)

    class Meta:
        abstract=True
        ordering=['-debut','-pk']
        constraints=[models.CheckConstraint(condition=models.Q(fin__isnull=True)|models.Q(fin__gt=models.F('debut')),name='%(class)s_periode'),
            models.CheckConstraint(condition=models.Q(annule_le__isnull=True,annule_par__isnull=True,motif_annulation='')|(models.Q(annule_le__isnull=False,annule_par__isnull=False)&~models.Q(motif_annulation='')),name='%(class)s_annulation')]

    def verifier_details(self,champs):
        from django.core.exceptions import ValidationError
        if self.etat!='detail' and any(getattr(self,c) not in (None,'') for c in champs):
            raise ValidationError('Une absence ou une information non connue ne porte aucun détail contradictoire.')


class RessourcePersonnelle(FaitPersonnelDate):
    libelle=models.CharField('Nature du revenu',max_length=160,blank=True)
    organisme=models.ForeignKey(Partenaire,on_delete=models.PROTECT,null=True,blank=True)
    montant=models.DecimalField('Montant déclaré',max_digits=14,decimal_places=2,null=True,blank=True,validators=[MinValueValidator(0)])
    devise=models.CharField('Devise',max_length=3,default='EUR',validators=[RegexValidator(r'^[A-Z]{3}$','Utilisez trois lettres majuscules.')])
    periodicite=models.CharField('Périodicité',max_length=12,blank=True,choices=[('','Non renseignée'),('mensuelle','Mensuelle'),('hebdomadaire','Hebdomadaire'),('annuelle','Annuelle'),('ponctuelle','Ponctuelle')])
    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        if self.etat=='detail' and not self.libelle.strip():raise ValidationError({'libelle':'Indiquez la nature du revenu.'})
        self.verifier_details(('libelle','organisme_id','montant','periodicite'))
    class Meta(FaitPersonnelDate.Meta):
        abstract=False
        permissions=[('annuler_ressourcepersonnelle','Annuler une ressource saisie par erreur')]
        constraints=FaitPersonnelDate.Meta.constraints+[models.CheckConstraint(condition=models.Q(montant__isnull=True)|models.Q(montant__gte=0),name='ressource_montant_positif')]


class DettePersonnelle(FaitPersonnelDate):
    nature=models.CharField('Nature du montant',max_length=10,default='detail',choices=[('detail','Dette détaillée'),('total','Total de dette déclaré')])
    creancier=models.CharField('Créancier ou type de créancier',max_length=160,blank=True)
    organisme=models.ForeignKey(Partenaire,on_delete=models.PROTECT,null=True,blank=True)
    montant=models.DecimalField('Solde de dette déclaré',max_digits=14,decimal_places=2,null=True,blank=True,validators=[MinValueValidator(0)])
    devise=models.CharField('Devise',max_length=3,default='EUR',validators=[RegexValidator(r'^[A-Z]{3}$','Utilisez trois lettres majuscules.')])
    reference=models.CharField('Référence de dette (facultative)',max_length=160,blank=True)
    mensualite=models.DecimalField('Mensualité déclarée (même devise)',max_digits=14,decimal_places=2,null=True,blank=True,validators=[MinValueValidator(0)])
    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        if self.etat=='detail':
            if self.nature=='detail' and not (self.creancier.strip() or self.organisme_id):raise ValidationError({'creancier':'Précisez le créancier ou choisissez un organisme.'})
            if self.nature=='total' and (self.creancier or self.organisme_id or self.mensualite is not None or self.reference):raise ValidationError('Le total déclaré est distinct des créanciers et de leurs mensualités.')
        self.verifier_details(('creancier','organisme_id','montant','mensualite','reference'))
    class Meta(FaitPersonnelDate.Meta):
        abstract=False
        permissions=[('annuler_dettepersonnelle','Annuler une dette saisie par erreur')]
        constraints=FaitPersonnelDate.Meta.constraints+[models.CheckConstraint(condition=models.Q(montant__isnull=True)|models.Q(montant__gte=0),name='dette_montant_positif'),models.CheckConstraint(condition=models.Q(mensualite__isnull=True)|models.Q(mensualite__gte=0),name='dette_mensualite_positive')]


class PieceAdministrative(FaitPersonnelDate):
    type_document=models.CharField('Type de pièce présentée',max_length=160,blank=True)
    reference=models.CharField('Référence déclarée (facultative)',max_length=160,blank=True)
    date_presentation=models.DateField('Date de présentation connue',null=True,blank=True)
    echeance_prevue=models.DateField('Échéance prévue annoncée',null=True,blank=True)
    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        if self.etat=='detail' and not self.type_document.strip():raise ValidationError({'type_document':'Précisez le type de pièce.'})
        if self.date_presentation and self.debut and self.date_presentation>self.debut:raise ValidationError({'date_presentation':'La présentation ne peut pas suivre la déclaration.'})
        self.verifier_details(('type_document','reference','date_presentation','echeance_prevue'))
    class Meta(FaitPersonnelDate.Meta):
        abstract=False
        permissions=[('annuler_pieceadministrative','Annuler une pièce saisie par erreur')]


class CouvertureSociale(FaitPersonnelDate):
    libelle=models.CharField('Couverture déclarée',max_length=160,blank=True)
    regime=models.CharField('Régime déclaré',max_length=160,blank=True)
    organisme=models.ForeignKey(Partenaire,on_delete=models.PROTECT,null=True,blank=True)
    identifiant=models.CharField('Identifiant d’adhésion déclaré',max_length=80,blank=True)
    interlocuteur=models.ForeignKey(Intervenant,on_delete=models.PROTECT,null=True,blank=True)
    echeance_prevue=models.DateField('Échéance prévue annoncée',null=True,blank=True)
    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        if self.etat=='detail' and not self.libelle.strip():raise ValidationError({'libelle':'Précisez la couverture.'})
        self.verifier_details(('libelle','regime','organisme_id','identifiant','interlocuteur_id','echeance_prevue'))
    class Meta(FaitPersonnelDate.Meta):
        abstract=False
        permissions=[('annuler_couverturesociale','Annuler une couverture saisie par erreur')]


class ProtectionJuridique(FaitPersonnelDate):
    mesure=models.CharField('Mesure déclarée',max_length=160,blank=True)
    domaine=models.CharField('Portée déclarée',max_length=16,blank=True,choices=[('','Non renseignée'),('biens','Biens'),('personne','Personne'),('biens_personne','Biens et personne'),('autre','Autre portée')])
    precision_portee=models.TextField('Précisions sur la portée',max_length=1000,blank=True)
    reference_decision=models.CharField('Référence de décision connue',max_length=160,blank=True)
    date_decision=models.DateField('Date de décision connue',null=True,blank=True)
    echeance_prevue=models.DateField('Échéance prévue annoncée',null=True,blank=True)
    representant_intervenant=models.ForeignKey(Intervenant,on_delete=models.PROTECT,null=True,blank=True,related_name='mesures_representation',verbose_name='Professionnel représentant déclaré')
    representant_personne=models.ForeignKey(Personne,on_delete=models.PROTECT,null=True,blank=True,related_name='representations_declarees')
    organisme=models.ForeignKey(Partenaire,on_delete=models.PROTECT,null=True,blank=True)
    interlocuteur=models.ForeignKey(Intervenant,on_delete=models.PROTECT,null=True,blank=True)
    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        if self.etat=='detail' and not self.mesure.strip():raise ValidationError({'mesure':'Précisez la mesure déclarée.'})
        if sum(bool(v) for v in (self.representant_personne_id,self.representant_intervenant_id,self.organisme_id))>1:raise ValidationError('Choisissez un représentant personne, professionnel OU organisme ; le contact professionnel est distinct.')
        if self.representant_personne_id and self.representant_personne_id==self.personne_id:raise ValidationError({'representant_personne':'Choisissez une autre personne pour ce rôle déclaré.'})
        if self.date_decision and self.date_decision>timezone.localdate():raise ValidationError({'date_decision':'Une décision connue ne peut pas être future.'})
        self.verifier_details(('mesure','domaine','precision_portee','reference_decision','date_decision','echeance_prevue','representant_personne_id','representant_intervenant_id','organisme_id','interlocuteur_id'))
    class Meta(FaitPersonnelDate.Meta):
        abstract=False
        permissions=[('annuler_protectionjuridique','Annuler une mesure saisie par erreur')]
        constraints=FaitPersonnelDate.Meta.constraints+[models.CheckConstraint(condition=models.Q(representant_personne__isnull=True,representant_intervenant__isnull=True)|models.Q(representant_personne__isnull=True,organisme__isnull=True)|models.Q(representant_intervenant__isnull=True,organisme__isnull=True),name='protection_representant_unique')]


class RevisionRessourcePersonnelle(TraceSaisie, JournalPersonnel):
    fait=models.ForeignKey(RessourcePersonnelle,on_delete=models.PROTECT,related_name="revisions")


class RevisionDettePersonnelle(TraceSaisie, JournalPersonnel):
    fait=models.ForeignKey(DettePersonnelle,on_delete=models.PROTECT,related_name="revisions")


class RevisionPieceAdministrative(TraceSaisie, JournalPersonnel):
    fait=models.ForeignKey(PieceAdministrative,on_delete=models.PROTECT,related_name="revisions")


class RevisionCouvertureSociale(TraceSaisie, JournalPersonnel):
    fait=models.ForeignKey(CouvertureSociale,on_delete=models.PROTECT,related_name="revisions")


class RevisionProtectionJuridique(TraceSaisie, JournalPersonnel):
    fait=models.ForeignKey(ProtectionJuridique,on_delete=models.PROTECT,related_name="revisions")


class ElementParcours(ModeleControle):
    """Identité stable et bénéficiaires explicitement choisis, sans prestation implicite."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    personne = models.ForeignKey(Personne, null=True, blank=True, on_delete=models.PROTECT, related_name='%(class)s_elements')
    menage = models.ForeignKey(Menage, null=True, blank=True, on_delete=models.PROTECT, related_name='%(class)s_elements')
    beneficiaires = models.ManyToManyField(Personne, related_name='%(class)s_benefices')
    revision_sociale = models.PositiveIntegerField(default=0, editable=False)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    cree_le = models.DateTimeField(auto_now_add=True)
    annule_le = models.DateTimeField(null=True, editable=False)
    annule_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+', editable=False)
    motif_annulation = models.CharField(max_length=240, blank=True, editable=False)

    class Meta:
        abstract = True
        ordering = ['-cree_le', 'pk']
        constraints = [models.CheckConstraint(condition=(models.Q(personne__isnull=False, menage__isnull=True) | models.Q(personne__isnull=True, menage__isnull=False)), name='%(class)s_cible_unique'),
            models.CheckConstraint(condition=(models.Q(annule_le__isnull=True, annule_par__isnull=True, motif_annulation='') | (models.Q(annule_le__isnull=False, annule_par__isnull=False) & ~models.Q(motif_annulation=''))), name='%(class)s_annulation_coherente')]

    @property
    def cible(self):return self.personne or self.menage
    def __str__(self):return str(self.cible)


class DemandeAccueil(ElementParcours):
    class Meta(ElementParcours.Meta):
        permissions = [('annuler_demandeaccueil', 'Annuler une saisie erronée du parcours')]

    accompagnement = models.OneToOneField(Accompagnement, null=True, blank=True, on_delete=models.PROTECT, related_name='demande_accueil')


class OrientationParcours(ElementParcours):
    class Meta(ElementParcours.Meta):
        permissions = [('annuler_orientationparcours', 'Annuler une saisie erronée du parcours')]

    demande = models.ForeignKey(DemandeAccueil, null=True, blank=True, on_delete=models.PROTECT, related_name='orientations')
    accompagnement = models.ForeignKey(Accompagnement, null=True, blank=True, on_delete=models.PROTECT, related_name='orientations_parcours')


class ObjectifParcours(ElementParcours):
    class Meta(ElementParcours.Meta):
        permissions = [('annuler_objectifparcours', 'Annuler une saisie erronée du parcours')]

    accompagnement = models.ForeignKey(Accompagnement, null=True, blank=True, on_delete=models.PROTECT, related_name='objectifs_parcours')


class RepereDossier(ElementParcours):
    class Meta(ElementParcours.Meta):
        permissions = [('annuler_reperedossier', 'Annuler un état de suivi erroné')]
        constraints = [*ElementParcours.Meta.constraints,
            models.UniqueConstraint(fields=['personne'], condition=models.Q(personne__isnull=False, annule_le__isnull=True), name='repere_personne_unique'),
            models.UniqueConstraint(fields=['menage'], condition=models.Q(menage__isnull=False, annule_le__isnull=True), name='repere_menage_unique')]


class VersionParcours(Periode):
    source = models.CharField('Source de l’information', max_length=160, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    enregistre_le = models.DateTimeField(auto_now_add=True)
    class Meta:
        abstract = True
        ordering = ['-debut', '-pk']
        constraints = [models.CheckConstraint(condition=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F('debut')), name='%(class)s_periode_valide'),
            models.UniqueConstraint(fields=['element', 'debut'], name='%(class)s_date_unique'),
            models.UniqueConstraint(fields=['element'], condition=models.Q(fin__isnull=True), name='%(class)s_ouverte_unique')]


class VersionDemande(VersionParcours):
    element = models.ForeignKey(DemandeAccueil, on_delete=models.PROTECT, related_name='versions')
    etat = models.CharField('État de la demande', max_length=16, choices=[('attente','En attente'),('acceptee','Acceptée'),('refusee','Refusée'),('retiree','Retirée')])
    groupe_demande = models.CharField('Personne seule ou groupe demandeur déclaré', max_length=160, blank=True)
    motif_demande = models.CharField('Motif de la demande', max_length=160)
    motif_decision = models.CharField('Motif de la décision ou du retrait', max_length=160, blank=True)
    demandeur = models.CharField('Demande exprimée par', max_length=16, choices=[('personne','La personne'),('menage','Le ménage'),('professionnel','Un professionnel'),('organisme','Un organisme'),('autre','Autre / non précisé')])
    demandeur_professionnel = models.ForeignKey(Intervenant, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    demandeur_organisme = models.ForeignKey(Partenaire, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    precision_demandeur = models.CharField('Précision sur le demandeur', max_length=160, blank=True)
    prescripteur = models.ForeignKey(Intervenant, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    organisme_orienteur = models.ForeignKey(Partenaire, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    provenance = models.CharField('Provenance déclarée', max_length=160, blank=True)
    dernier_hebergement_type = models.CharField('Type du dernier hébergement déclaré', max_length=160, blank=True)
    dernier_hebergement_lieu = models.CharField('Lieu du dernier hébergement déclaré', max_length=160, blank=True)
    dernier_hebergement_duree = models.CharField('Durée déclarée dans le dernier hébergement', max_length=160, blank=True)
    accueil_prevu = models.DateField('Date d’accueil annoncée', null=True, blank=True)
    activite = models.CharField('Activité demandée', max_length=16, blank=True, choices=[('chrs','CHRS'),('urgence','Urgence'),('autre','Autre activité')])
    def clean(self):
        super().clean()
        if self.demandeur_professionnel_id and self.demandeur != 'professionnel' or self.demandeur_organisme_id and self.demandeur != 'organisme':
            raise ValidationError('Le demandeur identifié doit correspondre au type choisi.')
        if self.etat in ('refusee','retiree') and not self.motif_decision.strip():raise ValidationError({'motif_decision':'Expliquez le refus ou le retrait.'})


class VersionOrientation(VersionParcours):
    element = models.ForeignKey(OrientationParcours, on_delete=models.PROTECT, related_name='versions')
    etat = models.CharField('État de l’orientation', max_length=16, choices=[('proposee','Proposée'),('realisee','Réalisée'),('refusee','Refusée'),('abandonnee','Abandonnée')])
    destination = models.CharField('Destination', max_length=160)
    type_destination = models.CharField('Type de solution ou de service', max_length=160, blank=True)
    organisme = models.ForeignKey(Partenaire, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    interlocuteur = models.ForeignKey(Intervenant, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    motif_orientation = models.CharField('Motif de l’orientation', max_length=160)
    resultat = models.CharField('Résultat ou motif de refus/abandon', max_length=500, blank=True)
    date_prevue = models.DateField('Date annoncée', null=True, blank=True)
    def clean(self):
        super().clean()
        if self.etat != 'proposee' and not self.resultat.strip():raise ValidationError({'resultat':'Précisez le résultat effectif de cette orientation.'})


class VersionObjectif(VersionParcours):
    element = models.ForeignKey(ObjectifParcours, on_delete=models.PROTECT, related_name='versions')
    etat = models.CharField('Avancement', max_length=16, choices=[('encours','En cours'),('atteint','Atteint'),('suspendu','Suspendu'),('abandonne','Abandonné')])
    theme = models.CharField('Thème', max_length=160)
    titre = models.CharField('Objectif', max_length=160)
    horizon = models.CharField('Horizon', max_length=8, choices=[('court','Court terme'),('long','Plus long terme')])
    echeance = models.DateField('Échéance visée', null=True, blank=True)
    texte = models.TextField('Démarche et bilan de progression', max_length=4000, blank=True)
    texte_document = models.JSONField(null=True, blank=True, editable=False)


class VersionRepereDossier(VersionParcours):
    element = models.ForeignKey(RepereDossier, on_delete=models.PROTECT, related_name='versions')
    etat = models.CharField('État du suivi du dossier', max_length=16, choices=[('actif','Suivi actif'),('veille','En veille'),('termine','Suivi terminé')])
    raison = models.CharField('Raison du changement de suivi', max_length=240)


class RevisionDemande(TraceSaisie, JournalPersonnel):
    element = models.ForeignKey(DemandeAccueil, on_delete=models.PROTECT, related_name='revisions')
    action = models.CharField(max_length=16, choices=[*JournalPersonnel._meta.get_field('action').choices,('liaison','Liaison à une prise en charge'),('deliaison','Correction de liaison')])


class RevisionOrientation(TraceSaisie, JournalPersonnel):
    element = models.ForeignKey(OrientationParcours, on_delete=models.PROTECT, related_name='revisions')


class RevisionObjectif(TraceSaisie, JournalPersonnel):
    element = models.ForeignKey(ObjectifParcours, on_delete=models.PROTECT, related_name='revisions')


class RevisionRepereDossier(TraceSaisie, JournalPersonnel):
    element = models.ForeignKey(RepereDossier, on_delete=models.PROTECT, related_name='revisions')


class TypeAide(ModeleControle):
    NATURES=[('transport','Transport'),('bon_alimentaire','Bon alimentaire'),('produits','Produits alimentaires'),('accueil_jour','Accueil de jour')]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    revision_sociale=models.PositiveIntegerField(default=0,editable=False)
    nature=models.CharField('Nature',max_length=20,choices=NATURES)
    libelle=models.CharField('Titre ou aide',max_length=160)
    unite=models.CharField('Unité comptée',max_length=40)
    fractionnable=models.BooleanField('Unités fractionnables (par exemple kg)',default=False)
    precision=models.CharField('Sens de l’unité',max_length=500,blank=True)
    actif=models.BooleanField('Proposé pour les nouveaux accords',default=True)
    cree_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    cree_le=models.DateTimeField(auto_now_add=True)
    def __str__(self):return self.libelle+' — '+self.unite


class RevisionTypeAide(JournalPersonnel):
    type_aide=models.ForeignKey(TypeAide,on_delete=models.PROTECT,related_name='revisions')


class AccordAide(Periode):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    revision_sociale=models.PositiveIntegerField(default=0,editable=False)
    accompagnement=models.ForeignKey(Accompagnement,on_delete=models.PROTECT,related_name='accords_aides')
    beneficiaires=models.ManyToManyField(Personne,related_name='accords_aides')
    type_aide=models.ForeignKey(TypeAide,on_delete=models.PROTECT)
    nature=models.CharField(max_length=20,choices=TypeAide.NATURES,editable=False)
    libelle=models.CharField(max_length=160,editable=False)
    unite=models.CharField(max_length=40,editable=False)
    fractionnable=models.BooleanField(default=False,editable=False)
    precision=models.CharField(max_length=500,blank=True,editable=False)
    quantite=models.DecimalField('Quantité totale autorisée',max_digits=14,decimal_places=3,null=True,blank=True,validators=[MinValueValidator(Decimal('0.001'))])
    prestataire=models.ForeignKey(Partenaire,on_delete=models.PROTECT,null=True,blank=True,related_name='+')
    financeur=models.ForeignKey(Partenaire,on_delete=models.PROTECT,null=True,blank=True,related_name='+')
    valeur_bon=models.DecimalField('Valeur faciale d’un bon',max_digits=14,decimal_places=2,null=True,blank=True,validators=[MinValueValidator(0)])
    devise=models.CharField('Devise de la valeur faciale',max_length=3,default='EUR',validators=[RegexValidator(r'^[A-Z]{3}$','Trois lettres majuscules.')])
    source=models.CharField('Source de l’autorisation',max_length=160)
    cree_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    cree_le=models.DateTimeField(auto_now_add=True)
    annule_le=models.DateTimeField(null=True,editable=False)
    annule_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,related_name='+',editable=False)
    motif_annulation=models.CharField(max_length=240,blank=True,editable=False)
    class Meta:
        ordering=['-debut','pk']
        permissions=[('annuler_accordaide','Annuler un accord d’aide erroné')]
        constraints=[models.CheckConstraint(condition=models.Q(fin__isnull=True)|models.Q(fin__gt=models.F('debut')),name='aide_periode_valide'),
            models.CheckConstraint(condition=models.Q(quantite__isnull=True)|models.Q(quantite__gt=0),name='aide_quantite_positive'),
            models.CheckConstraint(condition=models.Q(valeur_bon__isnull=True)|models.Q(valeur_bon__gte=0),name='aide_valeur_positive'),
            models.CheckConstraint(condition=models.Q(annule_le__isnull=True,annule_par__isnull=True,motif_annulation='')|(models.Q(annule_le__isnull=False,annule_par__isnull=False)&~models.Q(motif_annulation='')),name='aide_annulation_coherente')]
    def clean(self):
        super().clean()
        if self.valeur_bon is not None and self.nature!='bon_alimentaire':raise ValidationError({'valeur_bon':'La valeur faciale concerne seulement les bons alimentaires, pas un tarif.'})
    def __str__(self):return self.libelle+' — '+str(self.debut)


class RemiseAide(ModeleControle):
    accord=models.ForeignKey(AccordAide,on_delete=models.PROTECT,related_name='remises')
    beneficiaires=models.ManyToManyField(Personne,related_name='remises_aides')
    date=models.DateField('Date de remise ou de réalisation')
    quantite=models.DecimalField('Quantité réellement remise',max_digits=14,decimal_places=3,validators=[MinValueValidator(Decimal('0.001'))])
    source=models.CharField('Source de la réalisation',max_length=160)
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    enregistre_le=models.DateTimeField(auto_now_add=True)
    annule_le=models.DateTimeField(null=True,editable=False)
    annule_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,related_name='+',editable=False)
    motif_annulation=models.CharField(max_length=240,blank=True,editable=False)
    class Meta:
        ordering=['-date','-pk']
        permissions=[('annuler_remiseaide','Annuler une remise erronée')]
        constraints=[models.CheckConstraint(condition=models.Q(quantite__gt=0),name='remise_aide_positive'),
            models.CheckConstraint(condition=models.Q(annule_le__isnull=True,annule_par__isnull=True,motif_annulation='')|(models.Q(annule_le__isnull=False,annule_par__isnull=False)&~models.Q(motif_annulation='')),name='remise_annulation_coherente')]


class UsageAide(ModeleControle):
    remise=models.ForeignKey(RemiseAide,on_delete=models.PROTECT,related_name='usages')
    version=models.PositiveIntegerField()
    date=models.DateField('Date du constat d’utilisation')
    quantite=models.DecimalField('Unités utilisées déclarées',max_digits=14,decimal_places=3,null=True,blank=True,validators=[MinValueValidator(0)])
    source=models.CharField(max_length=160)
    motif=models.CharField(max_length=240,blank=True)
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-version']
        constraints=[models.UniqueConstraint(fields=['remise','version'],name='usage_version_unique'),models.CheckConstraint(condition=models.Q(quantite__isnull=True)|models.Q(quantite__gte=0),name='usage_quantite_positive')]


class RevisionAide(JournalPersonnel):
    accord=models.ForeignKey(AccordAide,on_delete=models.PROTECT,related_name='revisions')
    remise=models.ForeignKey(RemiseAide,on_delete=models.PROTECT,null=True,related_name='revisions')


class RevisionRepas(JournalPersonnel):
    repas=models.ForeignKey(RepasDistribue,on_delete=models.PROTECT,related_name='revisions')


class ContinuiteSejour(ModeleControle):
    origine=models.OneToOneField(Sejour,on_delete=models.PROTECT,related_name='individualisation')
    date=models.DateField()
    motif=models.CharField(max_length=240)
    avant=models.JSONField()
    apres=models.JSONField()
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)


class RevisionLieu(JournalPersonnel):
    lieu=models.ForeignKey(LieuHebergement,on_delete=models.PROTECT,related_name='revisions')


class RevisionServiceRepas(JournalPersonnel):
    accord=models.ForeignKey(AccordRepas,on_delete=models.PROTECT,related_name='revisions_service')


class RevisionContinuite(JournalPersonnel):
    continuite=models.ForeignKey(ContinuiteSejour,on_delete=models.PROTECT,related_name='revisions')


# Financements D : versions de calcul immuables, séparées des faits de prestation.
class TarifPrestation(ModeleControle):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    libelle=models.CharField('Nom du tarif',max_length=160)
    revision_sociale=models.PositiveIntegerField(default=0,editable=False)
    cree_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    class Meta:
        ordering=['libelle','pk']
    def __str__(self):return self.libelle


class VersionTarif(Periode):
    tarif=models.ForeignKey(TarifPrestation,on_delete=models.PROTECT,related_name='versions')
    version=models.PositiveIntegerField()
    libelle=models.CharField(max_length=160)
    unite=models.CharField('Unité facturée',max_length=60)
    categorie=models.CharField('Catégorie déclarée (facultative)',max_length=80,blank=True)
    montant=models.DecimalField('Prix unitaire',max_digits=14,decimal_places=4,validators=[MinValueValidator(0)])
    devise=models.CharField(max_length=3,default='EUR',validators=[RegexValidator(r'^[A-Z]{3}$','Trois lettres majuscules.')])
    prestataire=models.ForeignKey(Partenaire,on_delete=models.PROTECT,null=True,blank=True)
    actif=models.BooleanField('Proposer ce tarif',default=True)
    source=models.CharField(max_length=160)
    motif=models.CharField(max_length=240,blank=True)
    action=models.CharField(max_length=16,choices=[('definition','Définition'),('changement','Nouveau prix'),('correction','Correction d’erreur')])
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions=('view','add')
        ordering=['-version']
        constraints=[models.CheckConstraint(condition=models.Q(fin__isnull=True)|models.Q(fin__gt=models.F('debut')),name='tarif_periode_valide'),models.UniqueConstraint(fields=['tarif','version'],name='tarif_version_unique'),models.CheckConstraint(condition=models.Q(montant__gte=0),name='tarif_prix_positif')]
    def __str__(self):return f'{self.libelle} · v{self.version} du {self.debut} · {self.montant} {self.devise}/{self.unite}'


class FinancementPrestation(ModeleControle):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    revision_sociale=models.PositiveIntegerField(default=0,editable=False)
    accompagnement=models.ForeignKey(Accompagnement,on_delete=models.PROTECT,related_name='financements')
    hebergement=models.OneToOneField(AccordHebergement,on_delete=models.PROTECT,null=True,blank=True,related_name='financement')
    repas=models.OneToOneField(AccordRepas,on_delete=models.PROTECT,null=True,blank=True,related_name='financement')
    aide=models.OneToOneField(AccordAide,on_delete=models.PROTECT,null=True,blank=True,related_name='financement')
    cree_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    class Meta:
        default_permissions=('view','add')
        constraints=[models.CheckConstraint(condition=models.Q(hebergement__isnull=False,repas__isnull=True,aide__isnull=True)|models.Q(hebergement__isnull=True,repas__isnull=False,aide__isnull=True)|models.Q(hebergement__isnull=True,repas__isnull=True,aide__isnull=False),name='financement_cible_unique')]
    @property
    def accord(self):return self.hebergement or self.repas or self.aide
    @property
    def nature(self):return 'hebergement' if self.hebergement_id else 'repas' if self.repas_id else 'aide'


class VersionFinancement(Periode):
    emetteur=models.ForeignKey(Partenaire,on_delete=models.PROTECT,null=True,blank=True,related_name='+',verbose_name='Établissement / organisme émetteur')
    mentions=models.TextField('Mentions particulières du document',max_length=2000,blank=True)
    financement=models.ForeignKey(FinancementPrestation,on_delete=models.PROTECT,related_name='versions')
    version=models.PositiveIntegerField()
    devise=models.CharField(max_length=3,default='EUR',validators=[RegexValidator(r'^[A-Z]{3}$','Trois lettres majuscules.')])
    prestataire=models.ForeignKey(Partenaire,on_delete=models.PROTECT,null=True,blank=True,related_name='+')
    prescripteur=models.ForeignKey(Partenaire,on_delete=models.PROTECT,null=True,blank=True,related_name='+')
    facturation=models.ForeignKey(Partenaire,on_delete=models.PROTECT,null=True,blank=True,related_name='+',verbose_name='Destinataire de facturation')
    signataire=models.ForeignKey(Intervenant,on_delete=models.PROTECT,null=True,blank=True)
    reference=models.CharField('Référence de décision / convention',max_length=100,blank=True)
    source=models.CharField(max_length=160)
    motif=models.CharField(max_length=240,blank=True)
    action=models.CharField(max_length=16,choices=[('definition','Définition'),('changement','Nouvelle décision'),('correction','Correction d’erreur')])
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions=('view','add')
        ordering=['-version']
        constraints=[models.CheckConstraint(condition=models.Q(fin__isnull=True)|models.Q(fin__gt=models.F('debut')),name='calcul_periode_valide'),models.UniqueConstraint(fields=['financement','version'],name='financement_version_unique')]


class LigneCout(ModeleControle):
    PHASES=[('prevu','Prévu'),('autorise','Autorisé'),('realise','Réalisé documenté')]
    version=models.ForeignKey(VersionFinancement,on_delete=models.PROTECT,related_name='lignes')
    phase=models.CharField(max_length=10,choices=PHASES)
    date=models.DateField('Date du prix applicable')
    libelle=models.CharField('Composante de coût',max_length=160)
    unite=models.CharField('Unité facturée',max_length=60)
    categorie=models.CharField('Catégorie déclarée',max_length=80,blank=True)
    quantite=models.DecimalField(max_digits=14,decimal_places=3,validators=[MinValueValidator(0)])
    prix=models.DecimalField('Prix unitaire',max_digits=14,decimal_places=4,validators=[MinValueValidator(0)])
    montant=models.DecimalField(max_digits=20,decimal_places=2,editable=False)
    tarif=models.ForeignKey(VersionTarif,on_delete=models.PROTECT,null=True,blank=True)
    justification=models.CharField('Origine de la quantité / pièce justificative',max_length=240)
    class Meta:
        default_permissions=('view',)
        ordering=['phase','pk']
        constraints=[models.CheckConstraint(condition=models.Q(quantite__gte=0,prix__gte=0,montant__gte=0),name='couts_non_negatifs')]


class ImputationFinancement(ModeleControle):
    version=models.ForeignKey(VersionFinancement,on_delete=models.PROTECT,related_name='imputations')
    phase=models.CharField(max_length=10,choices=LigneCout.PHASES)
    financeur=models.ForeignKey(Partenaire,on_delete=models.PROTECT)
    budget=models.CharField('Budget / dispositif / imputation',max_length=160)
    montant=models.DecimalField('Montant affecté',max_digits=20,decimal_places=2,validators=[MinValueValidator(0)])
    reference=models.CharField('Référence de décision',max_length=100,blank=True)
    class Meta:
        default_permissions=('view',)
        constraints=[models.CheckConstraint(condition=models.Q(montant__gte=0),name='imputation_non_negative')]


class DocumentFinancement(ModeleControle):
    MODELES=[('engagement','Bon d’engagement'),('prescription','Bon de prescription'),('releve','Relevé de coûts')]
    version=models.ForeignKey(VersionFinancement,on_delete=models.PROTECT,related_name='documents')
    modele=models.CharField(max_length=16,choices=MODELES)
    date=models.DateField('Date d’émission')
    phase=models.CharField(max_length=10,choices=LigneCout.PHASES)
    remplace=models.OneToOneField('self',on_delete=models.PROTECT,null=True,blank=True,related_name='remplacement')
    contenu=models.JSONField()
    empreinte=models.CharField(max_length=64)
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions=('view','add')
        ordering=['-pk']
    @property
    def numero(self):return f'PAP-{self.pk:08d}'


class AnnulationDocument(ModeleControle):
    document=models.OneToOneField(DocumentFinancement,on_delete=models.PROTECT,related_name='annulation')
    motif=models.CharField(max_length=240)
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions=('view','add')


class Appel115(ModeleControle):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    revision_sociale=models.PositiveIntegerField(default=0,editable=False)
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    annule_le=models.DateTimeField(null=True,blank=True,editable=False)
    annule_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,related_name='+',editable=False)
    motif_annulation=models.CharField(max_length=240,blank=True,editable=False)
    class Meta:
        default_permissions=('view','add')
        permissions=[('annuler_appel115','Annuler un appel saisi par erreur')]
        ordering=['-enregistre_le','pk']
        constraints=[models.CheckConstraint(condition=models.Q(annule_le__isnull=True,annule_par__isnull=True,motif_annulation='')|(models.Q(annule_le__isnull=False,annule_par__isnull=False)&~models.Q(motif_annulation='')),name='appel_annulation_coherente')]


class VersionAppel115(ModeleControle):
    TYPES=[('personne','Personne concernée'),('tiers','Tiers / proche'),('professionnel','Professionnel'),('organisme','Organisme / service'),('inconnu','Appelant non identifié')]
    appel=models.ForeignKey(Appel115,on_delete=models.PROTECT,related_name='versions')
    version=models.PositiveIntegerField()
    date=models.DateField('Date de l’appel')
    heure=models.TimeField('Heure de l’appel (si connue)',null=True,blank=True)
    type_appelant=models.CharField(max_length=16,choices=TYPES)
    appelant_personne=models.ForeignKey(Personne,on_delete=models.PROTECT,null=True,blank=True,related_name='+')
    appelant_intervenant=models.ForeignKey(Intervenant,on_delete=models.PROTECT,null=True,blank=True,related_name='+')
    appelant_organisme=models.ForeignKey(Partenaire,on_delete=models.PROTECT,null=True,blank=True,related_name='+')
    appelant_libre=models.CharField('Nom déclaré de l’appelant (hors répertoire)',max_length=160,blank=True)
    telephone=models.CharField('Téléphone de rappel déclaré',max_length=80,blank=True)
    lieu_appel=models.CharField('Lieu / origine de l’appel',max_length=160,blank=True)
    menage=models.ForeignKey(Menage,on_delete=models.PROTECT,null=True,blank=True)
    beneficiaires=models.ManyToManyField(Personne,related_name='appels115')
    adultes_declares=models.PositiveSmallIntegerField('Adultes déclarés lors de l’appel',null=True,blank=True)
    enfants_declares=models.PositiveSmallIntegerField('Enfants déclarés lors de l’appel',null=True,blank=True)
    grossesses_declarees=models.PositiveSmallIntegerField('Grossesses déclarées lors de l’appel',null=True,blank=True)
    motif_principal=models.CharField('Demande principale',max_length=160)
    details=models.TextField('Détails de la demande',blank=True,max_length=4000)
    details_document=models.JSONField(null=True,blank=True,editable=False)
    demandes_secondaires=models.JSONField('Autres demandes',default=list,blank=True)
    reponses=models.JSONField('Réponses apportées',default=list,blank=True)
    etat_reponse=models.CharField('État de la réponse',max_length=16,choices=[('inconnue','Non renseignée'),('sans_reponse','Aucune réponse apportée déclarée'),('apportee','Réponse apportée')],default='inconnue')
    orientation=models.ForeignKey(Partenaire,on_delete=models.PROTECT,null=True,blank=True,related_name='+',verbose_name='Organisme vers lequel orienter')
    orientation_declaree=models.CharField('Orientation déclarée hors répertoire',max_length=160,blank=True)
    information_complementaire=models.CharField('Information complémentaire propre à l’appel',max_length=500,blank=True)
    source=models.CharField(max_length=160)
    action=models.CharField(max_length=16,choices=[('saisie','Saisie de l’appel'),('suite','Suite / identification ultérieure'),('correction','Correction d’erreur')])
    motif=models.CharField(max_length=240,blank=True)
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions=('view','add')
        ordering=['-version']
        constraints=[models.UniqueConstraint(fields=['appel','version'],name='appel_version_unique')]
    def clean(self):
        super().clean()
        from django.utils import timezone
        if self.date and self.date>timezone.localdate():raise ValidationError({'date':'Un appel effectué ne peut pas être futur.'})
        for c in ('demandes_secondaires','reponses'):
            v=getattr(self,c)
            if not isinstance(v,list) or len(v)>30 or any(not isinstance(s,str) or not s.strip() or len(s)>160 for s in v) or len({s.strip().casefold() for s in v})!=len(v):raise ValidationError({c:'Au plus 30 éléments distincts, de 160 caractères chacun.'})
        appelants=[self.appelant_personne_id,self.appelant_intervenant_id,self.appelant_organisme_id,bool(self.appelant_libre.strip())]
        if sum(bool(x) for x in appelants)>1:raise ValidationError('Choisissez une seule identité d’appelant, du répertoire ou déclarée librement.')
        if self.type_appelant=='inconnu' and any(appelants):raise ValidationError({'type_appelant':'Un appelant identifié ne peut pas être déclaré inconnu.'})
        if self.appelant_personne_id and self.type_appelant not in ('personne','tiers') or self.appelant_intervenant_id and self.type_appelant!='professionnel' or self.appelant_organisme_id and self.type_appelant!='organisme':raise ValidationError({'type_appelant':'Le type et l’identité de l’appelant doivent correspondre.'})
        if bool(self.reponses)!=(self.etat_reponse=='apportee'):raise ValidationError({'reponses':'Indiquez les réponses lorsque l’état est « Réponse apportée » ; sinon laissez la liste vide.'})
        if self.orientation_id and self.orientation_declaree.strip():raise ValidationError({'orientation_declaree':'Choisissez le répertoire ou une orientation déclarée, pas les deux.'})


class LienAppelParcours(ModeleControle):
    appel=models.ForeignKey(Appel115,on_delete=models.PROTECT,related_name='liens')
    demande=models.ForeignKey(DemandeAccueil,on_delete=models.PROTECT,null=True,blank=True)
    accompagnement=models.ForeignKey(Accompagnement,on_delete=models.PROTECT,null=True,blank=True)
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    motif=models.CharField(max_length=240)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    annule_le=models.DateTimeField(null=True,editable=False)
    annule_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,related_name='+',editable=False)
    motif_annulation=models.CharField(max_length=240,blank=True,editable=False)
    class Meta:
        default_permissions=('view','add')
        permissions=[('annuler_lienappelparcours','Annuler un lien erroné d’appel au parcours')]
        constraints=[models.CheckConstraint(condition=models.Q(demande__isnull=True,accompagnement__isnull=False)|models.Q(demande__isnull=False,accompagnement__isnull=True),name='appel_lien_cible_unique'),models.UniqueConstraint(fields=['appel','demande'],condition=models.Q(annule_le__isnull=True),name='appel_demande_active_unique'),models.UniqueConstraint(fields=['appel','accompagnement'],condition=models.Q(annule_le__isnull=True),name='appel_prise_active_unique')]


class RevisionAppel115(JournalPersonnel):
    appel=models.ForeignKey(Appel115,on_delete=models.PROTECT,related_name='revisions')


class AnnulationContribution(ModeleControle):
    transmission=models.OneToOneField(Transmission,on_delete=models.PROTECT,null=True,blank=True,related_name='annulation')
    note=models.OneToOneField(NotePartagee,on_delete=models.PROTECT,null=True,blank=True,related_name='annulation')
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    motif=models.CharField(max_length=240)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions=('view','add')
        constraints=[models.CheckConstraint(condition=models.Q(transmission__isnull=True,note__isnull=False)|models.Q(transmission__isnull=False,note__isnull=True),name='annulation_contribution_cible')]


class RevisionActionRelais(JournalPersonnel):
    action_relais=models.ForeignKey(ActionRelais,on_delete=models.PROTECT,related_name='revisions')


class PieceDossier(ModeleControle):
    """Document externe privé : cible immuable, fichiers versionnés et annulation."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    personne = models.ForeignKey(Personne,on_delete=models.PROTECT,null=True,blank=True,related_name='pieces_dossier')
    menage = models.ForeignKey(Menage,on_delete=models.PROTECT,null=True,blank=True,related_name='pieces_dossier')
    accompagnement = models.ForeignKey(Accompagnement,on_delete=models.PROTECT,null=True,blank=True,related_name='pieces_dossier')
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    enregistre_le = models.DateTimeField(auto_now_add=True)
    annule_le = models.DateTimeField(null=True,blank=True)
    annule_par = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,related_name='+')
    motif_annulation = models.CharField(max_length=240,blank=True)

    class Meta:
        permissions=[('annuler_piecedossier','Annuler une pièce jointe sans supprimer ses versions')]
        constraints=[models.CheckConstraint(condition=(models.Q(personne__isnull=False,menage__isnull=True,accompagnement__isnull=True)|models.Q(personne__isnull=True,menage__isnull=False,accompagnement__isnull=True)|models.Q(personne__isnull=True,menage__isnull=True,accompagnement__isnull=False)),name='piece_dossier_cible_unique'),models.CheckConstraint(condition=(models.Q(annule_le__isnull=True,annule_par__isnull=True,motif_annulation='')|(models.Q(annule_le__isnull=False,annule_par__isnull=False)&~models.Q(motif_annulation=''))),name='piece_dossier_annulation_coherente')]

    @property
    def cible(self):
        return self.personne or self.menage or self.accompagnement


class VersionPieceDossier(ModeleControle):
    piece = models.ForeignKey(PieceDossier,on_delete=models.PROTECT,related_name='versions')
    version = models.PositiveIntegerField()
    titre = models.CharField(max_length=160)
    date_document = models.DateField(null=True,blank=True)
    nom_fichier = models.CharField(max_length=180)
    contenu = models.BinaryField(editable=False)
    taille = models.PositiveIntegerField()
    empreinte = models.CharField(max_length=64)
    source = models.CharField(max_length=160)
    motif = models.CharField(max_length=240,blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=['-version']
        constraints=[models.UniqueConstraint(fields=['piece','version'],name='piece_dossier_version_unique'),models.CheckConstraint(condition=models.Q(taille__gt=0,taille__lte=5242880,version__gt=0),name='piece_dossier_fichier_borne')]


class BesoinAccueil(FaitPersonnelDate):
    categorie=models.CharField('Nature du besoin déclaré',max_length=20,choices=[('','Non renseignée'),('sante','Besoin lié à la santé'),('mobilite','Mobilité / accessibilité'),('alimentation','Alimentation adaptée'),('communication','Communication'),('animal','Accueil avec un animal'),('autre','Autre besoin pratique')],blank=True)
    libelle=models.CharField('Besoin ou situation déclaré',max_length=160,blank=True)
    adaptation=models.CharField('Adaptation pratique demandée (si connue)',max_length=500,blank=True)

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        if self.etat=='detail' and (not self.categorie or not self.libelle.strip()):raise ValidationError({'libelle':'Précisez la nature et le besoin déclaré ; aucune conclusion médicale n’est déduite.'})
        self.verifier_details(('categorie','libelle','adaptation'))

    class Meta(FaitPersonnelDate.Meta):
        abstract=False
        permissions=[('annuler_besoinaccueil','Annuler un besoin d’accueil saisi par erreur')]


class RevisionBesoinAccueil(TraceSaisie, JournalPersonnel):
    fait=models.ForeignKey(BesoinAccueil,on_delete=models.PROTECT,related_name='revisions')


class AntecedentInstitutionnel(FaitPersonnelDate):
    libelle=models.CharField('Institution ou type de passage déclaré',max_length=160,blank=True)
    frequentation=models.CharField('Fréquentation de cette institution déclarée',max_length=10,blank=True,choices=[('','Non qualifiée'),('oui','Déjà fréquentée'),('non','Jamais fréquentée, selon la déclaration'),('inconnu','Non connue pour cette institution')])
    organisme=models.ForeignKey(Partenaire,on_delete=models.PROTECT,null=True,blank=True)
    periode_declaree=models.CharField('Période déclarée (si non datée précisément)',max_length=160,blank=True)
    date_entree=models.DateField('Entrée connue dans cette institution',null=True,blank=True)
    date_sortie=models.DateField('Sortie connue de cette institution',null=True,blank=True)
    precision_dates=models.CharField('Précision des dates connues',max_length=10,blank=True,choices=[('','Dates non connues'),('exactes','Dates déclarées exactes'),('estimees','Dates déclarées estimées')])

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        if self.etat=='detail' and not self.libelle.strip():raise ValidationError({'libelle':'Nommez le passage déclaré, sans déduire une institution depuis une situation actuelle.'})
        self.verifier_details(('libelle','frequentation','organisme_id','periode_declaree','date_entree','date_sortie','precision_dates'))
        if self.frequentation in ('non','inconnu') and any((self.periode_declaree,self.date_entree,self.date_sortie,self.precision_dates)):raise ValidationError('Une institution déclarée jamais fréquentée, ou de fréquentation non connue, ne porte ni date ni durée de passage.')
        if bool(self.date_entree or self.date_sortie)!=bool(self.precision_dates):raise ValidationError({'precision_dates':'Une date connue doit être qualifiée ; une période approximative seule ne crée aucune date.'})
        if self.date_entree and self.date_sortie and self.date_sortie<self.date_entree:raise ValidationError({'date_sortie':'La sortie ne peut pas précéder l’entrée.'})
        if self.debut and any(d and d>self.debut for d in (self.date_entree,self.date_sortie)):raise ValidationError({'date_entree':'Un antécédent ne peut pas être postérieur à sa déclaration.'})

    class Meta(FaitPersonnelDate.Meta):
        abstract=False
        permissions=[('annuler_antecedentinstitutionnel','Annuler un antécédent déclaré par erreur')]


class RevisionAntecedentInstitutionnel(TraceSaisie, JournalPersonnel):
    fait=models.ForeignKey(AntecedentInstitutionnel,on_delete=models.PROTECT,related_name='revisions')


class AncrageTerritorial(FaitPersonnelDate):
    type_territoire=models.CharField('Type de territoire déclaré',max_length=15,blank=True,choices=[('agglomeration','Agglomération'),('commune','Commune'),('departement','Département'),('autre','Autre territoire')])
    territoire=models.CharField('Territoire déclaré',max_length=160,blank=True)
    anciennete_declaree=models.CharField('Ancienneté déclarée',max_length=160,blank=True)
    depuis=models.DateField('Présence déclarée depuis',null=True,blank=True)
    precision_depuis=models.CharField('Précision de cette date',max_length=10,blank=True,choices=[('','Date non connue'),('exacte','Date déclarée exacte'),('estimee','Date déclarée estimée')])

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        if self.etat=='detail' and (not self.territoire.strip() or not self.type_territoire):raise ValidationError('Précisez le territoire et son type ; aucune ville n’est déduite de l’adresse ou du lieu d’accueil.')
        self.verifier_details(('type_territoire','territoire','anciennete_declaree','depuis','precision_depuis'))
        if bool(self.depuis)!=bool(self.precision_depuis):raise ValidationError({'precision_depuis':'Qualifiez la date si elle est connue ; une durée déclarée seule ne crée aucune date.'})
        if self.depuis and self.debut and self.depuis>self.debut:raise ValidationError({'depuis':'La présence déclarée ne peut pas commencer après la date de cette déclaration.'})

    class Meta(FaitPersonnelDate.Meta):
        abstract=False
        permissions=[('annuler_ancrageterritorial','Annuler un ancrage territorial déclaré par erreur')]
        constraints=FaitPersonnelDate.Meta.constraints+[models.CheckConstraint(condition=models.Q(depuis__isnull=True)|models.Q(depuis__lte=models.F('debut')),name='ancrage_depuis_declaration')]


class RevisionAncrageTerritorial(TraceSaisie, JournalPersonnel):
    fait=models.ForeignKey(AncrageTerritorial,on_delete=models.PROTECT,related_name='revisions')


class EvolutionPersonnelleDeclaree(FaitPersonnelDate):
    domaine=models.CharField('Domaine de l’évolution déclarée',max_length=20,blank=True,choices=[('logement','Logement'),('emploi','Emploi / formation'),('ressources','Ressources'),('liens','Liens et vie sociale'),('demarches','Démarches'),('autre','Autre domaine déclaré')])
    libelle=models.CharField('Évolution déclarée',max_length=160,blank=True)

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        if self.etat=='detail' and not self.libelle.strip():raise ValidationError({'libelle':'Nommez l’évolution déclarée, sans déduire de score ou de changement de situation.'})
        self.verifier_details(('domaine','libelle'))

    class Meta(FaitPersonnelDate.Meta):
        abstract=False
        permissions=[('annuler_evolutionpersonnelledeclaree','Annuler une évolution personnelle déclarée par erreur')]


class RevisionEvolutionPersonnelleDeclaree(TraceSaisie, JournalPersonnel):
    fait=models.ForeignKey(EvolutionPersonnelleDeclaree,on_delete=models.PROTECT,related_name='revisions')


class ImportParametrage(ModeleControle):
    """Confirmation unique d'un catalogue, jamais une restauration de dossiers."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    empreinte=models.CharField(max_length=64,unique=True)
    motif=models.CharField(max_length=240)
    contenu=models.JSONField()
    correspondances=models.JSONField(default=dict)
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enregistre_le=models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions=('view','add')
        permissions=[('exporter_parametrage','Exporter les répertoires et catalogues sans dossiers')]
        ordering=['-enregistre_le']
