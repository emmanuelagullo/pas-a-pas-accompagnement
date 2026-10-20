"""Écriture transactionnelle des transmissions et notes métier."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from .models import Transmission, NotePartagee


def _droit(auteur, action, modele):
    if not auteur.is_authenticated or not auteur.has_perm(f"personnes.{action}_{modele}"):
        raise PermissionDenied


def _texte(valeur):
    valeur = (valeur or "").strip()
    if not valeur:
        raise ValidationError("Le texte est obligatoire.")
    return valeur


@transaction.atomic
def transmettre(auteur, contenu):
    _droit(auteur, "add", "transmission")
    return Transmission.objects.create(auteur=auteur, contenu=_texte(contenu))


@transaction.atomic
def noter(auteur, contenu, *, personne=None, accompagnement=None, sejour=None):
    _droit(auteur, "add", "notepartagee")
    cibles = [c for c in (personne, accompagnement, sejour) if c is not None]
    if len(cibles) != 1:
        raise ValidationError("Une note doit avoir exactement un rattachement.")
    cible = cibles[0]
    _droit(auteur, "view", {"Personne": "personne", "Accompagnement": "accompagnement", "Sejour": "sejour"}[type(cible).__name__])
    return NotePartagee.objects.create(auteur=auteur, contenu=_texte(contenu), personne=personne,
                                      accompagnement=accompagnement, sejour=sejour)


@transaction.atomic
def rectifier(auteur, contribution, nouveau_texte, motif):
    """Correction conservant chaque version, sous verrou transactionnel."""
    from .models import RevisionContribution
    modele = "transmission" if isinstance(contribution, Transmission) else "notepartagee"
    _droit(auteur, "change", modele)
    if modele == "notepartagee":
        cible = contribution.personne or contribution.accompagnement or contribution.sejour
        _droit(auteur, "view", type(cible).__name__.lower())
    nouveau_texte, motif = _texte(nouveau_texte), _texte(motif)
    objet = type(contribution).objects.select_for_update().get(pk=contribution.pk)
    if objet.contenu == nouveau_texte:
        raise ValidationError("La correction doit modifier le texte.")
    revision = RevisionContribution.objects.create(
        transmission=objet if modele == "transmission" else None,
        note=objet if modele == "notepartagee" else None,
        auteur=auteur, ancien_texte=objet.contenu, nouveau_texte=nouveau_texte, motif=motif)
    objet.contenu = nouveau_texte
    objet.save(update_fields=["contenu"])
    return revision
