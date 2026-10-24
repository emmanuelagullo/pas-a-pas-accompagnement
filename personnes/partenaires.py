"""Répertoire daté d'organismes, indépendant des personnes et comptes de l'équipe."""
from uuid import uuid4, UUID
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.utils import timezone
from . import bd6, suivi, series_personnelles
from .models import Partenaire, FichePartenaire, RevisionFichePartenaire

CHAMPS = ('nom', 'rue', 'code_postal', 'ville', 'pays', 'telephone', 'courriel', 'fax', 'informations')
DROITS_LECTURE = ('personnes.view_partenaire', 'personnes.view_fichepartenaire', 'personnes.view_revisionfichepartenaire')


def jeton_creation():
    return signing.dumps(str(uuid4()), salt='solenne-partenaire-creation-v1')


def droits(acteur):
    suivi.exiger(acteur, 'view_partenaire', 'view_fichepartenaire', 'view_revisionfichepartenaire', 'add_fichepartenaire')


def creer(acteur, debut, source, attendu, motif='', **valeurs):
    droits(acteur)
    suivi.exiger(acteur, 'add_partenaire')
    nom = valeurs.get('nom')
    if not isinstance(nom, str) or not nom.strip() or len(nom) > 160:
        raise ValidationError({'nom': 'Indiquez un nom de 1 à 160 caractères.'})
    try:
        pk = UUID(signing.loads(attendu, salt='solenne-partenaire-creation-v1', max_age=86400))
    except (signing.BadSignature, TypeError, ValueError):
        raise ValidationError('Confirmation de création non vérifiable. Rechargez le formulaire.')
    try:
        with transaction.atomic():
            # Premier SQL : INSERT de l'identité réservée ; le même formulaire
            # ne crée pas deux organismes et ne bloque aucune personne/ménage.
            objet = Partenaire.objects.create(pk=pk, libelle=valeurs.get('nom', ''), cree_par=acteur)
            renseigner(acteur, objet, debut, source, bd6.jeton(objet), motif=motif, **valeurs)
            return objet
    except IntegrityError as erreur:
        raise ValidationError('Cette confirmation a déjà été utilisée. Rechargez le répertoire.') from erreur


def renseigner(acteur, partenaire, debut, source, attendu, motif='', correction=None, **valeurs):
    droits(acteur)
    return _renseigner(acteur, partenaire, debut, source, attendu, motif, correction, valeurs)


@transaction.atomic
def _renseigner(acteur, partenaire, debut, source, attendu, motif, correction, valeurs):
    fiche = series_personnelles.enregistrer(acteur, partenaire, debut, source, attendu, motif, correction, valeurs,
        modele=FichePartenaire, journal=RevisionFichePartenaire, champs=CHAMPS, lien='fiche', champ_cible='partenaire')
    # Le libellé d'index suit la fiche applicable aujourd'hui. Les anciennes
    # fiches gardent leur nom et restent consultables à leur date d'effet.
    courante = a_date([partenaire], timezone.localdate()).get()
    Partenaire.objects.filter(pk=partenaire.pk).update(libelle=courante.nom)
    return fiche


def a_date(parties, date):
    return FichePartenaire.objects.filter(partenaire__in=parties, debut__lte=date).filter(
        Q(fin__isnull=True) | Q(fin__gt=date))
