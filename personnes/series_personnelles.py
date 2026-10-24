"""Chronologie commune à deux histoires personnelles typées, sans moteur de champs."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from . import bd6, suivi


def photographie(personne, modele, champs):
    return [{'id': x.pk, 'debut': x.debut.isoformat(), 'fin': x.fin.isoformat() if x.fin else None,
        **{champ: getattr(x, champ) for champ in champs}, 'source': x.source}
        for x in modele.objects.filter(personne=personne).order_by('debut', 'pk')]


@transaction.atomic
def enregistrer(acteur, personne, debut, source, attendu, motif, correction, valeurs, *, modele, journal, champs, lien):
    # Les droits sont chargés avant d'ouvrir la transaction : la réservation
    # personnelle est bien sa première requête SQL, même pour un compte neuf.
    bd6.reserver(personne, attendu)
    if set(valeurs) != set(champs):
        raise ValidationError('Cette information doit préciser toutes ses rubriques, y compris les valeurs inconnues.')
    if debut > timezone.localdate():
        raise ValidationError({'debut': 'Une information de situation ne peut pas être future.'})
    if not source.strip():
        raise ValidationError({'source': 'Indiquez la source de cette information.'})
    if len(motif) > 240:
        raise ValidationError({'motif': 'Le motif est limité à 240 caractères.'})
    avant = photographie(personne, modele, champs)
    serie = list(modele.objects.filter(personne=personne).order_by('debut', 'pk'))
    if correction is not None:
        suivi.exiger(acteur, 'change_' + modele._meta.model_name)
        fait = next((x for x in serie if x.pk == correction), None)
        if fait is None:
            raise ValidationError('Cette information ne correspond pas à cette personne.')
        action = 'correction'
        if fait.debut == debut and fait.source == source.strip() and all(getattr(fait, c) == valeurs[c] for c in champs):
            raise ValidationError('Aucune modification de cette information.')
    else:
        fait = modele(personne=personne, auteur=acteur)
        action = 'insertion' if any(x.debut > debut for x in serie) else 'changement'
        serie.append(fait)
    if action != 'changement':
        suivi.exiger(acteur, 'change_' + modele._meta.model_name)
        if not motif.strip():
            raise ValidationError({'motif': 'Expliquez la correction ou l’ajout d’un fait antérieur oublié.'})
    if any(x is not fait and x.debut == debut for x in serie):
        raise ValidationError({'debut': 'Une information existe déjà à cette date. Corrigez-la explicitement.'})
    fait.debut, fait.source = debut, source.strip()
    for champ in champs:
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
            raise ValidationError({'debut': 'La date corrigée ne peut pas traverser une autre information. Ajoutez le fait oublié à sa date.'})
    for x in sorted(serie, key=lambda x: x.fin is None):
        x.full_clean()
        x.save()
    journal.objects.create(personne=personne, **{lien: fait}, action=action,
        avant=avant, apres=photographie(personne, modele, champs), motif=motif.strip(), auteur=acteur)
    return fait
