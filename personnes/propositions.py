"""Listes volontaires de propositions ; jamais un collecteur de saisies de dossiers."""
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import F
from . import suivi
from .models import PropositionSaisie, RevisionPropositionSaisie


def jeton(objet):
    return signing.dumps([objet.pk, objet.revision], salt='proposition-saisie-v1')


def photo(x):
    return {'champ':x.champ, 'valeur':x.valeur, 'active':x.active}


def enregistrer(acteur, champ, valeur, active, motif, *, objet=None, attendu=None):
    suivi.exiger(acteur, 'view_propositionsaisie', 'view_revisionpropositionsaisie',
        'change_propositionsaisie' if objet else 'add_propositionsaisie')
    try:
        return _enregistrer(acteur, champ, valeur, active, motif, objet=objet, attendu=attendu)
    except IntegrityError as erreur:
        raise ValidationError('Cette proposition existe déjà ou sa confirmation n’a pas abouti. Rechargez la liste.') from erreur


@transaction.atomic
def _enregistrer(acteur, champ, valeur, active, motif, *, objet, attendu):
    if not motif.strip() or len(motif)>240:
        raise ValidationError({'motif':'Expliquez cette modification (240 caractères maximum).'})
    avant = {}
    if objet:
        try: etat = signing.loads(attendu, salt='proposition-saisie-v1', max_age=86400)
        except (signing.BadSignature, TypeError): raise ValidationError('État non vérifiable ; rechargez la liste.')
        if not isinstance(etat,list) or len(etat)!=2 or etat[0]!=objet.pk or PropositionSaisie.objects.filter(pk=objet.pk, revision=etat[1]).update(revision=F('revision')+1)!=1:
            raise ValidationError('Cette proposition a changé ; rechargez la liste.')
        objet.refresh_from_db(); avant=photo(objet)
    else:
        objet=PropositionSaisie()
    objet.champ, objet.valeur, objet.active = champ, valeur.strip(), active
    if objet.champ=='code_postal' and len(objet.valeur)>20:
        raise ValidationError({'valeur':'Un code postal comporte au maximum 20 caractères.'})
    objet.full_clean(validate_unique=objet.pk is not None, validate_constraints=objet.pk is not None)
    if photo(objet)==avant:raise ValidationError('Aucune modification.')
    objet.save()
    RevisionPropositionSaisie.objects.create(proposition=objet,avant=avant,apres=photo(objet),motif=motif.strip(),auteur=acteur)
    return objet
