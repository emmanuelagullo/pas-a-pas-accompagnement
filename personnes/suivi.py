"""Écritures CHRS1 : droits contrôlés et audit dans la même transaction."""
from .verrous_metier import serialiser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, models
from .models import Menage, Appartenance, Accompagnement, EvenementSuivi


def exiger(acteur, *droits):
    if not acteur.has_perms(["personnes." + droit for droit in droits]):
        raise PermissionDenied


@transaction.atomic
def creer_menage(acteur, libelle, personnes, debut, *, identifiant=None):
    exiger(acteur, "view_personne", "view_menage", "add_menage", "add_appartenance")
    if not personnes:
        raise ValidationError("Sélectionnez au moins une personne.")
    menage = Menage(libelle=libelle, cree_par=acteur, **({'pk': identifiant} if identifiant else {}))
    # Dans une confirmation signée, l'INSERT réservé est la première requête
    # SQL : pas de conversion de verrou lecture→écriture sur SQLite. La
    # validation reste dans la transaction et annule l'INSERT en cas d'erreur.
    if identifiant:
        menage.save(force_insert=True)
    menage.full_clean()
    if not identifiant:
        menage.save()
    EvenementSuivi.objects.create(menage=menage, type="menage_cree", auteur=acteur, date_effet=debut)
    for personne in personnes:
        ajouter_appartenance(acteur, menage, personne, debut)
    return menage


@serialiser("menage")
@transaction.atomic
def ajouter_appartenance(acteur, menage, personne, debut, fin=None):
    exiger(acteur, "view_personne", "view_menage", "add_appartenance")
    if Appartenance.objects.filter(menage=menage, personne=personne, debut=debut, fin=fin).exists():
        raise ValidationError("Cette appartenance est déjà enregistrée avec les mêmes dates.")
    objet = Appartenance(menage=menage, personne=personne, debut=debut, fin=fin)
    objet.full_clean()
    objet.save()
    EvenementSuivi.objects.create(menage=menage, appartenance=objet, type="appartenance_ajoutee", auteur=acteur, date_effet=debut)
    return objet


@serialiser("menage")
@transaction.atomic
def ouvrir(acteur, menage, beneficiaires, debut, fin_prevue=None, *, identifiant=None):
    exiger(acteur, "view_personne", "view_menage", "view_accompagnement", "add_accompagnement")
    if not beneficiaires:
        raise ValidationError("Sélectionnez au moins un bénéficiaire.")
    objet = Accompagnement(menage=menage, debut=debut, fin_prevue=fin_prevue, cree_par=acteur,
        **({'pk': identifiant} if identifiant else {}))
    objet.full_clean()
    objet.save()
    objet.beneficiaires.set(beneficiaires)
    EvenementSuivi.objects.create(menage=menage, accompagnement=objet, type="accompagnement_ouvert", auteur=acteur, date_effet=debut)
    return objet


@serialiser("objet")
@transaction.atomic
def clore(acteur, objet, fin):
    accompagnement = isinstance(objet, Accompagnement)
    exiger(acteur, "view_menage", "change_accompagnement" if accompagnement else "change_appartenance")
    if accompagnement:
        exiger(acteur, "view_accompagnement")
    if accompagnement:
        Accompagnement.objects.filter(pk=objet.pk).update(revision_sociale=models.F("revision_sociale") + 1)
        objet = Accompagnement.objects.get(pk=objet.pk)
    if objet.fin is not None:
        raise ValidationError("Cette période est déjà close.")
    if accompagnement:
        from .models import RepasDistribue, Sejour, SituationSociale, EvenementSocial, BilanSocial
        if (SituationSociale.objects.filter(accompagnement=objet, debut__gte=fin).exists()
            or EvenementSocial.objects.filter(accompagnement=objet, date_effet__gte=fin).exists()
            or BilanSocial.objects.filter(accompagnement=objet, date_effet__gte=fin).exists()):
            raise ValidationError("Des informations sociales datées seraient exclues de l’accompagnement.")
        if Sejour.objects.filter(accord__accompagnement=objet).filter(models.Q(fin__isnull=True) | models.Q(fin__gt=fin)).exists():
            raise ValidationError("Clôturez d’abord les séjours au plus tard à la fin de l’accompagnement.")
        if RepasDistribue.objects.filter(accord__accompagnement=objet, annule_le__isnull=True, date__gte=fin).exists():
            raise ValidationError("Des repas distribués existent à cette date ou après. Corrigez-les avant de clôturer.")
    objet.fin = fin
    objet.full_clean()
    # UPDATE conditionnel : une clôture concurrente ne peut pas être écrasée.
    if type(objet).objects.filter(pk=objet.pk, fin__isnull=True).update(fin=fin) != 1:
        raise ValidationError("Cette période vient d’être close. Rechargez la fiche.")
    EvenementSuivi.objects.create(menage=objet.menage, auteur=acteur, date_effet=fin,
        type="accompagnement_clos" if accompagnement else "appartenance_close",
        **({"accompagnement": objet} if accompagnement else {"appartenance": objet}))
