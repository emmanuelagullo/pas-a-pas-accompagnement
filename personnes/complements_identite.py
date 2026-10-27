from acteurs.contexte import service_metier
"""Renseignements d'identité déclarés, datés, facultatifs et corrigibles."""
from django.db.models import Q
from . import suivi, series_personnelles
from .models import ComplementIdentite,RevisionComplementIdentite

CHAMPS=('sexe_declare','naissance_lieu','naissance_ville','naissance_pays','nationalites','apatridie_declaree')
DROITS_LECTURE=('personnes.view_personne','personnes.view_complementidentite','personnes.view_revisioncomplementidentite')


@service_metier
def renseigner(acteur,personne,debut,source,attendu,motif='',correction=None,**valeurs):
    suivi.exiger(acteur,'view_personne','view_complementidentite','view_revisioncomplementidentite','add_complementidentite')
    # La collection est typée et conservée comme telle, jamais une chaîne CSV.
    if isinstance(valeurs.get('nationalites'),list):
        valeurs['nationalites']=[v.strip() if isinstance(v,str) else v for v in valeurs['nationalites']]
    return series_personnelles.enregistrer(acteur,personne,debut,source,attendu,motif,correction,valeurs,
        modele=ComplementIdentite,journal=RevisionComplementIdentite,champs=CHAMPS,lien='complement')


def a_date(personnes,jour):
    return ComplementIdentite.objects.filter(personne__in=personnes,debut__lte=jour).filter(Q(fin__isnull=True)|Q(fin__gt=jour))
