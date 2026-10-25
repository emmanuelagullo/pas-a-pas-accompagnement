"""Coordonnées déclarées d'une personne ; ni lieu d'hébergement ni partenaire."""
from django.db.models import Q
from . import suivi, series_personnelles
from .models import CoordonneesPersonnelles, RevisionCoordonneesPersonnelles

CHAMPS = ('usage_adresse', 'rue', 'code_postal', 'ville', 'pays', 'telephone', 'courriel', 'fax')
DROITS_LECTURE = ('personnes.view_personne', 'personnes.view_coordonneespersonnelles',
    'personnes.view_revisioncoordonneespersonnelles')


def renseigner(acteur, personne, debut, source, attendu, motif='', correction=None, **valeurs):
    valeurs.setdefault('usage_adresse','')
    suivi.exiger(acteur, 'view_personne', 'view_coordonneespersonnelles',
        'view_revisioncoordonneespersonnelles', 'add_coordonneespersonnelles')
    return series_personnelles.enregistrer(acteur, personne, debut, source, attendu, motif, correction, valeurs,
        modele=CoordonneesPersonnelles, journal=RevisionCoordonneesPersonnelles, champs=CHAMPS, lien='coordonnees')


def a_date(personnes, date):
    return CoordonneesPersonnelles.objects.filter(personne__in=personnes, debut__lte=date).filter(
        Q(fin__isnull=True) | Q(fin__gt=date))
