from acteurs.contexte import service_metier
"""Un contact daté, sans fonction professionnelle ni responsabilité juridique implicite."""
from django.db.models import Q
from . import suivi, series_personnelles
from .models import ContactMenage, RevisionContactMenage

DROITS_LECTURE = ('personnes.view_personne', 'personnes.view_menage',
    'personnes.view_contactmenage', 'personnes.view_revisioncontactmenage')


@service_metier
def designer(acteur, menage, contact, debut, source, attendu, motif='', correction=None):
    suivi.exiger(acteur, 'view_personne', 'view_menage', 'view_contactmenage',
        'view_revisioncontactmenage', 'add_contactmenage')
    return series_personnelles.enregistrer(acteur, menage, debut, source, attendu, motif, correction,
        {'contact': contact}, modele=ContactMenage, journal=RevisionContactMenage,
        champs=('contact',), lien='designation', champ_cible='menage')


def a_date(menages, date):
    return ContactMenage.objects.filter(menage__in=menages, debut__lte=date).filter(
        Q(fin__isnull=True) | Q(fin__gt=date)).select_related('contact')
