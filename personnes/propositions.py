from acteurs.contexte import service_metier
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


@service_metier
def enregistrer(acteur, champ, valeur, active, motif, *, objet=None, attendu=None):
    suivi.exiger(acteur, 'view_propositionsaisie', 'view_revisionpropositionsaisie',
        'change_propositionsaisie' if objet else 'add_propositionsaisie')
    try:
        return _enregistrer(acteur, champ, valeur, active, motif, objet=objet, attendu=attendu)
    except IntegrityError as erreur:
        raise ValidationError('Cette proposition existe déjà ou sa confirmation n’a pas abouti. Rechargez la liste.') from erreur


@service_metier
@transaction.atomic
def _enregistrer(acteur, champ, valeur, active, motif, *, objet, attendu):
    if len(motif)>240 or objet is None and not motif.strip():
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


@service_metier
@transaction.atomic
def importer(acteur,contenu,motif):
    """Ajouts explicites en bloc ; aucune proposition existante n'est réécrite."""
    import json
    suivi.exiger(acteur,'view_propositionsaisie','view_revisionpropositionsaisie','add_propositionsaisie')
    if len(contenu)>1048576:raise ValidationError('Le fichier de propositions dépasse 1 Mio.')
    try:d=json.loads(contenu)
    except (ValueError,UnicodeError):raise ValidationError('Choisissez un fichier JSON de propositions de saisie.')
    if not isinstance(d,dict) or d.get('schema')!=1 or d.get('application')!='pas-a-pas-accompagnement' or d.get('type')!='propositions-saisie':raise ValidationError('Format, application ou version de propositions non pris en charge.')
    lignes=d.get('propositions')
    if not isinstance(lignes,list) or len(lignes)>1000:raise ValidationError('Au plus 1 000 propositions par fichier.')
    nouveaux=existants=0
    for ligne in lignes:
        if not isinstance(ligne,dict) or set(ligne)!={'champ','valeur','active'} or not isinstance(ligne['champ'],str) or not isinstance(ligne['valeur'],str) or type(ligne['active']) is not bool:raise ValidationError('Une proposition doit contenir champ, valeur textuelle et active booléen, sans identifiant importé.')
        champ,valeur,active=ligne['champ'],ligne['valeur'].strip(),ligne['active']
        if PropositionSaisie.objects.filter(champ=champ,valeur=valeur).exists():existants+=1;continue
        enregistrer(acteur,champ,valeur,active,motif);nouveaux+=1
    return nouveaux,existants


@service_metier
def exporter(acteur):
    import json
    suivi.exiger(acteur,'view_propositionsaisie','view_revisionpropositionsaisie')
    return json.dumps(dict(schema=1,application='pas-a-pas-accompagnement',type='propositions-saisie',propositions=[photo(x) for x in PropositionSaisie.objects.all()]),ensure_ascii=False,indent=2).encode()
