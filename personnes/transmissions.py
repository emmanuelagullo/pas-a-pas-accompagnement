"""Écriture transactionnelle des transmissions et notes métier."""
from . import textes_riches as tr
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
    return Transmission.objects.create(auteur=auteur, **tr.colonnes('contenu', contenu, required=True))


@transaction.atomic
def noter(auteur, contenu, *, personne=None, accompagnement=None, sejour=None):
    _droit(auteur, "add", "notepartagee")
    cibles = [c for c in (personne, accompagnement, sejour) if c is not None]
    if len(cibles) != 1:
        raise ValidationError("Une note doit avoir exactement un rattachement.")
    cible = cibles[0]
    _droit(auteur, "view", {"Personne": "personne", "Accompagnement": "accompagnement", "Sejour": "sejour"}[type(cible).__name__])
    return NotePartagee.objects.create(auteur=auteur, **tr.colonnes('contenu', contenu, required=True), personne=personne,
                                      accompagnement=accompagnement, sejour=sejour)


@transaction.atomic
def rectifier(auteur, contribution, nouveau_texte, motif, *, texte_attendu=None, etat_attendu=None):
    """Correction conservant chaque version, sous verrou transactionnel."""
    from .models import RevisionContribution
    modele = "transmission" if isinstance(contribution, Transmission) else "notepartagee"
    _droit(auteur, "change", modele)
    if modele == "notepartagee":
        cible = contribution.personne or contribution.accompagnement or contribution.sejour
        _droit(auteur, "view", type(cible).__name__.lower())
    nouveau_texte, motif = tr.preparer(nouveau_texte, required=True), _texte(motif)
    objet = type(contribution).objects.select_for_update().get(pk=contribution.pk)
    if etat_attendu:
        verifier_etat(objet, etat_attendu)
    elif objet.contenu_document is not None and texte_attendu is not None:
        raise ValidationError('Rechargez la contribution enrichie avant de la corriger.')
    if texte_attendu is not None and objet.contenu != texte_attendu:
        raise ValidationError("Cette contribution a été modifiée entre-temps. Rechargez-la avant de corriger.")
    if objet.contenu == nouveau_texte and objet.contenu_document == nouveau_texte.document:
        raise ValidationError("La correction doit modifier le texte.")
    # Comparer-et-échanger aussi sur SQLite ; le verrou de ligne seul ne suffit pas.
    condition = {'contenu_document__isnull': True} if objet.contenu_document is None else {'contenu_document': objet.contenu_document}
    change = type(objet).objects.filter(pk=objet.pk, contenu=objet.contenu,
        **condition).update(contenu=str(nouveau_texte), contenu_document=nouveau_texte.document)
    if change != 1:
        raise ValidationError('Cette contribution a changé. Votre saisie est conservée.')
    revision = RevisionContribution.objects.create(
        transmission=objet if modele == "transmission" else None,
        note=objet if modele == "notepartagee" else None,
        auteur=auteur, ancien_texte=objet.contenu, nouveau_texte=str(nouveau_texte),
        ancien_texte_document=objet.contenu_document, nouveau_texte_document=nouveau_texte.document, motif=motif)
    objet.contenu = str(nouveau_texte)
    objet.contenu_document = nouveau_texte.document

    return revision


def jeton(objet):
    from django.core import signing
    return signing.dumps([objet._meta.model_name, objet.pk, objet.contenu, objet.contenu_document], salt='texte-contribution-v1')


def verifier_etat(objet, attendu):
    from django.core import signing
    try:
        etat = signing.loads(attendu, salt='texte-contribution-v1', max_age=86400)
    except signing.BadSignature as exc:
        raise ValidationError('Le formulaire a expiré. Votre saisie est conservée.') from exc
    if etat != [objet._meta.model_name, objet.pk, objet.contenu, objet.contenu_document]:
        raise ValidationError('Cette contribution a été modifiée entre-temps. Votre saisie est conservée ; consultez la version actuelle avant de réessayer.')
