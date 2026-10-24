"""Rapports descriptifs : populations et unités explicites, aucun état inféré."""
from collections import Counter
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from .models import Personne, Sejour
from .statistiques import chevauche


def mouvements(debut, fin):
    if fin <= debut:
        raise ValueError('La fin doit être postérieure au début.')
    from .continuite_hebergement import episodes
    logique=list(episodes())
    entrees=[s for s,f in logique if debut<=s.debut<fin]
    sorties=[(s,f) for s,f in logique if f is not None and debut<=f<fin]
    entrants=[p.pk for s in entrees for p in s.beneficiaires.all()]
    sortants=[p.pk for s,f in sorties for p in s.beneficiaires.all()]
    durees=[(f-s.debut).days for s,f in sorties]
    return {
        'admissions_sejours': len(entrees), 'sorties_sejours': len(sorties),
        'beneficiaires_admissions': len(entrants), 'beneficiaires_sorties': len(sortants),
        'personnes_admises_distinctes': len(set(entrants)), 'personnes_sorties_distinctes': len(set(sortants)),
        'nuits_sejours_clos_total': sum(durees),
        'nuits_sejours_clos_min': min(durees) if durees else None,
        'nuits_sejours_clos_max': max(durees) if durees else None,
        'nuits_sejours_clos_moyenne': (Decimal(sum(durees)) / len(durees)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP) if durees else None,
    }


LIBELLES_MOUVEMENTS = {
    'admissions_sejours': 'Admissions — nombre de séjours',
    'sorties_sejours': 'Sorties — nombre de séjours',
    'beneficiaires_admissions': 'Admissions — bénéficiaires comptés par séjour',
    'beneficiaires_sorties': 'Sorties — bénéficiaires comptés par séjour',
    'personnes_admises_distinctes': 'Personnes admises distinctes',
    'personnes_sorties_distinctes': 'Personnes sorties distinctes',
    'nuits_sejours_clos_total': 'Durées des séjours sortis — total des nuits civiles',
    'nuits_sejours_clos_min': 'Durées des séjours sortis — minimum',
    'nuits_sejours_clos_max': 'Durées des séjours sortis — maximum',
    'nuits_sejours_clos_moyenne': 'Durées des séjours sortis — moyenne',
}


def ages(debut, fin):
    """Personnes distinctes avec séjour chevauchant la période ; âge à fin-1."""
    if fin <= debut:
        raise ValueError('La fin doit être postérieure au début.')
    reference = fin - timedelta(days=1)
    population = Personne.objects.filter(pk__in=
        Sejour.objects.filter(chevauche(debut, fin)).values('beneficiaires__pk')).distinct()
    comptes = Counter()
    qualite = {code: 0 for code in ('inconnue', 'estimee', 'annee', 'annee_estimee', 'apres_reference')}
    for p in population.only('date_naissance', 'precision_naissance'):
        if p.precision_naissance != 'exacte' or not p.date_naissance:
            qualite[p.precision_naissance if p.precision_naissance in qualite else 'inconnue'] += 1
        elif p.date_naissance > reference:
            qualite['apres_reference'] += 1
        else:
            naissance = p.date_naissance
            age = reference.year - naissance.year - ((reference.month, reference.day) < (naissance.month, naissance.day))
            comptes[age] += 1
    return reference, comptes, qualite


LIBELLES_NAISSANCES = {'inconnue': 'Naissance non renseignée', 'estimee': 'Date estimée — âge non calculé',
    'annee': 'Année connue seule — âge non calculé', 'annee_estimee': 'Année estimée seule — âge non calculé',
    'apres_reference': 'Date exacte postérieure à la référence — âge non calculé'}
