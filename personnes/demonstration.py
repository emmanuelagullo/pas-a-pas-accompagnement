"""Jeu métier fictif distribuable sous forme de code, jamais d'une base privée."""
from datetime import timedelta
from io import StringIO
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone
from . import models as m, suivi, repas, hebergement as h, social, transmissions


def espace_metier_vide():
    return not any(modele.objects.exists() for modele in apps.get_app_config('personnes').get_models())


def autoriser(compte):
    call_command('autoriser_chrs7', compte.username, stdout=StringIO())
    call_command('autoriser_bd3', compte.username, stdout=StringIO())
    compte.user_permissions.add(Permission.objects.get(content_type__app_label='personnes', codename='add_personne'))
    compte.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes', codename__in=(
        'view_transmission', 'add_transmission', 'change_transmission',
        'view_actionrelais', 'add_actionrelais', 'change_actionrelais',
        'view_notepartagee', 'add_notepartagee', 'change_notepartagee')))
    # Les commandes rechargent le compte ; ne pas conserver un cache de droits.
    return get_user_model().objects.get(pk=compte.pk)


@transaction.atomic
def generer(compte, *, professionnels=None, reference=None):
    """Après création explicite des comptes, dans la transaction de l'appelant.

    Le contenu et les décalages sont reproductibles, pas les UUID, secrets,
    mots de passe ou horodatages techniques. Aucune remise à zéro implicite.
    """
    if not espace_metier_vide():
        raise ValidationError('Espace métier non vide : aucune donnée modifiée.')
    acteurs = professionnels or {'nadia': compte, 'remi': compte, 'camille': compte}
    autorises = {acteur.pk: acteur for acteur in acteurs.values()}
    autorises = {pk: autoriser(acteur) for pk, acteur in autorises.items()}
    acteurs = {nom: autorises[acteur.pk] for nom, acteur in acteurs.items()}
    nadia, remi, camille = (acteurs[nom] for nom in ('nadia', 'remi', 'camille'))
    jour = reference or timezone.localdate()
    if jour > timezone.localdate():
        raise ValidationError('La date de référence ne peut pas être future.')
    def j(delta):
        return jour + timedelta(days=delta)
    personnes = {nom: m.Personne.objects.create(designation=nom + ' (fictif)', cree_par=nadia)
                 for nom in ('Alex', 'Samira', 'Lina', 'Adam', 'Thomas')}
    suivis = {}
    for nom, membres in [('Alex', ['Alex']), ('Samira, Lina et Adam', ['Samira', 'Lina', 'Adam']), ('Thomas', ['Thomas'])]:
        beneficiaires = [personnes[n] for n in membres]
        menage = suivi.creer_menage(nadia, nom + ' — Les Passerelles (fictif)', beneficiaires, j(-60))
        suivis[membres[0]] = suivi.ouvrir(nadia, menage, beneficiaires, j(-60))
    # Alex est accompagné sans hébergement. Le repas du jour reste à saisir.
    accord = repas.accorder(camille, suivis['Alex'], [personnes['Alex']], j(-7), None, 'dejeuner')
    for delta in (-2, -1):
        repas.distribuer(camille, accord, personnes['Alex'], j(delta), 1)
    interne = h.creer_lieu(remi, 'Les Passerelles — unité A (fictive)')
    partenaire = h.creer_lieu(remi, 'Appartement relais (fictif)', 'Association des Rives (fictive)')
    famille = [personnes[n] for n in ('Samira', 'Lina', 'Adam')]
    accord = h.accorder(remi, suivis['Samira'], famille, j(-40), None)
    sejour = h.admettre(remi, accord, famille, j(-39))
    h.ajouter_periode(remi, sejour, j(-39), j(-15), lieu=interne)
    h.ajouter_periode(remi, sejour, j(-15), None, lieu=partenaire)
    h.ajouter_periode(remi, sejour, j(-7), j(-5), absence=True)
    # Les enfants ont chacun des prestations, sans lien de représentation légale.
    accord = repas.accorder(camille, suivis['Samira'], famille, j(-39), None, 'diner')
    for personne in famille:
        repas.distribuer(camille, accord, personne, j(-1), 1)
    thomas = personnes['Thomas']
    accord = h.accorder(remi, suivis['Thomas'], [thomas], j(-50), j(-10))
    sejour = h.admettre(remi, accord, [thomas], j(-49))
    h.ajouter_periode(remi, sejour, j(-49), None, lieu=interne)
    h.sortir(remi, sejour, j(-10))
    source = 'Entretien fictif de démonstration'
    for dimension, valeur, delta in [('logement', 'hebergement', -49), ('logement', 'logement_autonome', -10),
                                     ('emploi', 'sans_emploi', -49), ('emploi', 'formation', -5),
                                     ('ressources', 'inconnu', -49), ('ressources', 'ressources_declarees', -5)]:
        social.renseigner(nadia, suivis['Thomas'], thomas, dimension, valeur, j(delta), source)
    social.evenement(nadia, suivis['Thomas'], thomas, j(-10), 'Installation dans un logement autonome fictif.', source)
    social.bilan(nadia, suivis['Thomas'], j(-2), 'Bilan fictif : installation réalisée ; accompagnement maintenu pour les démarches et la formation.')
    transmissions.transmettre(remi, 'Relève fictive : vérifier les arrivées et les repas du jour.')
    transmissions.noter(nadia, 'Point fictif à reprendre lors du prochain entretien.', accompagnement=suivis['Alex'])
    transmissions.noter(remi, 'Retour fictif à confirmer avec la personne.', personne=thomas)
    return suivis


@transaction.atomic
def preparer_jeu_public():
    """Comptes du jeu neuf : serveur jetable ou espace d’essai local distinct."""
    from pas_a_pas_accompagnement.demo import IDENTIFIANT, MOT_DE_PASSE
    if get_user_model().objects.exists() or not espace_metier_vide():
        raise ValidationError('Base non vide : aucune donnée modifiée.')
    compte = get_user_model().objects.create_user(IDENTIFIANT, password=MOT_DE_PASSE)
    professionnels = {nom: get_user_model().objects.create_user(nom, password=MOT_DE_PASSE,
        first_name=prenom) for nom, prenom in [('nadia', 'Nadia'), ('remi', 'Rémi'), ('camille', 'Camille')]}
    autoriser(compte)
    return generer(compte, professionnels=professionnels)
