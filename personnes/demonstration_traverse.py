"""Premier parcours fictif de La Traverse, de l’entrée à la sortie."""
from datetime import date, timedelta

from django.utils import timezone

from acteurs import services
from acteurs.collecte import profil
from acteurs.contexte import perimetre
from acteurs.models import AppartenanceProfessionnelle, Service
from acteurs.profils_collectifs import defaut_individuel
from . import collectifs, hebergement, informations_suivi, models as m, suivi


# Choix du service fictif, proposés à la saisie sans présélection.
DESTINATIONS_TRAVERSE = [
    'Logement social', 'Logement privé', 'Logement privé avec mandat de gestion',
    'Pension de famille', 'Résidence accueil',
    'Intermédiation locative avec bail glissant',
    'Intermédiation locative avec mandat de gestion', 'Sous-location avec bail glissant',
    'Résidence sociale', 'Foyer de jeunes travailleurs', 'Foyer de travailleurs migrants',
    'Intermédiation locative sans bail glissant', 'Sous-location sans bail glissant',
    'Hébergement d’urgence', 'Hébergement de stabilisation', 'Hôtel social',
    'Centre d’hébergement et de réinsertion sociale', 'Appartement relais',
    'Hospitalisation', 'Incarcération', 'Hébergé chez un tiers', 'Rue',
    'Établissement pour personnes âgées ou handicapées', 'Retour au domicile',
    'Structure médico-sociale', 'Hébergement d’urgence pour demandeurs d’asile',
    'Centre d’accueil pour demandeurs d’asile', 'Autre destination',
    'Sans information', 'Hors champ',
]


def completer(auteur, etablissement, professionnel):
    entree = timezone.localdate() - timedelta(days=240)
    sortie = entree + timedelta(days=210)
    regles = profil('adultes')
    regles['coordonnees'] = {'portee': 'menage', 'population': 'tous'}
    regles['couvertures']['population'] = 'reference'
    service = Service.objects.create(
        etablissement=etablissement, libelle='La Traverse',
        sous_titre='Hébergement et accompagnement vers le logement',
        collecte_rubriques=regles,
        profil_collectif={**defaut_individuel(collecte_configuree=True), 'prestations': ['hebergement'], 'parcours_simples': ['hebergement']},
        listes_saisie={'destination_sortie': DESTINATIONS_TRAVERSE},
    )
    AppartenanceProfessionnelle.objects.create(service=service, professionnel=professionnel, debut=entree)
    services.habiliter(auteur, auteur, service, 'social', entree, exporter=True)
    with perimetre(auteur, service=service, creation='dossier', nature_creation='menage'):
        adulte = m.Personne.objects.create(designation='Maya Morel', date_naissance=date(1989, 4, 8),
                                         precision_naissance='exacte', cree_par=auteur)
        enfant = m.Personne.objects.create(designation='Sam Morel', date_naissance=date(2018, 9, 7),
                                         precision_naissance='exacte', cree_par=auteur)
        menage = suivi.creer_menage(auteur, 'Famille Morel — La Traverse', [adulte, enfant], entree)
        prise = suivi.ouvrir(auteur, menage, [adulte, enfant], entree)
        prise = m.Accompagnement.objects.select_related("menage").get(pk=prise.pk)
        collectifs.renseigner(auteur, prise, collectifs.jeton(prise), debut=entree, reference=adulte,
                              identifies=[adulte, enfant], complements=[], actualiser=True)
        lieu = hebergement.creer_lieu(auteur, 'La Traverse — logement T1', niveau='logement')
        accord = hebergement.accorder(auteur, prise, [adulte, enfant], entree, sortie)
        sejour = hebergement.admettre(auteur, accord, [adulte, enfant], entree)
        hebergement.ajouter_periode(auteur, sejour, entree, sortie, lieu=lieu)
        hebergement.sortir(auteur, sejour, sortie, destination_sortie="Logement social")
        donnees = dict.fromkeys(informations_suivi.CHAMPS, '')
        donnees.update(motif_entree='Orientation vers un logement', motif_sortie='Fin de prise en charge',
                       dispositif_logement='iml', type_logement='t1',
                       situation_logement_entree='urgence')
        informations_suivi.enregistrer(auteur, prise, informations_suivi.jeton(prise, None), '', **donnees)
        suivi.clore(auteur, prise, sortie)
    return service
