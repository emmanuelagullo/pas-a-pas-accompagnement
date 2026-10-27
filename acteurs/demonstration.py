"""Parcours public acteurs, uniquement lors de la préparation d’une base vide."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from personnes.demonstration import espace_metier_vide
from pas_a_pas_accompagnement.demo import MOT_DE_PASSE
from .essai import preparer as preparer_essai
from .models import Service


@transaction.atomic
def preparer():
    if not getattr(settings, 'DEMONSTRATION_PUBLIQUE', False):
        raise ValidationError('Parcours réservé à la démonstration publique jetable.')
    if get_user_model().objects.exists() or not espace_metier_vide() or Service.objects.exists():
        raise ValidationError('Base non vide : aucune donnée modifiée.')
    comptes = {nom: get_user_model().objects.create_user(nom, password=MOT_DE_PASSE)
               for nom in ('essai', 'remi', 'coordination')}
    return preparer_essai(comptes['essai'], comptes['remi'], comptes['coordination'])
