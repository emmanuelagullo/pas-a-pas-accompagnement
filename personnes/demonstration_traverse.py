"""Premier parcours fictif de La Traverse, de l’entrée à la sortie."""
from dataclasses import dataclass
from datetime import date, timedelta

from django.utils import timezone

from acteurs import services
from acteurs.collecte import profil
from acteurs.contexte import perimetre
from acteurs.models import AppartenanceProfessionnelle, Service
from acteurs.profils_collectifs import defaut_individuel
from . import bd6, collectifs, complements_identite, dossier_complet, hebergement, informations_suivi
from . import models as m, relations_personnelles, social, suivi


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


@dataclass(frozen=True)
class CasTraverse:
    nom: str
    membres: tuple
    description: str
    duree: int | None = 90
    non_loges: tuple = ()
    destination: str = 'Logement social'

    @property
    def libelle(self):
        return f'Famille {self.nom} — La Traverse'


CAS = (
    CasTraverse('Morel', (('Maya', 1989), ('Robin', 1987), ('Sam', 2018)),
        'Un couple déclaré et un enfant logés. Maya est la personne de référence. Comparez l’emploi de Maya à l’entrée et après son entrée en formation. Robin est déjà en emploi.', 210),
    CasTraverse('Aubert', (('Nora', 1991), ('Lou', 2014), ('Eli', 2020)),
        'Un parent et deux enfants dans la composition. Eli est logé ailleurs. Comparez la composition du ménage et les bénéficiaires du séjour.', non_loges=('Eli',)),
    CasTraverse('Benoît', (('Alix', 1984),),
        'Adulte seul, séjour de 12 jours et absence de couverture santé déclarée. Le décompte des droits ouverts sera à vérifier dans la fiche AHI.', 12, destination='Retour au domicile'),
    CasTraverse('Carrel', (('Camille', 1990), ('Sacha', 1992)),
        'Camille déclare les nationalités française et italienne, Sacha la nationalité portugaise. Vérifiez les déclarations. La règle de classement AHI reste à définir.'),
    CasTraverse('Delaunay', (('Noa', 1980), ('Lina', 1988)),
        'Noa déclare une demande d’asile en procédure normale. La situation de séjour de Lina reste inconnue. Le décompte par code AHI reste à mettre en place.'),
    CasTraverse('Fournier', (('Charlie', 1994), ('Diane', 1995)),
        'Deux adultes, Charlie est la personne de référence. La couverture AME de Charlie est renseignée. Vérifiez que la saisie des couvertures est réservée à la personne de référence dans ce service.'),
    CasTraverse('Garnier', (('Léa', 1983), ('Nils', 1985)),
        'Léa cumule deux ressources mensuelles en euros qui totalisent exactement 800 €. Nils dispose de 950 € par mois. Vérifiez les deux côtés du seuil et le décompte par personne.'),
    CasTraverse('Hamel', (('Zoé', 1993), ('Émile', 1990)),
        'Zoé déclare ne pas avoir de ressources. Le montant des ressources d’Émile est inconnu. Les deux situations doivent rester distinctes.'),
    CasTraverse('Joly', (('Ariane', 1986),),
        'Sortie vers le logement social après exactement 15 jours. La qualification DALO et l’adresse de correspondance restent à compléter dans le parcours AHI.', 15),
    CasTraverse('Lenoir', (('Jade', 1996),),
        'Prise en charge et hébergement toujours ouverts. La prise a une date de fin prévue. Ce dossier doit figurer à l’entrée et rester hors des sorties effectives.', None),
)


def declarer(acteur, code, personne, jour, **valeurs):
    modele = dossier_complet.RUBRIQUES[code].modele
    declaration = modele()
    champs = dossier_complet.RUBRIQUES[code].champs
    donnees = {champ: getattr(declaration, champ) for champ in champs}
    dossier_complet.enregistrer(
        acteur, code, personne, jour, None, 'Scénario fictif La Traverse',
        bd6.jeton(personne), **(donnees | valeurs),
    )


def renseigner_cas(auteur, cas, prise, membres, entree):
    reference = membres[0]
    if cas.nom == 'Morel':
        relations_personnelles.enregistrer(
            auteur, reference, membres[1], entree, None, 'couple', '',
            'Scénario fictif La Traverse', bd6.jeton(reference),
        )
        social.renseigner(auteur, prise, reference, 'emploi', 'sans_emploi', entree, 'Scénario fictif La Traverse')
        social.renseigner(auteur, prise, membres[1], 'emploi', 'emploi', entree, 'Scénario fictif La Traverse')
        social.renseigner(auteur, prise, reference, 'emploi', 'formation', entree + timedelta(days=30), 'Scénario fictif La Traverse')
    elif cas.nom == 'Benoît':
        declarer(auteur, 'couvertures', reference, entree, etat='aucun')
    elif cas.nom == 'Carrel':
        for personne, nationalites in zip(membres, (['Française', 'Italienne'], ['Portugaise'])):
            complements_identite.renseigner(
                auteur, personne, entree, 'Scénario fictif La Traverse', bd6.jeton(personne),
                sexe_declare='', naissance_lieu='', naissance_ville='', naissance_pays='',
                nationalites=nationalites, apatridie_declaree=None,
            )
    elif cas.nom == 'Delaunay':
        declaration = m.SituationAdministrative(droit_sejour='Demande d’asile en procédure normale')
        dossier_complet.administration(
            auteur, reference, entree, 'Scénario fictif La Traverse', bd6.jeton(reference),
            **{champ: getattr(declaration, champ) for champ in dossier_complet.ADMIN_CHAMPS},
        )
    elif cas.nom == 'Fournier':
        declarer(auteur, 'couvertures', reference, entree, libelle='AME')
    elif cas.nom == 'Garnier':
        for personne, libelle, montant in (
            (reference, 'Salaire', 500), (reference, 'RSA', 300), (membres[1], 'Salaire', 950),
        ):
            declarer(auteur, 'ressources', personne, entree, libelle=libelle, montant=montant, periodicite='mensuelle')
    elif cas.nom == 'Hamel':
        declarer(auteur, 'ressources', reference, entree, etat='aucun')
        declarer(auteur, 'ressources', membres[1], entree, libelle='Salaire', periodicite='mensuelle')


def creer_cas(auteur, cas, entree):
    sortie = entree + timedelta(days=cas.duree) if cas.duree else None
    membres = [
        m.Personne.objects.create(designation=f'{prenom} {cas.nom}', date_naissance=date(annee, 4, 8),
                                 precision_naissance='exacte', cree_par=auteur)
        for prenom, annee in cas.membres
    ]
    menage = suivi.creer_menage(auteur, cas.libelle, membres, entree)
    bd6.commenter(auteur, menage, cas.description, '', bd6.jeton(menage))
    prevision = entree + timedelta(days=300) if sortie is None else None
    prise = suivi.ouvrir(auteur, menage, membres, entree, prevision)
    prise = m.Accompagnement.objects.select_related('menage').get(pk=prise.pk)
    collectifs.renseigner(auteur, prise, collectifs.jeton(prise), debut=entree, reference=membres[0],
                          identifies=membres, complements=[], actualiser=True)
    loges = [personne for (prenom, _), personne in zip(cas.membres, membres) if prenom not in cas.non_loges]
    lieu = hebergement.creer_lieu(auteur, f'La Traverse — logement {cas.nom}', niveau='logement')
    accord = hebergement.accorder(auteur, prise, loges, entree, sortie)
    sejour = hebergement.admettre(auteur, accord, loges, entree)
    hebergement.ajouter_periode(auteur, sejour, entree, sortie, lieu=lieu)
    renseigner_cas(auteur, cas, prise, membres, entree)
    donnees = dict.fromkeys(informations_suivi.CHAMPS, '')
    donnees.update(motif_entree='Orientation vers un logement', dispositif_logement='iml',
                   type_logement='t1', situation_logement_entree='urgence')
    if sortie:
        hebergement.sortir(auteur, sejour, sortie)
        donnees.update(motif_sortie='Fin de prise en charge', destination_sortie=cas.destination)
    informations_suivi.enregistrer(auteur, prise, informations_suivi.jeton(prise, None), '', **donnees)
    if sortie:
        suivi.clore(auteur, prise, sortie)


def completer(auteur, etablissement, professionnel):
    entree = timezone.localdate() - timedelta(days=240)
    regles = profil('adultes')
    regles['coordonnees'] = {'portee': 'menage', 'population': 'tous'}
    regles['couvertures']['population'] = 'reference'
    service = Service.objects.create(
        etablissement=etablissement, libelle='La Traverse',
        sous_titre='Hébergement et accompagnement vers le logement',
        collecte_rubriques=regles,
        profil_collectif={**defaut_individuel(collecte_configuree=True), 'prestations': ['hebergement'], 'parcours_simples': ['hebergement'], 'fin_hebergement_unique': True},
        listes_saisie={'destination_sortie': DESTINATIONS_TRAVERSE},
    )
    AppartenanceProfessionnelle.objects.create(service=service, professionnel=professionnel, debut=entree)
    services.habiliter(auteur, auteur, service, 'social', entree, exporter=True)
    with perimetre(auteur, service=service, creation='dossier', nature_creation='menage'):
        for cas in CAS:
            creer_cas(auteur, cas, entree)
    return service
