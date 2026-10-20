"""Indicateurs CHRS10 : périodes civiles semi-ouvertes, sans présumer de présence.

Une nuitée est ici une *nuitée de séjour théorique* par bénéficiaire,
non une présence physique constatée. Les absences ne sont pas déduites.
"""
from datetime import timedelta
from django.db.models import Q, Sum
from .models import Accompagnement, Sejour, RepasDistribue


def chevauche(debut, fin):
    return Q(debut__lt=fin) & (Q(fin__isnull=True) | Q(fin__gt=debut))


def bilan(debut, fin):
    """Retourne des entiers agrégés pour [debut, fin[ ; fin doit être > debut."""
    if fin <= debut:
        raise ValueError("La fin doit être postérieure au début")
    accompagnements = Accompagnement.objects.filter(chevauche(debut, fin))
    sejours = Sejour.objects.filter(chevauche(debut, fin))
    # Les M2M peuvent produire des doublons : DISTINCT porte sur les identités.
    personnes = sejours.values_list('beneficiaires__pk', flat=True).exclude(beneficiaires__isnull=True).distinct().count()
    menages = accompagnements.values_list('menage_id', flat=True).distinct().count()
    admissions = Sejour.objects.filter(debut__gte=debut, debut__lt=fin).count()
    sorties = Sejour.objects.filter(fin__gte=debut, fin__lt=fin, fin__isnull=False).count()
    # Chaque séjour contribue séparément. Les séjours concomitants sont
    # comptés deux fois : ce n'est PAS un indicateur de nuits uniques/personne.
    nuitees = 0
    for sejour in sejours.prefetch_related('beneficiaires').only('debut', 'fin'):
        jours = (min(sejour.fin or fin, fin) - max(sejour.debut, debut)).days
        nuitees += jours * sejour.beneficiaires.count()
    distributions = RepasDistribue.objects.filter(date__gte=debut, date__lt=fin, annule_le__isnull=True)
    return {
        'menages_accompagnes': menages,
        'accompagnements': accompagnements.count(),
        'personnes_avec_sejour': personnes,
        'sejours': sejours.count(),
        'admissions': admissions,
        'sorties': sorties,
        'nuitees_theoriques': nuitees,
        'repas_distribues': distributions.aggregate(total=Sum('quantite'))['total'] or 0,
    }
