"""Départs effectifs visibles, indépendants de la clôture de la prise en charge."""
from collections import defaultdict
from django.db.models import OuterRef, Subquery

from . import models as m


def par_prise(acteur, prises, au):
    resultats = defaultdict(list)
    if acteur.has_perms(('personnes.view_accordhebergement', 'personnes.view_sejour')):
        sejours = m.Sejour.objects.non_annules().filter(
            accord__accompagnement_id__in=prises, fin__lte=au, individualisation__isnull=True,
        ).values_list('accord__accompagnement_id', 'fin', 'destination_sortie')
        for prise, date, destination in sejours:
            resultats[prise].append((date, destination))
    if acteur.has_perms(('personnes.view_prestationcollective', 'personnes.view_versionprestationcollective')):
        courante = m.VersionPrestationCollective.objects.filter(
            prestation_id=OuterRef('prestation_id'),
        ).order_by('-numero').values('pk')[:1]
        versions = m.VersionPrestationCollective.objects.filter(
            pk=Subquery(courante), prestation__accompagnement_id__in=prises,
            prestation__nature='hebergement', arrivee__isnull=False, fin__lte=au,
        ).exclude(action='annulation').values_list('prestation__accompagnement_id', 'fin', 'destination_sortie')
        for prise, date, destination in versions:
            resultats[prise].append((date, destination))
    return {prise: sorted(departs) for prise, departs in resultats.items()}
