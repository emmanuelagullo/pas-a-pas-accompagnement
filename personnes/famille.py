"""Histoire familiale typée et corrections de valeurs/dates sous réservation personnelle."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from . import bd6, suivi
from .models import DeclarationFamiliale, RevisionDeclarationFamiliale

CHAMPS = ('situation_familiale', 'rapports_parentaux', 'fratrie',
    'enfants_a_charge', 'enfants_non_a_charge', 'grossesse')
DROITS_LECTURE = ('personnes.view_personne', 'personnes.view_declarationfamiliale',
    'personnes.view_revisiondeclarationfamiliale')


def photographie(personne):
    return [{'id': x.pk, 'debut': x.debut.isoformat(), 'fin': x.fin.isoformat() if x.fin else None,
        **{champ: getattr(x, champ) for champ in CHAMPS}, 'source': x.source}
        for x in personne.declarations_familiales.order_by('debut', 'pk')]


def renseigner(acteur, personne, debut, source, attendu, motif='', correction=None, **valeurs):
    suivi.exiger(acteur, 'view_personne', 'view_declarationfamiliale', 'view_revisiondeclarationfamiliale', 'add_declarationfamiliale')
    return _renseigner(acteur, personne, debut, source, attendu, motif, correction, valeurs)


@transaction.atomic
def _renseigner(acteur, personne, debut, source, attendu, motif, correction, valeurs):
    # Les droits sont chargés avant d'ouvrir la transaction : la réservation
    # personnelle est bien sa première requête SQL, même pour un compte neuf.
    bd6.reserver(personne, attendu)
    if set(valeurs) != set(CHAMPS):
        raise ValidationError('La déclaration doit préciser toutes ses rubriques, y compris les valeurs inconnues.')
    if debut > timezone.localdate():
        raise ValidationError({'debut': 'Une déclaration de situation ne peut pas être future.'})
    if not source.strip():
        raise ValidationError({'source': 'Indiquez la source de cette déclaration.'})
    if len(motif) > 240:
        raise ValidationError({'motif': 'Le motif est limité à 240 caractères.'})
    avant = photographie(personne)
    serie = list(personne.declarations_familiales.order_by('debut', 'pk'))
    if correction is not None:
        suivi.exiger(acteur, 'change_declarationfamiliale')
        fait = next((x for x in serie if x.pk == correction), None)
        if fait is None:
            raise ValidationError('La déclaration ne correspond pas à cette personne.')
        action = 'correction'
        if fait.debut == debut and fait.source == source.strip() and all(getattr(fait, c) == valeurs[c] for c in CHAMPS):
            raise ValidationError('Aucune modification de la déclaration.')
    else:
        fait = DeclarationFamiliale(personne=personne, auteur=acteur)
        action = 'insertion' if any(x.debut > debut for x in serie) else 'changement'
        serie.append(fait)
    if action != 'changement':
        suivi.exiger(acteur, 'change_declarationfamiliale')
        if not motif.strip():
            raise ValidationError({'motif': 'Expliquez la correction ou l’ajout d’un fait antérieur oublié.'})
    if any(x is not fait and x.debut == debut for x in serie):
        raise ValidationError({'debut': 'Une déclaration existe déjà à cette date. Corrigez-la explicitement.'})
    fait.debut, fait.source = debut, source.strip()
    for champ in CHAMPS:
        setattr(fait, champ, valeurs[champ])
    serie.sort(key=lambda x: x.debut)
    for i, x in enumerate(serie):
        x.fin = serie[i + 1].debut if i + 1 < len(serie) else None
    # Fermer d'abord l'ancienne ligne ouverte pour respecter l'unicité SQL.
    # Une correction de date reste dans sa position chronologique : traverser
    # un autre fait changerait le sens de toute la série.
    if correction is not None:
        anciens_ids = [x['id'] for x in avant]
        if [x.pk for x in serie] != anciens_ids:
            raise ValidationError({'debut': 'La date corrigée ne peut pas traverser une autre déclaration. Ajoutez le fait oublié à sa date.'})
    for x in sorted(serie, key=lambda x: x.fin is None):
        x.full_clean()
        x.save()
    RevisionDeclarationFamiliale.objects.create(personne=personne, declaration=fait, action=action,
        avant=avant, apres=photographie(personne), motif=motif.strip(), auteur=acteur)
    return fait


def a_date(personnes, date):
    return DeclarationFamiliale.objects.filter(personne__in=personnes, debut__lte=date).filter(
        Q(fin__isnull=True) | Q(fin__gt=date))
