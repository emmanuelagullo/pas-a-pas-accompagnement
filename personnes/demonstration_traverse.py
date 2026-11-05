"""Premier parcours fictif de La Traverse, de l’entrée à la sortie."""
from datetime import date, timedelta

from django.utils import timezone

from acteurs import services
from acteurs.collecte import profil
from acteurs.contexte import perimetre
from acteurs.models import AppartenanceProfessionnelle, Service
from acteurs.profils_collectifs import defaut_individuel
from . import collectifs, hebergement, informations_suivi, models as m, suivi


def completer(auteur, etablissement, professionnel):
    entree = timezone.localdate() - timedelta(days=240)
    sortie = entree + timedelta(days=210)
    regles = profil('adultes')
    regles['coordonnees'] = {'portee': 'menage', 'population': 'tous'}
    for code in ('administration', 'couvertures'):
        regles[code]['population'] = 'reference'
    service = Service.objects.create(
        etablissement=etablissement, libelle='La Traverse',
        sous_titre='Hébergement et accompagnement vers le logement',
        collecte_rubriques=regles,
        profil_collectif={**defaut_individuel(collecte_configuree=True), 'prestations': ['hebergement']},
        listes_saisie={'destination_sortie': ['Logement social', 'Logement privé', 'Résidence sociale', 'Pension de famille']},
    )
    AppartenanceProfessionnelle.objects.create(service=service, professionnel=professionnel, debut=entree)
    services.habiliter(auteur, auteur, service, 'social', entree)
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
        hebergement.sortir(auteur, sejour, sortie)
        donnees = dict.fromkeys(informations_suivi.CHAMPS, '')
        donnees.update(motif_entree='Orientation vers un logement', motif_sortie='Fin de prise en charge',
                       destination_sortie='Logement social')
        informations_suivi.enregistrer(auteur, prise, informations_suivi.jeton(prise, None), '', **donnees)
        suivi.clore(auteur, prise, sortie)
    return service
