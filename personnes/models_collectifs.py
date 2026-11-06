"""COL2–4 : faits collectifs typés ; aucune identité anonyme artificielle."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q, F
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from acteurs.listes_saisie import DESTINATION_SORTIE
from acteurs.managers import ModeleControle


class CompositionCollective(ModeleControle):
    menage = models.ForeignKey('personnes.Menage', on_delete=models.PROTECT)
    accompagnement = models.ForeignKey('personnes.Accompagnement', on_delete=models.PROTECT, null=True, blank=True)
    reference = models.ForeignKey('personnes.Personne', on_delete=models.PROTECT, related_name='+')
    service = models.ForeignKey('acteurs.Service', on_delete=models.PROTECT)
    debut = models.DateField('Date de la composition déclarée')
    identifies = models.ManyToManyField('personnes.Personne', related_name='+')
    identites = models.JSONField(default=list, editable=False)
    pour_prestation = models.BooleanField(default=False, editable=False)
    # Schéma fermé validé par collectifs.verifier_composition : pas d'attributs libres.
    complements = models.JSONField(default=list, blank=True)
    categories = models.JSONField()
    logement = models.CharField('Situation de logement du ménage', max_length=240, blank=True)
    revenu = models.DecimalField('Revenu mensuel déclaré du ménage', max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    dette = models.DecimalField('Total de dettes déclaré du ménage', max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    devise = models.CharField(max_length=3, default='EUR')
    telephone = models.CharField('Téléphone commun du ménage', max_length=80, blank=True)
    courriel = models.EmailField('Courriel commun du ménage', blank=True)
    projet = models.TextField('Projet collectif déclaré', max_length=4000, blank=True)
    source = models.CharField(max_length=160, blank=True)
    remplace = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    annule_le = models.DateTimeField(null=True, editable=False)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions = ('view', 'add', 'change')
        ordering = ['-debut', '-pk']


class PrestationCollective(ModeleControle):
    """Identité de prestation ; les décisions sont des versions conservées."""
    NATURES = [('hebergement', 'Hébergement'), ('restauration', 'Restauration')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    accompagnement = models.ForeignKey('personnes.Accompagnement', on_delete=models.PROTECT, related_name='prestations_collectives')
    nature = models.CharField(max_length=16, choices=NATURES)
    revision = models.PositiveIntegerField(default=0, editable=False)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions = ('view', 'add', 'change')
        ordering = ['-enregistre_le', 'pk']
    @property
    def courante(self):
        return self.versions.order_by('-numero').first()


class VersionPrestationCollective(ModeleControle):
    destination_sortie = models.CharField(DESTINATION_SORTIE, max_length=160, blank=True)
    prestation = models.ForeignKey(PrestationCollective, on_delete=models.PROTECT, related_name='versions')
    offre = models.ForeignKey('acteurs.OffrePrestataire', on_delete=models.PROTECT, null=True, blank=True)
    libelle_offre = models.CharField(max_length=160, blank=True)
    composition = models.ForeignKey(CompositionCollective, on_delete=models.PROTECT)
    numero = models.PositiveIntegerField()
    action = models.CharField(max_length=16, choices=[('creation','Création'),('correction','Correction'),('prolongation','Prolongation'),('depart','Départ'),('annulation','Annulation')])
    debut = models.DateField('Début')
    fin = models.DateField('Dernier jour / départ', null=True, blank=True)
    fin_prevue = models.DateField('Départ prévu', null=True, blank=True)
    arrivee = models.DateField('Arrivée effective', null=True, blank=True)
    lieu = models.ForeignKey('personnes.LieuHebergement', on_delete=models.PROTECT, null=True, blank=True)
    prestataire = models.ForeignKey('personnes.Partenaire', on_delete=models.PROTECT, null=True, blank=True)
    dejeuner = models.BooleanField(default=True)
    diner = models.BooleanField(default=True)
    premier = models.CharField(max_length=12, default='dejeuner', choices=[('dejeuner','Déjeuner'),('diner','Dîner')])
    dernier = models.CharField(max_length=12, default='diner', choices=[('dejeuner','Déjeuner'),('diner','Dîner')])
    petits_dejeuners = models.BooleanField(default=False)
    devise = models.CharField(max_length=3, default='EUR')
    motif = models.CharField(max_length=240, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions = ('view',)
        constraints = [models.UniqueConstraint(fields=['prestation','numero'], name='col_version_unique')]
        ordering = ['-numero']


class CouvertCollectif(ModeleControle):
    version = models.ForeignKey(VersionPrestationCollective, on_delete=models.PROTECT, related_name='couverts')
    categorie = models.CharField(max_length=40)
    libelle = models.CharField(max_length=80)
    nombre = models.PositiveSmallIntegerField('Couverts par repas')
    prix = models.DecimalField('Prix par repas', max_digits=14, decimal_places=4, null=True, blank=True, validators=[MinValueValidator(0)])
    tarif = models.ForeignKey('personnes.VersionTarif', on_delete=models.PROTECT, null=True, blank=True)
    prix_diner = models.DecimalField('Prix du dîner différent', max_digits=14, decimal_places=4, null=True, blank=True, validators=[MinValueValidator(0)])
    tarif_diner = models.ForeignKey('personnes.VersionTarif', on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    class Meta:
        default_permissions = ('view',)
        constraints = [models.UniqueConstraint(fields=['version','categorie'], name='col_couvert_unique')]


class MouvementCollectif(ModeleControle):
    prestation = models.ForeignKey(PrestationCollective, on_delete=models.PROTECT, related_name='mouvements')
    nature = models.CharField(max_length=8, choices=[('lieu','Affectation'),('absence','Absence')])
    debut = models.DateField()
    fin = models.DateField(null=True, blank=True)
    lieu = models.ForeignKey('personnes.LieuHebergement', on_delete=models.PROTECT, null=True, blank=True)
    annule_le = models.DateTimeField(null=True, editable=False)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions = ('view','add','change')
        constraints = [models.CheckConstraint(condition=Q(fin__isnull=True)|Q(fin__gt=F('debut')), name='col_mouvement_periode')]


class JournalCollectif(ModeleControle):
    prestation = models.ForeignKey(PrestationCollective, on_delete=models.PROTECT, null=True, blank=True)
    composition = models.ForeignKey(CompositionCollective, on_delete=models.PROTECT, null=True, blank=True)
    mouvement = models.ForeignKey(MouvementCollectif, on_delete=models.PROTECT, null=True, blank=True)
    action = models.CharField(max_length=40)
    avant = models.JSONField(default=dict)
    apres = models.JSONField(default=dict)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enregistre_le = models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions = ('view',)
        ordering = ['-pk']
