from acteurs.contexte import service_metier
"""Répertoire daté de professionnels, indépendant des personnes et comptes de l'équipe."""
from uuid import uuid4, UUID
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.utils import timezone
from . import bd6, suivi, series_personnelles
from .models import Intervenant, FicheIntervenant, RevisionFicheIntervenant

CHAMPS = ('nom', 'fonction', 'organisme', 'telephone', 'courriel', 'fax')
DROITS_LECTURE = ('personnes.view_partenaire', 'personnes.view_intervenant', 'personnes.view_ficheintervenant', 'personnes.view_revisionficheintervenant')


def jeton_creation():
    return signing.dumps(str(uuid4()), salt='solenne-intervenant-creation-v1')


@service_metier
def droits(acteur):
    suivi.exiger(acteur, 'view_intervenant', 'view_ficheintervenant', 'view_revisionficheintervenant', 'add_ficheintervenant')


@service_metier
def creer(acteur, debut, source, attendu, motif='', **valeurs):
    droits(acteur)
    suivi.exiger(acteur, 'add_intervenant')
    nom = valeurs.get('nom')
    if not isinstance(nom, str) or not nom.strip() or len(nom) > 160:
        raise ValidationError({'nom': 'Indiquez un nom de 1 à 160 caractères.'})
    try:
        pk = UUID(signing.loads(attendu, salt='solenne-intervenant-creation-v1', max_age=86400))
    except (signing.BadSignature, TypeError, ValueError):
        raise ValidationError('Confirmation de création non vérifiable. Rechargez le formulaire.')
    try:
        with transaction.atomic():
            # Premier SQL : INSERT de l'identité réservée ; le même formulaire
            # ne crée pas deux professionnels et ne bloque aucune personne/ménage.
            objet = Intervenant.objects.create(pk=pk, libelle=valeurs.get('nom', ''), cree_par=acteur)
            renseigner(acteur, objet, debut, source, bd6.jeton(objet), motif=motif, **valeurs)
            return objet
    except IntegrityError as erreur:
        raise ValidationError('Cette confirmation a déjà été utilisée. Rechargez le répertoire.') from erreur


@service_metier
def renseigner(acteur, intervenant, debut, source, attendu, motif='', correction=None, **valeurs):
    droits(acteur)
    if valeurs.get('organisme') is not None:
        suivi.exiger(acteur, 'view_partenaire')
    return _renseigner(acteur, intervenant, debut, source, attendu, motif, correction, valeurs)


@service_metier
@transaction.atomic
def _renseigner(acteur, intervenant, debut, source, attendu, motif, correction, valeurs):
    fiche = series_personnelles.enregistrer(acteur, intervenant, debut, source, attendu, motif, correction, valeurs,
        modele=FicheIntervenant, journal=RevisionFicheIntervenant, champs=CHAMPS, lien='fiche', champ_cible='intervenant')
    # Le libellé d'index suit la fiche applicable aujourd'hui. Les anciennes
    # fiches gardent leur nom et restent consultables à leur date d'effet.
    courante = a_date([intervenant], timezone.localdate()).get()
    Intervenant.objects.filter(pk=intervenant.pk).update(libelle=courante.nom)
    return fiche


def a_date(parties, date):
    return FicheIntervenant.objects.filter(intervenant__in=parties, debut__lte=date).filter(
        Q(fin__isnull=True) | Q(fin__gt=date))
