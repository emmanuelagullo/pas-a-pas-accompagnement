"""Organisation, responsabilités métier et habilitations : trois relations distinctes."""
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F
from django.utils import timezone
from .cache import ModeleOrganisation


class Periode(ModeleOrganisation):
    debut = models.DateField(default=timezone.localdate)
    fin = models.DateField(null=True, blank=True, help_text='Fin exclue.')

    class Meta:
        abstract = True
        constraints = [models.CheckConstraint(condition=Q(fin__isnull=True) | Q(fin__gt=F('debut')),
            name='%(app_label)s_%(class)s_periode')]

    def clean(self):
        super().clean()
        if self.fin and self.fin <= self.debut:
            raise ValidationError({'fin': 'La fin exclue doit suivre le début.'})


class OrganismeGestionnaire(ModeleOrganisation):
    organisme = models.OneToOneField('personnes.Partenaire', on_delete=models.PROTECT)
    def __str__(self): return str(self.organisme)


class Etablissement(ModeleOrganisation):
    reperage_identites=models.BooleanField(default=False)
    revision=models.PositiveIntegerField(default=0,editable=False)
    organisme = models.ForeignKey(OrganismeGestionnaire, on_delete=models.PROTECT)
    fiche = models.OneToOneField('personnes.Partenaire', on_delete=models.PROTECT)
    def __str__(self): return str(self.fiche)


class Service(ModeleOrganisation):
    POLITIQUES = [('collectif', 'Lecture et écriture collectives'),
        ('lecture', 'Lecture collective, écriture sur les dossiers suivis'),
        ('individuel', 'Lecture et écriture sur les dossiers suivis')]
    etablissement = models.ForeignKey(Etablissement, on_delete=models.PROTECT)
    libelle = models.CharField(max_length=160)
    politique = models.CharField(max_length=12, choices=POLITIQUES, default='collectif')
    revision = models.PositiveIntegerField(default=0, editable=False)
    actif = models.BooleanField(default=True)
    class Meta:
        permissions = [('gerer_organisation', 'Configurer les services et leurs accès explicites')]
        constraints = [models.UniqueConstraint(fields=['etablissement', 'libelle'], name='act_service_nom_unique')]
    def __str__(self): return self.libelle


class LienCompteProfessionnel(ModeleOrganisation):
    compte = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    professionnel = models.OneToOneField('personnes.Intervenant', on_delete=models.PROTECT)


class AppartenanceProfessionnelle(Periode):
    professionnel = models.ForeignKey('personnes.Intervenant', on_delete=models.PROTECT)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    fonction = models.CharField(max_length=160, blank=True)


class Habilitation(Periode):
    TACHES = [('social', 'Accompagnement social'), ('accueil', 'Accueil et mouvements'),
        ('gestion', 'Gestion des prestations'), ('coordination', 'Statistiques regroupées')]
    compte = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    tache = models.CharField(max_length=16, choices=TACHES)
    statistiques_service = models.BooleanField(default=False)
    statistiques_etablissement = models.BooleanField(default=False)
    exporter = models.BooleanField(default=False)
    corriger_autrui = models.BooleanField(default=False)
    accorde_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    cree_le = models.DateTimeField(auto_now_add=True)
    revoque_le = models.DateTimeField(null=True, editable=False)
    revision = models.PositiveIntegerField(default=0, editable=False)


class DossierService(ModeleOrganisation):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    personne = models.ForeignKey('personnes.Personne', null=True, blank=True, on_delete=models.PROTECT)
    menage = models.ForeignKey('personnes.Menage', null=True, blank=True, on_delete=models.PROTECT)
    en_attente = models.BooleanField(default=True)
    revision = models.PositiveIntegerField(default=0, editable=False)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(personne__isnull=False, menage__isnull=True) | Q(personne__isnull=True, menage__isnull=False), name='act_dossier_cible_unique'),
            models.UniqueConstraint(fields=['service', 'personne'], condition=Q(personne__isnull=False), name='act_dossier_personne_unique'),
            models.UniqueConstraint(fields=['service', 'menage'], condition=Q(menage__isnull=False), name='act_dossier_menage_unique')]
    def __str__(self): return str(self.personne or self.menage)


class PorteeObjet(ModeleOrganisation):
    """Origine explicite des faits ; aucune déduction par le nom ou le créateur."""
    modele = models.CharField(max_length=80)
    identifiant = models.CharField(max_length=64)
    dossier = models.ForeignKey(DossierService, on_delete=models.PROTECT, null=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    prise = models.ForeignKey('personnes.Accompagnement', on_delete=models.PROTECT, null=True, blank=True)
    prestation_modele = models.CharField(max_length=40, blank=True)
    prestation_id = models.UUIDField(null=True, blank=True)
    debut_histoire = models.DateField(null=True, blank=True)
    fin_histoire = models.DateField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['modele', 'identifiant'], name='act_portee_objet_unique')]


class Responsabilite(Periode):
    message=models.CharField(max_length=1000,blank=True)
    auteur_libelle=models.CharField(max_length=200,blank=True,editable=False)
    annule_le = models.DateTimeField(null=True, blank=True, editable=False)
    debut = models.DateTimeField(default=timezone.now)
    fin = models.DateTimeField(null=True, blank=True)
    dossier = models.ForeignKey(DossierService, on_delete=models.PROTECT, related_name='responsabilites')
    professionnel = models.ForeignKey('personnes.Intervenant', on_delete=models.PROTECT)
    prise = models.ForeignKey('personnes.Accompagnement', on_delete=models.PROTECT, null=True, blank=True)
    hebergement = models.ForeignKey('personnes.AccordHebergement', on_delete=models.PROTECT, null=True, blank=True)
    repas = models.ForeignKey('personnes.AccordRepas', on_delete=models.PROTECT, null=True, blank=True)
    aide = models.ForeignKey('personnes.AccordAide', on_delete=models.PROTECT, null=True, blank=True)
    role = models.CharField(max_length=16, choices=[('suivi', 'Suivi'), ('ponctuel', 'Intervention ponctuelle'), ('suppleance', 'Remplacement')], default='suivi')
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cree_le = models.DateTimeField(auto_now_add=True)
    class Meta(Periode.Meta):
        constraints = Periode.Meta.constraints + [models.CheckConstraint(condition=(
            Q(prise__isnull=True, hebergement__isnull=True, repas__isnull=True, aide__isnull=True) |
            Q(prise__isnull=False, hebergement__isnull=True, repas__isnull=True, aide__isnull=True) |
            Q(prise__isnull=True, hebergement__isnull=False, repas__isnull=True, aide__isnull=True) |
            Q(prise__isnull=True, hebergement__isnull=True, repas__isnull=False, aide__isnull=True) |
            Q(prise__isnull=True, hebergement__isnull=True, repas__isnull=True, aide__isnull=False)), name='act_responsabilite_cible')]
    def save(self,*args,**kwargs):
        if self._state.adding and not self.auteur_libelle:
            lien=LienCompteProfessionnel.objects.filter(compte_id=self.cree_par_id).select_related('professionnel').first()
            self.auteur_libelle=(str(lien.professionnel) if lien else self.cree_par.get_username())[:200]
        return super().save(*args,**kwargs)
    @property
    def auteur_affiche(self):return self.auteur_libelle or self.cree_par.get_username()
    @property
    def cible(self): return self.hebergement or self.repas or self.aide or self.prise or self.dossier


class JournalAcces(ModeleOrganisation):
    action = models.CharField(max_length=40)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    dossier = models.ForeignKey(DossierService, on_delete=models.PROTECT, null=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    date_effet = models.DateField()
    avant = models.JSONField(default=dict)
    apres = models.JSONField(default=dict)
    cree_le = models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions = ('view',)


class ExploitationLieu(Periode):
    lieu = models.ForeignKey('personnes.LieuHebergement', on_delete=models.PROTECT)
    etablissement = models.ForeignKey(Etablissement, on_delete=models.PROTECT, null=True, blank=True)
    organisme_exterieur = models.ForeignKey('personnes.Partenaire', on_delete=models.PROTECT, null=True, blank=True)
    interlocuteur = models.ForeignKey('personnes.Intervenant', on_delete=models.PROTECT, null=True, blank=True)
    class Meta(Periode.Meta):
        constraints = Periode.Meta.constraints + [models.CheckConstraint(condition=
            Q(etablissement__isnull=False, organisme_exterieur__isnull=True) |
            Q(etablissement__isnull=True, organisme_exterieur__isnull=False), name='act_exploitant_cible')]


class ConfigurationAcces(ModeleOrganisation):
    """Activation explicite après affectation ; ne modifie aucun droit ancien."""
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    active = models.BooleanField(default=False)
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(pk=1), name='act_configuration_unique')]


class DemandeRattachement(ModeleOrganisation):
    dossier=models.ForeignKey(DossierService,on_delete=models.PROTECT,related_name='demandes_rattachement')
    demandeur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    professionnel=models.ForeignKey('personnes.Intervenant',on_delete=models.PROTECT)
    cree_le=models.DateTimeField(auto_now_add=True)
    etat=models.CharField(max_length=12,choices=[('attente','En attente'),('acceptee','Acceptée'),('refusee','Refusée')],default='attente')
    decide_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,related_name='+')
    decide_le=models.DateTimeField(null=True)
    revision=models.PositiveIntegerField(default=0,editable=False)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['dossier','demandeur'],condition=Q(etat='attente'),name='act_demande_rattachement_attente')]


class Notification(ModeleOrganisation):
    """Signal interne sans copie de texte ; autorisations revalidées à la lecture."""
    compte=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    dossier=models.ForeignKey(DossierService,on_delete=models.PROTECT)
    origine=models.ForeignKey(PorteeObjet,on_delete=models.PROTECT,null=True)
    responsabilite=models.ForeignKey(Responsabilite,on_delete=models.PROTECT,null=True)
    cle=models.CharField(max_length=190)
    nature=models.CharField(max_length=20,choices=[('attribution','Un suivi vous a été attribué'),('prestation','Une prestation a été ajoutée'),('modification','Le dossier a été complété ou modifié'),('demande','Une demande de rattachement attend une réponse')])
    modifie_le=models.DateTimeField(default=timezone.now)
    lu_le=models.DateTimeField(null=True)
    occurrences=models.PositiveIntegerField(default=1)
    revision=models.PositiveIntegerField(default=0,editable=False)
    class Meta:
        default_permissions=()
        constraints=[models.UniqueConstraint(fields=['compte','dossier','cle'],name='act_notification_groupe')]
        indexes=[models.Index(fields=['compte','lu_le'],name='act_notification_compte_lu')]
