"""Écritures CHRS3, périodes civiles et sérialisation par séjour."""
from .verrous_metier import serialiser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from .models import (AccordHebergement, Sejour, Affectation, Absence, LieuHebergement, OperationHebergement)
from .suivi import exiger


def droit(acteur, action):
    exiger(acteur, "view_personne", "view_menage", "view_accompagnement", "view_accordhebergement", "view_sejour", action)


def audit(acteur, accord, action, date, **liens):
    OperationHebergement.objects.create(auteur=acteur, accord=accord, action=action, date_effet=date, **liens)


def verifier_periode(debut, fin):
    if fin is not None and fin <= debut:
        raise ValidationError("La fin exclue doit être postérieure au début.")


def verrouiller(sejour):
    # Première écriture de la transaction : sérialise les mutations d’un séjour
    # sur SQLite comme PostgreSQL. Aucun select_for_update supposé sur SQLite.
    Sejour.objects.filter(pk=sejour.pk).update(revision=F("revision") + 1)
    return Sejour.objects.select_related("accord__accompagnement").get(pk=sejour.pk)


def bornes(sejour, debut, fin):
    verifier_periode(debut, fin)
    if debut < sejour.debut or (sejour.fin and (fin is None or fin > sejour.fin)):
        raise ValidationError("La période doit être comprise dans le séjour.")
    if fin is not None and fin > timezone.localdate():
        raise ValidationError("La fin effective ne peut pas être future.")
    accord = sejour.accord
    suivi = accord.accompagnement
    for limite in (accord.fin, suivi.fin):
        if limite and (debut >= limite or (fin is not None and fin > limite)):
            raise ValidationError("La période dépasse l’accord ou l’accompagnement.")
    if debut > timezone.localdate():
        raise ValidationError("Le début effectif ne peut pas être futur.")


@serialiser("accompagnement")
@transaction.atomic
def accorder(acteur, accompagnement, beneficiaires, debut, fin):
    droit(acteur, "add_accordhebergement")
    accompagnement.refresh_from_db()
    verifier_periode(debut, fin)
    ids = {p.pk for p in beneficiaires}
    if not ids or not ids.issubset(set(accompagnement.beneficiaires.values_list("pk", flat=True))):
        raise ValidationError("Sélectionnez des bénéficiaires de cet accompagnement.")
    if debut < accompagnement.debut or (accompagnement.fin and (fin is None or fin > accompagnement.fin)):
        raise ValidationError("L’accord doit être compris dans l’accompagnement.")
    accord = AccordHebergement(accompagnement=accompagnement, debut=debut, fin=fin, cree_par=acteur)
    accord.full_clean(); accord.save(); accord.beneficiaires.set(ids)
    audit(acteur, accord, "Hébergement accordé", debut)
    return accord


@serialiser("accord")
@transaction.atomic
def admettre(acteur, accord, beneficiaires, debut):
    droit(acteur, "add_sejour")
    accord = AccordHebergement.objects.select_related("accompagnement").get(pk=accord.pk)
    ids = {p.pk for p in beneficiaires}
    if not ids or not ids.issubset(set(accord.beneficiaires.values_list("pk", flat=True))):
        raise ValidationError("Sélectionnez des bénéficiaires de cet accord.")
    if debut < accord.debut or (accord.fin and debut >= accord.fin) or debut > timezone.localdate():
        raise ValidationError("L’admission effective doit être dans l’accord et non future.")
    suivi = accord.accompagnement
    if debut < suivi.debut or (suivi.fin and debut >= suivi.fin):
        raise ValidationError("L’admission doit être dans l’accompagnement.")
    sejour = Sejour.objects.create(accord=accord, debut=debut, cree_par=acteur)
    sejour.beneficiaires.set(ids)
    audit(acteur, accord, "Admission effective", debut, sejour=sejour)
    return sejour


@transaction.atomic
def creer_lieu(acteur, libelle, partenaire=""):
    droit(acteur, "add_lieuhebergement")
    exiger(acteur, "view_lieuhebergement")
    lieu = LieuHebergement(libelle=libelle, partenaire=partenaire, cree_par=acteur)
    lieu.full_clean(); lieu.save()
    return lieu


@serialiser("sejour")
@transaction.atomic
def ajouter_periode(acteur, sejour, debut, fin, lieu=None, absence=False):
    droit(acteur, "add_absence" if absence else "add_affectation")
    exiger(acteur, "view_absence" if absence else "view_affectation")
    if not absence:
        exiger(acteur, "view_lieuhebergement")
        if lieu is None: raise ValidationError("Choisissez un lieu.")
    sejour = verrouiller(sejour)
    bornes(sejour, debut, fin)
    modele = Absence if absence else Affectation
    existants = modele.objects.filter(sejour=sejour).filter(Q(fin__isnull=True) | Q(fin__gt=debut))
    if fin is not None: existants = existants.filter(debut__lt=fin)
    if existants.exists():
        raise ValidationError("Cette période chevauche une période du même type dans ce séjour.")
    objet = modele(sejour=sejour, debut=debut, fin=fin, **({} if absence else {"lieu": lieu}))
    objet.full_clean(); objet.save()
    audit(acteur, sejour.accord, "Absence enregistrée" if absence else "Affectation enregistrée", debut,
        sejour=sejour, **({"absence": objet} if absence else {"affectation": objet}))
    return objet


@serialiser("objet")
@transaction.atomic
def terminer_periode(acteur, objet, fin):
    absence = isinstance(objet, Absence)
    droit(acteur, "change_absence" if absence else "change_affectation")
    exiger(acteur, "view_absence" if absence else "view_affectation")
    sejour = verrouiller(objet.sejour)
    objet = type(objet).objects.get(pk=objet.pk)
    if objet.fin is not None: raise ValidationError("Cette période est déjà close.")
    bornes(sejour, objet.debut, fin)
    if fin > timezone.localdate(): raise ValidationError("La fin effective ne peut pas être future.")
    objet.fin = fin; objet.save(update_fields=["fin"])
    audit(acteur, sejour.accord, "Absence close" if absence else "Affectation close", fin,
        sejour=sejour, **({"absence": objet} if absence else {"affectation": objet}))


@serialiser("sejour")
@transaction.atomic
def sortir(acteur, sejour, fin):
    droit(acteur, "change_sejour")
    # La sortie peut clôturer automatiquement les périodes encore ouvertes.
    exiger(acteur, "change_affectation", "change_absence")
    sejour = verrouiller(sejour)
    if sejour.fin is not None: raise ValidationError("Le séjour est déjà clos.")
    verifier_periode(sejour.debut, fin)
    if fin > timezone.localdate(): raise ValidationError("La sortie effective ne peut pas être future.")
    suivi = sejour.accord.accompagnement
    if (sejour.accord.fin and fin > sejour.accord.fin) or (suivi.fin and fin > suivi.fin):
        raise ValidationError("La sortie doit respecter la fin de l’accord et de l’accompagnement.")
    for modele in (Affectation, Absence):
        for objet in modele.objects.filter(sejour=sejour):
            if objet.debut >= fin or (objet.fin and objet.fin > fin):
                raise ValidationError("Des périodes enregistrées dépassent la sortie demandée.")
            if objet.fin is None:
                objet.fin = fin; objet.save(update_fields=["fin"])
                audit(acteur, sejour.accord, "Absence close à la sortie" if modele is Absence else "Affectation close à la sortie", fin,
                    sejour=sejour, **({"absence": objet} if modele is Absence else {"affectation": objet}))
    sejour.fin = fin; sejour.save(update_fields=["fin"])
    audit(acteur, sejour.accord, "Sortie effective", fin, sejour=sejour)
