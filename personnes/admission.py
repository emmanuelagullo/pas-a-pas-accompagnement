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


def modifier_fin_prise(acteur, a, debut, fin):
    from django.utils import timezone
    from .models import EvolutionPriseEnCharge

    h.exiger(acteur, 'change_accompagnement')
    ancienne_fin = a.fin
    if not ancienne_fin or debut < a.debut or (debut < ancienne_fin and fin and fin <= ancienne_fin):
        raise ValidationError('La fin de cette prise en charge ne nécessite pas de modification.')
    a.fin = fin if fin and fin <= timezone.localdate() else None
    a.full_clean()
    a.save(update_fields=['fin'])
    EvolutionPriseEnCharge.objects.create(
        accompagnement=a, ancienne_fin=ancienne_fin, nouvelle_fin=a.fin,
        action='fin_effective', auteur=acteur,
    )


def peut_ouvrir_apres_interruption(acteur, prise, debut, fin=None):
    return bool(debut and prise and ((prise.fin and debut > prise.fin) or (fin and fin < prise.debut)) and acteur.has_perms([
        'personnes.view_personne', 'personnes.view_menage',
        'personnes.view_accompagnement', 'personnes.add_accompagnement',
    ]))


def ouvrir_apres_interruption(acteur, prise, beneficiaires, debut, fin, confirme, *, verrouille=False):
    from acteurs import portees
    from acteurs.contexte import perimetre
    from . import suivi

    if not verrouille:
        prise = verrouiller(prise)
    if (prise.fin, prise.revision_sociale - 1) != confirme:
        raise ValidationError('La prise en charge a changé. Rechargez le formulaire avant de confirmer.')
    if not peut_ouvrir_apres_interruption(acteur, prise, debut, fin):
        raise ValidationError('Une nouvelle prise en charge est proposée lorsqu’une interruption sépare les deux périodes.')
    origine = portees.existante(prise)
    with perimetre(acteur, service=origine.service_id if origine else None):
        return suivi.ouvrir(acteur, prise.menage, beneficiaires, debut, fin)


@service_metier
@serialiser('accompagnement')
def accueillir(acteur, accompagnement, beneficiaires, debut, fin, admission, attendu, lieu=None, arrivee_effectuee=True, nouvelle_prise=False, prise_confirmee=None):
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
    if prise_confirmee:
        from .validation_prestations import appliquer_resolution
        a = appliquer_resolution(acteur, a, debut, fin, prise_confirmee, verrouille=True)
    beneficiaires = list(beneficiaires)
    if nouvelle_prise:
        a = ouvrir_apres_interruption(acteur, a, beneficiaires, debut, fin, nouvelle_prise, verrouille=True)
    accord = h.accorder(acteur, a, beneficiaires, debut, fin)
    if not arrivee_effectuee:
        return accord
    sejour = h.admettre(acteur, accord, beneficiaires, admission)
    if lieu is not None:
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
    sejour = h.admettre(acteur, accord, personnes, debut)
    if lieu is not None:
        h.ajouter_periode(acteur, sejour, debut, None, lieu)
    return [sejour]
