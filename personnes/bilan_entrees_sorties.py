"""Indicateurs calculés à partir des déclarations applicables à l'entrée."""
from calendar import monthrange
from collections import Counter
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import CharField
from django.db.models.functions import Cast

from acteurs.models import PorteeObjet
from acteurs.portees import existante

from . import collectifs, dossier_complet, models as m


DROITS = (
    'personnes.view_compositioncollective',
    'personnes.view_situationpersonnelle', 'personnes.view_revisionsituationpersonnelle',
    'personnes.view_situationadministrative', 'personnes.view_revisionsituationadministrative',
    'personnes.view_couverturesociale', 'personnes.view_revisioncouverturesociale',
    'personnes.view_ressourcepersonnelle', 'personnes.view_revisionressourcepersonnelle',
)


LOGEMENT_GROUPES = {
    'Sans logement': {'rue', 'urgence', 'hotel', 'insertion', 'incarceration', 'hospitalisation', 'asile'},
    'Habitat précaire ou inadapté': {'tiers', 'precaire', 'expulsion', 'violences', 'squat', 'indigne'},
}

DESTINATION_GROUPES = {
    'Logement ordinaire': {'Logement social', 'Logement privé', 'Logement privé avec mandat de gestion', 'Autre logement ordinaire'},
    'Logement durable adapté': {'Pension de famille', 'Résidence accueil', 'Intermédiation locative avec bail glissant',
                                'Intermédiation locative avec mandat de gestion', 'Sous-location avec bail glissant'},
    'Logement de transition': {'Résidence sociale', 'Foyer de jeunes travailleurs', 'Foyer de travailleurs migrants',
                              'Intermédiation locative sans bail glissant', 'Sous-location sans bail glissant'},
    'Hébergement d’urgence ou d’insertion': {'Hébergement d’urgence', 'Hébergement de stabilisation', 'Hôtel social',
                                            'Centre d’hébergement et de réinsertion sociale', 'Appartement relais'},
    'Dispositifs d’asile': {'Hébergement d’urgence pour demandeurs d’asile', 'Centre d’accueil pour demandeurs d’asile'},
}


def compter_groupe(compteurs, categories, valeur):
    for libelle, valeurs in categories.items():
        if valeur in valeurs:
            compteurs[libelle] += 1
            break


def six_mois_apres(jour):
    annee, mois = divmod(jour.year * 12 + jour.month - 1 + 6, 12)
    return jour.replace(year=annee, month=mois + 1,
                        day=min(jour.day, monthrange(annee, mois + 1)[1]))


def du_service(queryset, origine):
    if origine is None:
        return queryset
    identifiants = PorteeObjet.objects.filter(
        service_id=origine.service_id, modele=queryset.model._meta.label_lower,
    ).values('identifiant')
    return queryset.alias(identifiant_fait=Cast('pk', CharField())).filter(identifiant_fait__in=identifiants)


def rapport(versions, au):
    groupes = {
        titre: Counter() for titre in (
            'Adultes à l’entrée', 'Situation administrative à l’entrée',
            'Droits ouverts de la personne de référence', 'Couverture de la personne de référence',
            'Logement à l’entrée', 'Regroupements du logement à l’entrée', 'Motifs secondaires à l’entrée', 'Activité à l’entrée',
            'Ressources à l’entrée', 'Durée de prise en charge à la sortie',
            'Destination à la sortie', 'Regroupements des destinations', 'Motif de sortie', 'Précision sur la sortie',
        )
    }
    for version in versions:
        prise = version.accompagnement
        entree = prise.debut
        origine = existante(prise)
        try:
            composition = collectifs.composition(prise, entree)
        except ValidationError:
            composition = None
        for personne in prise.beneficiaires.all():
            age = (collectifs.age_exact(personne.date_naissance, entree)
                   if personne.date_naissance and personne.precision_naissance == 'exacte' else None)
            if age is None:
                groupes['Adultes à l’entrée']['Âge inconnu'] += 1
            if age is None or age < 18:
                continue
            groupes['Adultes à l’entrée']['Adultes'] += 1
            admin = du_service(dossier_complet.administration_a_date([personne], entree), origine).first()
            groupes['Situation administrative à l’entrée'][
                admin.droit_sejour if admin and admin.droit_sejour else 'Non renseignée'] += 1
            faits = {fait.dimension: fait for fait in du_service(m.SituationPersonnelle.objects.filter(
                personne=personne, debut__lte=entree).exclude(fin__lte=entree), origine)}
            for dimension, titre in (('logement', 'Logement à l’entrée'), ('emploi', 'Activité à l’entrée')):
                fait = faits.get(dimension)
                groupes[titre][fait.libelle_valeur if fait else 'Non renseignée'] += 1
            if logement := faits.get('logement'):
                compter_groupe(groupes['Regroupements du logement à l’entrée'], LOGEMENT_GROUPES,
                               logement.valeur.removeprefix('entree_'))
            motifs = faits.get('motifs_logement')
            if motifs:
                if motifs.valeur in ('violences', 'violences_et_traite'):
                    groupes['Motifs secondaires à l’entrée']['Violences conjugales'] += 1
                if motifs.valeur in ('traite', 'violences_et_traite'):
                    groupes['Motifs secondaires à l’entrée']['Traite des êtres humains'] += 1
            ressources = list(du_service(dossier_complet.a_date('ressources', [personne], entree), origine))
            details = [fait for fait in ressources if fait.etat == 'detail']
            revenus = groupes['Ressources à l’entrée']
            if details:
                revenus['Adultes ayant des ressources'] += 1
                revenus.update({fait.libelle for fait in details})
                if all(fait.devise == 'EUR' and fait.periodicite == 'mensuelle'
                       and fait.montant is not None for fait in details):
                    total = sum(fait.montant for fait in details)
                    revenus['Ressources mensuelles ≤ 800 €' if total <= Decimal(800)
                            else 'Ressources mensuelles > 800 €'] += 1
                else:
                    revenus['Montant mensuel non comparable'] += 1
            elif any(fait.etat == 'aucun' for fait in ressources):
                revenus['Absence déclarée de ressources'] += 1
            else:
                revenus['Non renseignées'] += 1
        if composition and composition.reference_id:
            personne = composition.reference
            admin = du_service(dossier_complet.administration_a_date([personne], entree), origine).first()
            groupes['Droits ouverts de la personne de référence'][
                admin.droits_ouverts if admin and admin.droits_ouverts else 'Non renseignés'] += 1
            couvertures = list(du_service(dossier_complet.a_date('couvertures', [personne], entree), origine))
            declarations = {fait.libelle for fait in couvertures if fait.etat == 'detail'}
            if declarations:
                groupes['Couverture de la personne de référence']['Couverture déclarée'] += 1
                groupes['Couverture de la personne de référence'].update(declarations)
            elif any(fait.etat == 'aucun' for fait in couvertures):
                groupes['Couverture de la personne de référence']['Sans couverture'] += 1
            else:
                groupes['Couverture de la personne de référence']['Non renseignée'] += 1
        if prise.fin and prise.fin <= au:
            duree = ('Moins de 15 jours' if (prise.fin - entree).days < 15 else
                     'De 15 jours à 6 mois' if prise.fin <= six_mois_apres(entree) else 'Plus de 6 mois')
            groupes['Durée de prise en charge à la sortie'][duree] += 1
            groupes['Destination à la sortie'][version.destination_sortie or 'Non renseignée'] += 1
            compter_groupe(groupes['Regroupements des destinations'], DESTINATION_GROUPES,
                           version.destination_sortie)
            if version.motif_sortie:
                groupes['Motif de sortie'][version.motif_sortie] += 1
            if version.qualification_sortie:
                groupes['Précision sur la sortie'][version.qualification_sortie] += 1
    return [(titre, sorted(compteurs.items())) for titre, compteurs in groupes.items() if compteurs]
