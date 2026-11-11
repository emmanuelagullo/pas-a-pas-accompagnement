"""Restitution nominative des faits déclarés, à l’entrée et à la sortie."""
from calendar import monthrange
from collections import defaultdict
from django.db.models import Q
from django.utils import timezone

from acteurs.portees import existante
from . import collectifs, complements_identite, dossier_complet, interventions, models as m, relations_personnelles

DROITS = (
    *interventions.DROITS_LECTURE,
    'personnes.view_informationsaccompagnement',
    'personnes.view_compositioncollective',
    'personnes.view_accordhebergement', 'personnes.view_sejour',
    'personnes.view_affectation', 'personnes.view_lieuhebergement',
    'personnes.view_situationsociale',
    *complements_identite.DROITS_LECTURE,
    *relations_personnelles.DROITS_LECTURE,
    *dossier_complet.droits_lecture('ressources'),
    *dossier_complet.droits_lecture('couvertures'),
    'personnes.view_situationadministrative', 'personnes.view_revisionsituationadministrative',
)


def disponible(acteur, prise):
    if not prise or not acteur.has_perms(DROITS):
        return False
    portee = existante(prise)
    return bool(portee and portee.service.profil_collectif.get('fiche_ahi'))


def par_personne(faits):
    resultat = defaultdict(list)
    for fait in faits:
        resultat[fait.personne_id].append(fait)
    return resultat


def tranche_duree(entree, sortie):
    if (sortie - entree).days < 15:
        return 'Moins de 15 jours'
    annee, mois = divmod(entree.month - 1 + 6, 12)
    annee += entree.year
    mois += 1
    borne = entree.replace(year=annee, month=mois, day=min(entree.day, monthrange(annee, mois)[1]))
    return 'De 15 jours à 6 mois' if sortie <= borne else 'Plus de 6 mois'


def preparer(acteur, prise):
    jour = prise.debut
    composition = collectifs.composition(prise, jour)
    personnes = list(prise.beneficiaires.all())
    if composition:
        identifies = set(composition.identifies.values_list('pk', flat=True))
        personnes = [personne for personne in personnes if personne.pk in identifies]
    reference = next((p for p in personnes if composition and p.pk == composition.reference_id), None)
    conjoints = []
    if reference:
        for lien in relations_personnelles.a_date(reference, jour).filter(nature='couple'):
            autre = lien.autre(reference)
            if autre in personnes:
                conjoints.append(autre)
    sejours = m.Sejour.objects.non_annules().filter(accord__accompagnement=prise, accord__annule_le__isnull=True)
    sejours_entree = sejours.filter(debut__lte=jour).filter(Q(fin__isnull=True) | Q(fin__gt=jour))
    loges = set(sejours_entree.values_list('beneficiaires', flat=True))
    lieux = m.LieuHebergement.objects.filter(
        pk__in=m.Affectation.objects.filter(sejour__in=sejours_entree, debut__lte=jour)
        .filter(Q(fin__isnull=True) | Q(fin__gt=jour)).values('lieu_id')
    ).order_by('libelle')
    complements = {x.personne_id: x for x in complements_identite.a_date(personnes, jour)}
    administration = {x.personne_id: x for x in dossier_complet.administration_a_date(personnes, jour)}
    ressources = par_personne(dossier_complet.a_date('ressources', personnes, jour))
    situations = prise.situations_sociales.filter(debut__lte=jour).filter(Q(fin__isnull=True) | Q(fin__gt=jour))
    emplois = {x.beneficiaire_id: x.libelle_valeur for x in situations.filter(dimension='emploi')}
    adultes, enfants, ages_inconnus = [], [], []
    for p in personnes:
        age = collectifs.age_exact(p.date_naissance, jour) if p.date_naissance and p.precision_naissance == 'exacte' else None
        complement = complements.get(p.pk)
        if age is None:
            ages_inconnus.append(p)
        elif age < 18 and p.pk in loges:
            enfants.append({'personne': p, 'age': age, 'sexe': complement.sexe_declare if complement else ''})
        elif age >= 18:
            faits = ressources[p.pk]
            details = [x for x in faits if x.etat == 'detail']
            comparables = details and len(details) == len(faits) and all(
                x.montant is not None and x.periodicite == 'mensuelle' and x.devise == 'EUR' for x in details
            )
            adultes.append({'personne': p, 'nationalites': complement.nationalites if complement else [],
                            'administration': administration.get(p.pk), 'emploi': emplois.get(p.pk),
                            'ressources': faits, 'total': sum(x.montant for x in details) if comparables else None})
    couvertures = dossier_complet.a_date('couvertures', [reference], jour) if reference else []
    sortie = prise.fin if prise.fin and prise.fin <= timezone.localdate() else None
    return {
        'reference': reference, 'conjoints': conjoints, 'enfants': enfants, 'adultes': adultes,
        'ages_inconnus': ages_inconnus, 'couvertures': couvertures,
        'ressources_jusqua_800': sum(x['total'] is not None and x['total'] <= 800 for x in adultes),
        'ressources_plus_de_800': sum(x['total'] is not None and x['total'] > 800 for x in adultes),
        'missions': interventions.presentation(acteur, prise, jour), 'lieux': lieux,
        'telephone': composition.telephone if composition else '',
        'courriel': composition.courriel if composition else '',
        'informations': prise.informations.first(),
        'sortie': sortie, 'duree': (sortie - jour).days if sortie else None,
        'tranche_duree': tranche_duree(jour, sortie) if sortie else '',
    }
