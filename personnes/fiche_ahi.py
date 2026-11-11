"""Restitution nominative des faits déclarés, à l’entrée et à la sortie."""
from calendar import monthrange
from collections import Counter, defaultdict
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.utils import timezone

from acteurs.portees import existante
from . import collectifs, complements_identite, dossier_complet, interventions, models as m, relations_personnelles
from . import nomenclature_ahi as n

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


def choix_valides(valeurs):
    for cle, valeur in valeurs.items():
        if cle in n.ADULTE:
            if not isinstance(valeur, str) or valeur not in n.ADULTE[cle][1]:
                return False
        elif cle in n.CHOIX_MULTIPLES:
            choix = n.CHOIX_MULTIPLES[cle][1]
            if not isinstance(valeur, list) or any(not isinstance(code, str) or code not in choix for code in valeur):
                return False
            if len(set(valeur)) != len(valeur):
                return False
        else:
            return False
    return True


def valider_releve(acteur, prise, releve):
    if not disponible(acteur, prise):
        raise PermissionDenied
    if not isinstance(releve, dict) or set(releve) - {*n.MENAGE, 'adultes', 'adresse_logement', 'adresse_sortie', 'qualifications', 'reference'}:
        raise ValidationError('Relevé AHI invalide.')
    contexte = preparer(acteur, prise)
    adultes = releve.get('adultes', {})
    identifiants = {str(ligne['personne'].pk) for ligne in contexte['adultes']}
    if not isinstance(adultes, dict) or set(adultes) - identifiants:
        raise ValidationError('Le relevé doit concerner les adultes identifiés à l’entrée.')
    for valeurs in adultes.values():
        if not isinstance(valeurs, dict) or not choix_valides(valeurs):
            raise ValidationError('Catégorie AHI inconnue.')
    for cle, valeur in releve.items():
        if cle in n.MENAGE and (not isinstance(valeur, str) or valeur not in n.MENAGE[cle][1]):
            raise ValidationError('Catégorie AHI inconnue.')
    if {'droits', 'couverture'} & releve.keys():
        reference = contexte['reference']
        if not reference or releve.get('reference') != str(reference.pk):
            raise ValidationError('La personne de référence a changé. Rouvrez le relevé AHI.')
    if not contexte['sortie'] and {'sortie', 'adresse_sortie', 'qualifications'} & releve.keys():
        raise ValidationError('Renseignez d’abord la sortie effective.')
    for cle in ('adresse_logement', 'adresse_sortie'):
        adresse = releve.get(cle, '')
        if not isinstance(adresse, str) or len(adresse) > 500:
            raise ValidationError('Adresse AHI invalide.')
    qualifications = releve.get('qualifications', [])
    if not isinstance(qualifications, list) or any(
        not isinstance(code, str) or code not in n.QUALIFICATIONS_SORTIE for code in qualifications
    ):
        raise ValidationError('Précisions de sortie AHI invalides.')


def compter(adultes, releve):
    groupes = []
    for cle, (titre, choix) in n.ADULTE.items():
        comptes = Counter(releve.get('adultes', {}).get(str(ligne['personne'].pk), {}).get(cle) for ligne in adultes)
        lignes = [(libelle, comptes[code]) for code, libelle in choix.items() if comptes[code]]
        if cle == 'logement':
            lignes.extend((libelle, sum(comptes[code] for code in codes)) for libelle, codes in n.GROUPES_LOGEMENT.items())
        elif cle == 'administration':
            lignes.extend((
                ('Total UE hors France', comptes['ue_droits'] + comptes['ue_sans_droits']),
                ('Total hors UE', sum(comptes[code] for code in choix if code not in {'france', 'ue_droits', 'ue_sans_droits'})),
            ))
        groupes.append((titre, lignes + [('Non renseigné', comptes[None])]))
    for cle, (titre, choix) in n.CHOIX_MULTIPLES.items():
        comptes = Counter(
            code for ligne in adultes
            for code in releve.get('adultes', {}).get(str(ligne['personne'].pk), {}).get(cle, [])
        )
        groupes.append((titre, [(libelle, comptes[code]) for code, libelle in choix.items() if comptes[code]]))
    return groupes


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
    informations = prise.informations.first()
    releve = informations.releve_ahi if informations else {}
    meme_reference = reference and releve.get('reference') == str(reference.pk)
    return {
        'releve': releve, 'comptes_ahi': compter(adultes, releve),
        'droits_ahi': n.DROITS_SOCIAUX.get(releve.get('droits')) if meme_reference else None,
        'couverture_ahi': n.COUVERTURE.get(releve.get('couverture')) if meme_reference else None,
        'sortie_ahi': n.SORTIES.get(releve.get('sortie')),
        'groupe_sortie_ahi': next((groupe for groupe, codes in n.GROUPES_SORTIES.items() if releve.get('sortie') in codes), ''),
        'sans_ressources': sum(bool(x['ressources']) and all(f.etat == 'aucun' for f in x['ressources']) for x in adultes),
        'avec_ressources': sum(any(f.etat == 'detail' for f in x['ressources']) for x in adultes),
        'qualifications_ahi': [n.QUALIFICATIONS_SORTIE[code] for code in releve.get('qualifications', [])],
        'reference': reference, 'conjoints': conjoints, 'enfants': enfants, 'adultes': adultes,
        'ages_inconnus': ages_inconnus, 'couvertures': couvertures,
        'ressources_jusqua_800': sum(x['total'] is not None and x['total'] <= 800 for x in adultes),
        'ressources_plus_de_800': sum(x['total'] is not None and x['total'] > 800 for x in adultes),
        'missions': interventions.presentation(acteur, prise, jour), 'lieux': lieux,
        'telephone': composition.telephone if composition else '',
        'courriel': composition.courriel if composition else '',
        'informations': informations,
        'sortie': sortie, 'duree': (sortie - jour).days if sortie else None,
        'tranche_duree': tranche_duree(jour, sortie) if sortie else '',
    }
