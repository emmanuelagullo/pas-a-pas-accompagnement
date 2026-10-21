"""Informations facultatives : une nouvelle version, jamais d’écrasement."""
from django.core import signing
from django.core.exceptions import ValidationError
from .models import InformationsAccompagnement
from .social import droit, verrouiller
from .corrections import motif_valide
from .verrous_metier import serialiser

CHAMPS = ('referent', 'provenance', 'motif_entree', 'orientation_sortie', 'motif_sortie',
          'destination_sortie', 'objectifs_courts', 'objectifs_longs', 'animaux')


def jeton(accompagnement, information):
    return signing.dumps([str(accompagnement.pk), information.pk if information else None], salt='chrs25-informations')


@serialiser('accompagnement')
def enregistrer(acteur, accompagnement, attendu, motif, **donnees):
    droit(acteur, 'view_informationsaccompagnement')
    droit(acteur, 'add_informationsaccompagnement')
    a = verrouiller(accompagnement)
    derniere = a.informations.first()
    try:
        etat = signing.loads(attendu, salt='chrs25-informations', max_age=86400)
    except signing.BadSignature as exc:
        raise ValidationError('Le formulaire a expiré. Rechargez l’accompagnement.') from exc
    if etat != [str(a.pk), derniere.pk if derniere else None]:
        raise ValidationError('Ces informations ont changé. Rechargez l’accompagnement.')
    motif = motif_valide(motif)
    valeurs = {champ: donnees[champ].strip() for champ in CHAMPS}
    if valeurs == {champ: getattr(derniere, champ) if derniere else '' for champ in CHAMPS}:
        raise ValidationError('Aucune modification.')
    information = InformationsAccompagnement(accompagnement=a, version=derniere.version + 1 if derniere else 1,
        auteur=acteur, motif=motif, **valeurs)
    information.full_clean()
    information.save()
    return information
