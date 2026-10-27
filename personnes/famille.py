from acteurs.contexte import service_metier
"""Histoire familiale typée et corrections de valeurs/dates sous réservation personnelle."""
from django.db.models import Q

from . import suivi, series_personnelles
from .models import DeclarationFamiliale, RevisionDeclarationFamiliale

CHAMPS = ('situation_familiale', 'rapports_parentaux', 'fratrie',
    'enfants_a_charge', 'enfants_non_a_charge', 'grossesse')
DROITS_LECTURE = ('personnes.view_personne', 'personnes.view_declarationfamiliale',
    'personnes.view_revisiondeclarationfamiliale')


def photographie(personne):
    return series_personnelles.photographie(personne, DeclarationFamiliale, CHAMPS)


@service_metier
def renseigner(acteur, personne, debut, source, attendu, motif='', correction=None, **valeurs):
    suivi.exiger(acteur, 'view_personne', 'view_declarationfamiliale', 'view_revisiondeclarationfamiliale', 'add_declarationfamiliale')
    return series_personnelles.enregistrer(acteur, personne, debut, source, attendu, motif, correction, valeurs,
        modele=DeclarationFamiliale, journal=RevisionDeclarationFamiliale, champs=CHAMPS, lien='declaration')


def a_date(personnes, date):
    return DeclarationFamiliale.objects.filter(personne__in=personnes, debut__lte=date).filter(
        Q(fin__isnull=True) | Q(fin__gt=date))
