"""Ordre commun aux écritures liées : ménage, accompagnement, séjour.

Les services restent applicatifs. Un échec de verrouillage refuse l’écriture.
"""
from functools import wraps
from inspect import signature
from django.db import transaction
from django.db.models import F
from .models import Menage


def menage_de(objet):
    if isinstance(objet, Menage): return objet
    if hasattr(objet, "menage_id"): return objet.menage
    if hasattr(objet, "accompagnement_id"): return objet.accompagnement.menage
    if hasattr(objet, "accord_id"): return objet.accord.accompagnement.menage
    return objet.sejour.accord.accompagnement.menage


def serialiser(argument):
    def decorer(fonction):
        sig = signature(fonction)
        @wraps(fonction)
        def executer(*args, **kwargs):
            objet = sig.bind(*args, **kwargs).arguments[argument]
            # Les relations de parenté ne sont pas modifiables par les parcours.
            menage_id = menage_de(objet).pk
            with transaction.atomic():
                Menage.objects.filter(pk=menage_id).update(revision=F("revision") + 1)
                return fonction(*args, **kwargs)
        return executer
    return decorer
