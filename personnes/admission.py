from acteurs.contexte import service_metier
"""Admission guidée : services existants, sous une transaction commune."""
from django.core import signing
from django.core.exceptions import ValidationError
from . import hebergement as h
from .social import verrouiller
from .verrous_metier import serialiser


def etat(accompagnement, revision=None):
    return [str(accompagnement.pk), accompagnement.revision_sociale if revision is None else revision,
        str(accompagnement.debut), str(accompagnement.fin),
        sorted(str(pk) for pk in accompagnement.beneficiaires.values_list('pk', flat=True))]


def jeton(accompagnement):
    return signing.dumps(etat(accompagnement), salt='bd6-sejour-unifie-v1')


@service_metier
@serialiser('accompagnement')
def accueillir(acteur, accompagnement, beneficiaires, debut, fin, admission, attendu, lieu=None, arrivee_effectuee=True):
    h.droit(acteur, 'add_accordhebergement')
    if arrivee_effectuee:
        h.exiger(acteur, 'add_sejour')
        if admission is None:
            raise ValidationError('Indiquez la date de l’arrivée effectuée.')
    elif admission is not None or lieu is not None:
        raise ValidationError('Un accueil prévu ne comporte ni arrivée effective ni affectation.')
    if lieu is not None:
        h.exiger(acteur, 'add_affectation', 'view_affectation', 'view_lieuhebergement')
    a = verrouiller(accompagnement)
    try:
        precedent = signing.loads(attendu, salt='bd6-sejour-unifie-v1', max_age=86400)
    except (signing.BadSignature, TypeError, ValueError) as exc:
        raise ValidationError('Le formulaire a expiré. Rechargez l’accompagnement.') from exc
    if precedent != etat(a, a.revision_sociale - 1):
        raise ValidationError('Cet accompagnement a changé. Rechargez le formulaire avant une nouvelle admission.')
    beneficiaires = list(beneficiaires)
    accord = h.accorder(acteur, a, beneficiaires, debut, fin)
    if not arrivee_effectuee:
        return accord
    sejours = h.admettre_individuellement(acteur, accord, beneficiaires, admission)
    if lieu is not None:
        for sejour in sejours:
            h.ajouter_periode(acteur, sejour, admission, None, lieu)
    return accord


@service_metier
@serialiser('accord')
def enregistrer_arrivee(acteur, accord, beneficiaires, debut, attendu, lieu=None):
    """Confirmer les premières arrivées d’un accord existant, sans créer d’accord."""
    from .models import AccordHebergement
    from . import accords
    h.droit(acteur, 'add_sejour')
    accord = AccordHebergement.objects.select_related('accompagnement').get(pk=accord.pk)
    accords.exiger_actif(accord)
    accords.verifier(accord, attendu)
    personnes = list(beneficiaires)
    if accord.sejours.non_annules().filter(beneficiaires__in=personnes).exists():
        raise ValidationError('Une arrivée est déjà enregistrée pour une personne sélectionnée. Rechargez la liste.')
    if lieu is not None:
        h.exiger(acteur, 'add_affectation', 'view_affectation', 'view_lieuhebergement')
    sejours = h.admettre_individuellement(acteur, accord, personnes, debut)
    if lieu is not None:
        for sejour in sejours:
            h.ajouter_periode(acteur, sejour, debut, None, lieu)
    return sejours
