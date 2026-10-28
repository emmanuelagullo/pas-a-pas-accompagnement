from acteurs.contexte import service_metier
"""Ouverture explicite depuis un dossier, atomique et sans rejeu de confirmation."""
from uuid import uuid4, UUID

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F

from . import suivi
from .models import Personne, Menage, Appartenance

SEL = 'solenne-ouverture-prise-v1'


def menages_personne(personne):
    return Menage.objects.filter(appartenances__personne=personne).distinct()


def jeton(objet):
    menages = menages_personne(objet) if isinstance(objet, Personne) else Menage.objects.filter(pk=objet.pk)
    return signing.dumps({'nature': objet._meta.model_name, 'cible': str(objet.pk),
        'menages': {str(m.pk): m.revision for m in menages},
        'prise': str(uuid4()), 'nouveau_menage': str(uuid4())}, salt=SEL)


@service_metier
def ouvrir(acteur, objet, beneficiaires, debut, fin_prevue, attendu, menage=None,
           creer_menage=False, libelle_menage='', demande=None, attendu_demande=None):
    suivi.exiger(acteur, 'view_personne', 'view_menage', 'view_accompagnement', 'add_accompagnement')
    if demande is not None:
        from . import parcours
        parcours.exiger(acteur,'demandes','change')
        if demande.cible.pk != objet.pk or demande.cible._meta.model_name != objet._meta.model_name:
            raise ValidationError('Cette demande ne concerne pas le dossier choisi.')
    try:
        etat = signing.loads(attendu, salt=SEL, max_age=86400)
        if etat['nature'] != objet._meta.model_name or etat['cible'] != str(objet.pk):
            raise ValueError
        identifiant, nouveau = UUID(etat['prise']), UUID(etat['nouveau_menage'])
        revisions = etat['menages']
    except (signing.BadSignature, ValueError, TypeError, KeyError):
        raise ValidationError('Formulaire non vérifiable pour ce dossier. Rechargez avant de confirmer.')
    personnes = list(beneficiaires)
    if isinstance(objet, Personne) and {p.pk for p in personnes} != {objet.pk}:
        raise ValidationError({'beneficiaires': 'Cette ouverture individuelle concerne uniquement la personne du dossier.'})
    if creer_menage:
        suivi.exiger(acteur, 'add_menage', 'add_appartenance')
        if not isinstance(objet, Personne) or menage is not None:
            raise ValidationError('Choisissez un seul rattachement explicite.')
        if not libelle_menage.strip():
            raise ValidationError({'libelle_menage': 'Nommez le ménage dont vous confirmez la création.'})
    elif menage is None:
        raise ValidationError({'menage': 'Choisissez un ménage existant ou confirmez la création.'})
    # Identifiants réservés par le formulaire signé : la contrainte PK assure
    # aussi le non-rejeu concurrent, sans verrou personne puis ménage.
    try:
        with transaction.atomic():
            if creer_menage:
                menage = suivi.creer_menage(acteur, libelle_menage, personnes, debut, identifiant=nouveau)
            else:
                precedente = revisions.get(str(menage.pk))
                from acteurs import reperage
                reserve=reperage.reserver_menage(acteur,objet,menage,precedente)
                if precedente is None or (not reserve and Menage.objects.filter(pk=menage.pk, revision=precedente).update(revision=F('revision') + 1) != 1):
                    raise ValidationError('Le ménage a changé. Rechargez avant de confirmer.')
                menage = Menage.objects.get(pk=menage.pk)
                if isinstance(objet, Menage) and menage.pk != objet.pk:
                    raise ValidationError('Le ménage ne correspond pas au dossier.')
                # Même périmètre explicite que le formulaire BD existant. Une
                # appartenance passée n'est pas prolongée par cette ouverture.
                ids = reperage.membres(acteur,menage) if reserve else set(Appartenance.objects.filter(menage=menage).values_list('personne_id', flat=True))
                if not personnes or not {p.pk for p in personnes}.issubset(ids):
                    raise ValidationError({'beneficiaires': 'Le rattachement des bénéficiaires a changé. Rechargez le dossier.'})
            a = suivi.ouvrir(acteur, menage, personnes, debut, fin_prevue, identifiant=identifiant)
            if demande is not None:
                parcours.lier(acteur,demande,a,attendu_demande,'Ouverture explicitement confirmée depuis la demande acceptée')
            return a
    except IntegrityError as erreur:
        raise ValidationError('Cette confirmation a déjà été utilisée. Rechargez le dossier.') from erreur
