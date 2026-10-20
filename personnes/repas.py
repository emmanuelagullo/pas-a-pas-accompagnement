"""CHRS2 : accords immuables et réalisations annulables, droits explicites."""
from .verrous_metier import serialiser
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone
from .models import AccordRepas, RepasDistribue, OperationRepas, Accompagnement
from .suivi import exiger


def droit(acteur, action):
    exiger(acteur, "view_personne", "view_menage", "view_accompagnement", "view_accordrepas", action)


@serialiser("accompagnement")
@transaction.atomic
def accorder(acteur, accompagnement, beneficiaires, debut, fin, service, prestataire=""):
    droit(acteur, "add_accordrepas")
    accompagnement = Accompagnement.objects.get(pk=accompagnement.pk)
    ids = {p.pk for p in beneficiaires}
    if not ids or not ids.issubset(set(accompagnement.beneficiaires.values_list("pk", flat=True))):
        raise ValidationError("Choisissez des bénéficiaires de cet accompagnement.")
    if debut < accompagnement.debut or (accompagnement.fin and (fin is None or fin > accompagnement.fin)):
        raise ValidationError("La période accordée doit être comprise dans l’accompagnement.")
    accord = AccordRepas(accompagnement=accompagnement, debut=debut, fin=fin, service=service, prestataire=prestataire, cree_par=acteur)
    accord.full_clean()
    accord.save()
    accord.beneficiaires.set(ids)
    OperationRepas.objects.create(accord=accord, action="accorde", auteur=acteur, date_effet=debut)
    return accord


@serialiser("accord")
@transaction.atomic
def distribuer(acteur, accord, beneficiaire, date, quantite):
    droit(acteur, "add_repasdistribue")
    exiger(acteur, "view_repasdistribue")
    accord = AccordRepas.objects.select_related("accompagnement").get(pk=accord.pk)
    if not accord.beneficiaires.filter(pk=beneficiaire.pk).exists():
        raise ValidationError("Cette personne ne bénéficie pas de cet accord.")
    if date < accord.debut or (accord.fin and date >= accord.fin):
        raise ValidationError("La distribution doit se situer dans la période accordée.")
    suivi = accord.accompagnement
    if date < suivi.debut or (suivi.fin and date >= suivi.fin):
        raise ValidationError("La distribution doit se situer dans l’accompagnement.")
    if date > timezone.localdate():
        raise ValidationError("Une distribution effective ne peut pas être future.")
    repas = RepasDistribue(accord=accord, beneficiaire=beneficiaire, date=date, quantite=quantite, cree_par=acteur)
    repas.full_clean()
    try:
        with transaction.atomic():
            repas.save()
    except IntegrityError as erreur:
        raise ValidationError("Une distribution existe déjà pour cet accord, cette personne et ce jour. Rechargez la fiche.") from erreur
    OperationRepas.objects.create(accord=accord, repas=repas, action="distribue", auteur=acteur, date_effet=date)
    return repas


@serialiser("repas")
@transaction.atomic
def annuler(acteur, repas, motif):
    droit(acteur, "change_repasdistribue")
    exiger(acteur, "view_repasdistribue")
    motif = motif.strip()
    if not motif or len(motif) > 240:
        raise ValidationError("Indiquez un motif de 1 à 240 caractères.")
    if RepasDistribue.objects.filter(pk=repas.pk, annule_le__isnull=True).update(annule_le=timezone.now(), annule_par=acteur, motif_annulation=motif) != 1:
        raise ValidationError("Cette distribution est déjà annulée.")
    OperationRepas.objects.create(accord=repas.accord, repas=repas, action="annule", auteur=acteur, date_effet=repas.date)
