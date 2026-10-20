"""CHRS4 : valeurs datées par dimension, sans reconstruction événementielle."""
from .verrous_metier import serialiser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from .models import Accompagnement, SituationSociale, EvenementSocial, BilanSocial, OperationSociale
from .suivi import exiger


def droit(acteur, action):
    exiger(acteur, "view_personne", "view_menage", "view_accompagnement", action)


def verrouiller(accompagnement):
    Accompagnement.objects.filter(pk=accompagnement.pk).update(revision_sociale=F("revision_sociale")+1)
    return Accompagnement.objects.get(pk=accompagnement.pk)


def date_valide(accompagnement, date):
    if date < accompagnement.debut or (accompagnement.fin and date >= accompagnement.fin) or date > timezone.localdate():
        raise ValidationError("La date d’effet doit appartenir à l’accompagnement et ne pas être future.")


def personne_valide(accompagnement, personne):
    if not accompagnement.beneficiaires.filter(pk=personne.pk).exists():
        raise ValidationError("Choisissez un bénéficiaire de cet accompagnement.")


@serialiser("accompagnement")
@transaction.atomic
def renseigner(acteur, accompagnement, beneficiaire, dimension, valeur, debut, source):
    droit(acteur,"add_situationsociale")
    droit(acteur,"view_situationsociale")
    a=verrouiller(accompagnement)
    date_valide(a,debut); personne_valide(a,beneficiaire)
    serie=SituationSociale.objects.filter(accompagnement=a,beneficiaire=beneficiaire,dimension=dimension)
    precedente=serie.order_by("-debut").first()
    if precedente and debut <= precedente.debut:
        raise ValidationError("Ajoutez une date postérieure à la dernière valeur. Pour une erreur de valeur, utilisez Corriger.")
    nouvelle=SituationSociale(accompagnement=a,beneficiaire=beneficiaire,dimension=dimension,valeur=valeur,debut=debut,source=source,cree_par=acteur)
    # Valider les champs avant de fermer la valeur précédente ; les contraintes
    # d’unicité sont ensuite vérifiées dans la même transaction.
    nouvelle.clean_fields(); nouvelle.clean()
    if precedente:
        precedente.fin=debut; precedente.save(update_fields=["fin"])
    nouvelle.full_clean(); nouvelle.save()
    OperationSociale.objects.create(accompagnement=a,situation=nouvelle,action="Situation renseignée",date_effet=debut,auteur=acteur,nouvelle_valeur=valeur)
    return nouvelle


@serialiser("situation")
@transaction.atomic
def corriger(acteur, situation, valeur, motif):
    droit(acteur,"change_situationsociale"); droit(acteur,"view_situationsociale")
    a=verrouiller(situation.accompagnement)
    situation=SituationSociale.objects.get(pk=situation.pk)
    motif=motif.strip()
    if not motif or len(motif)>240: raise ValidationError("Indiquez un motif de 1 à 240 caractères.")
    ancienne=situation.valeur
    if ancienne==valeur: raise ValidationError("La valeur est inchangée.")
    situation.valeur=valeur; situation.full_clean(); situation.save(update_fields=["valeur"])
    OperationSociale.objects.create(accompagnement=a,situation=situation,action="Valeur corrigée",date_effet=situation.debut,auteur=acteur,ancienne_valeur=ancienne,nouvelle_valeur=valeur,motif=motif)
    return situation


@serialiser("accompagnement")
@transaction.atomic
def evenement(acteur, accompagnement, beneficiaire, date_effet, texte, source):
    droit(acteur,"add_evenementsocial"); droit(acteur,"view_evenementsocial")
    a=verrouiller(accompagnement)
    date_valide(a,date_effet); personne_valide(a,beneficiaire)
    objet=EvenementSocial(accompagnement=a,beneficiaire=beneficiaire,date_effet=date_effet,texte=texte,source=source,cree_par=acteur)
    objet.full_clean(); objet.save()
    OperationSociale.objects.create(accompagnement=a,evenement=objet,action="Événement enregistré",date_effet=date_effet,auteur=acteur)
    return objet


@serialiser("accompagnement")
@transaction.atomic
def bilan(acteur, accompagnement, date_effet, texte):
    droit(acteur,"add_bilansocial"); droit(acteur,"view_bilansocial")
    a=verrouiller(accompagnement)
    date_valide(a,date_effet)
    objet=BilanSocial(accompagnement=a,date_effet=date_effet,texte=texte,cree_par=acteur)
    objet.full_clean(); objet.save()
    OperationSociale.objects.create(accompagnement=a,bilan=objet,action="Bilan enregistré",date_effet=date_effet,auteur=acteur)
    return objet


def etat_date(accompagnement, date):
    if date < accompagnement.debut or (accompagnement.fin and date >= accompagnement.fin):
        return SituationSociale.objects.none()
    return accompagnement.situations_sociales.filter(debut__lte=date).filter(Q(fin__isnull=True)|Q(fin__gt=date)).select_related("beneficiaire")
