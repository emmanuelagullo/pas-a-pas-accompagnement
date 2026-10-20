"""Indicateurs CHRS10 : périodes civiles semi-ouvertes, sans présumer de présence.

Une nuitée est ici une *nuitée de séjour théorique* par bénéficiaire,
non une présence physique constatée. Les absences ne sont pas déduites.
"""
from datetime import timedelta
from django.db.models import Q, Sum
from .models import Accompagnement, Sejour, RepasDistribue, Absence, AccordRepas


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
    nuits_uniques, nuits_hors_absence = nuits_distinctes(debut, fin)
    distributions = RepasDistribue.objects.filter(date__gte=debut, date__lt=fin, annule_le__isnull=True)
    return {
        'menages_accompagnes': menages,
        'accompagnements': accompagnements.count(),
        'personnes_avec_sejour': personnes,
        'sejours': sejours.count(),
        'admissions': admissions,
        'sorties': sorties,
        'nuitees_theoriques': nuitees,
        'nuits_distinctes': nuits_uniques,
        'nuits_hors_absences_declarees': nuits_hors_absence,
        'repas_distribues': distributions.aggregate(total=Sum('quantite'))['total'] or 0,
    }


def nuits_distinctes(debut, fin):
    """Nuits par personne sans doublon de séjours, et hors absences déclarées.

    Ces résultats ne prouvent PAS une présence physique : une absence non saisie
    n'est pas déductible. Une nuit correspond à la date civile de son début.
    """
    if fin <= debut:
        raise ValueError("La fin doit être postérieure au début")
    nuits = set()
    hors_absence = set()
    sejours = (Sejour.objects.filter(chevauche(debut, fin))
               .prefetch_related('beneficiaires', 'absences'))
    for sejour in sejours:
        personnes = [p.pk for p in sejour.beneficiaires.all()]
        debut_effectif = max(debut, sejour.debut)
        fin_effective = min(fin, sejour.fin or fin)
        absences = [(max(a.debut, debut_effectif), min(a.fin or fin_effective, fin_effective))
                    for a in sejour.absences.all()]
        jour = debut_effectif
        while jour < fin_effective:
            for identifiant in personnes:
                cle = (identifiant, jour)
                nuits.add(cle)
                if not any(a <= jour < b for a, b in absences):
                    hors_absence.add(cle)
            jour += timedelta(days=1)
    return len(nuits), len(hors_absence)


def ventilation_repas(debut, fin):
    """Quantités effectivement distribuées, par service, hors annulations."""
    if fin <= debut:
        raise ValueError("La fin doit être postérieure au début")
    resultats = {service: 0 for service, _ in AccordRepas.SERVICES}
    lignes = (RepasDistribue.objects.filter(date__gte=debut, date__lt=fin,
                                             annule_le__isnull=True)
              .values('accord__service').annotate(total=Sum('quantite')))
    for ligne in lignes:
        resultats[ligne['accord__service']] = ligne['total']
    return resultats


def evolution_mensuelle(debut, fin, *, maximum_mois=24):
    """Découpe [debut, fin[ en mois civils, sans sommer les populations distinctes."""
    if fin <= debut:
        raise ValueError("La fin doit être postérieure au début")
    # Le mois contenant la borne exclusive ne compte que si une nuit/jour
    # de ce mois est effectivement inclus dans la période.
    dernier_jour = fin - timedelta(days=1)
    mois = (dernier_jour.year - debut.year) * 12 + dernier_jour.month - debut.month + 1
    if mois > maximum_mois:
        raise ValueError("Période trop longue pour la ventilation mensuelle (24 mois maximum)")
    lignes = []
    courant = debut
    while courant < fin:
        annee, mois_num = courant.year, courant.month
        suivant = courant.replace(year=annee + (mois_num == 12),
                                   month=1 if mois_num == 12 else mois_num + 1, day=1)
        borne = min(suivant, fin)
        chiffres = bilan(courant, borne)
        lignes.append({'mois': courant.strftime('%Y-%m'), 'debut': courant,
                       'fin': borne, **chiffres})
        courant = borne
    return lignes
