from acteurs.contexte import service_metier
"""Correction atomique d’une identité, indépendante des liens de ménage."""
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from .models import Personne, RevisionIdentite
from .suivi import exiger

CHAMPS = ('designation', 'prenom', 'date_naissance', 'annee_naissance', 'precision_naissance')


def jeton(personne):
    return signing.dumps([str(personne.pk), personne.revision_identite,
        [str(getattr(personne, champ)) for champ in CHAMPS]], salt='chrs25-identite')


@service_metier
def corriger(acteur, personne, motif, attendu, **donnees):
    exiger(acteur, 'view_personne', 'change_personne', 'view_revisionidentite')
    return _corriger(acteur, personne.pk, motif, attendu, donnees)


@service_metier
@transaction.atomic
def _corriger(acteur, pk, motif, attendu, donnees):
    try:
        etat = signing.loads(attendu, salt='chrs25-identite', max_age=86400)
    except signing.BadSignature as exc:
        raise ValidationError('Le formulaire a expiré. Rechargez la fiche.') from exc
    if etat[0] != str(pk):
        raise ValidationError('Le formulaire ne correspond pas à cette personne.')
    # Première requête SQL de la transaction : réservation conditionnelle de
    # la révision sur SQLite et PostgreSQL. Toute erreur annule cette écriture.
    if Personne.objects.filter(pk=pk, revision_identite=etat[1]).update(revision_identite=F('revision_identite') + 1) != 1:
        raise ValidationError('Cette identité a changé. Rechargez la fiche avant de la corriger.')
    personne = Personne.objects.get(pk=pk)
    if etat != [str(personne.pk), personne.revision_identite - 1,
                [str(getattr(personne, champ)) for champ in CHAMPS]]:
        raise ValidationError('Cette identité a changé. Rechargez la fiche avant de la corriger.')
    motif = motif.strip()
    if len(motif) > 240:
        raise ValidationError({'motif': '240 caractères au plus.'})
    avant = {champ: getattr(personne, champ) for champ in CHAMPS}
    for champ in CHAMPS:
        setattr(personne, champ, donnees[champ])
    personne.full_clean()
    apres = {champ: getattr(personne, champ) for champ in CHAMPS}
    if avant == apres:
        raise ValidationError('Aucune modification.')
    Personne.objects.filter(pk=personne.pk).update(**apres)
    prefixes = {'designation': ('ancienne_designation', 'nouvelle_designation'),
        'prenom': ('ancien_prenom', 'nouveau_prenom'),
        'date_naissance': ('ancienne_date_naissance', 'nouvelle_date_naissance'),
        'annee_naissance': ('ancienne_annee_naissance', 'nouvelle_annee_naissance'),
        'precision_naissance': ('ancienne_precision_naissance', 'nouvelle_precision_naissance')}
    trace = {}
    for champ, (ancien, nouveau) in prefixes.items():
        trace[ancien], trace[nouveau] = avant[champ], apres[champ]
    RevisionIdentite.objects.create(personne=personne, auteur=acteur, motif=motif, **trace)
    personne.refresh_from_db()
    return personne
