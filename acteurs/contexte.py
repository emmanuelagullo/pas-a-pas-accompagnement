from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
from inspect import signature


@dataclass(frozen=True)
class Contexte:
    compte: object
    service_id: object = None
    statistiques: object = False
    responsable_id: object = None
    creation: str = ""
    nouveaux: set = field(default_factory=set)
    controle_actif: object = None
    export_demande: bool = False
    services_export: set = field(default_factory=set)
    nature_creation: str = ""


_courant = ContextVar('acteurs_perimetre', default=None)


def courant(): return _courant.get()


@contextmanager
def perimetre(compte, service=None, statistiques=False, responsable=None, creation=None, export_demande=None, nature_creation=None):
    ancien = courant()
    if ancien and ancien.compte.pk != compte.pk:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied('Un service ne peut pas changer le compte de la requête.')
    from .politique import active
    controle=ancien.controle_actif if ancien else active()
    ctx = Contexte(compte, getattr(service, 'pk', service) if service is not None else
        (ancien.service_id if ancien else None), statistiques or (ancien.statistiques if ancien else False),
        responsable if responsable is not None else (ancien.responsable_id if ancien else None),
        creation if creation is not None else (ancien.creation if ancien else ""),
        ancien.nouveaux if ancien else set(), controle,
        bool(export_demande) if export_demande is not None else bool(ancien and ancien.export_demande),
        ancien.services_export if ancien else set(),
        nature_creation if nature_creation is not None else (ancien.nature_creation if ancien else ""))
    jeton = _courant.set(ctx)
    try: yield ctx
    finally: _courant.reset(jeton)


def service_metier(f):
    """Le même contrôle dans les appels HTTP et les appels Python des services."""
    sig = signature(f)
    @wraps(f)
    def executer(*args, **kwargs):
        valeurs = sig.bind(*args, **kwargs).arguments
        compte = next((valeurs[n] for n in ('acteur', 'auteur', 'utilisateur') if n in valeurs), None)
        if not getattr(compte, 'is_authenticated', False):
            from .politique import active
            if active():
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied
            return f(*args, **kwargs)  # Les validations spécialisées restent responsables du refus.
        with perimetre(compte):
            from django.db.models import Model
            from . import politique as p
            if p.active():
                def verifier(v):
                    if isinstance(v, Model) and v._meta.app_label == 'personnes' and not v._state.adding:
                        p.exiger_objet(compte,v)
                    elif isinstance(v,dict):
                        for x in v.values():verifier(x)
                    elif isinstance(v,(list,tuple,set)):
                        for x in v:verifier(x)
                for n,v in valeurs.items():
                    if n not in ('acteur','auteur','utilisateur'):verifier(v)
            return f(*args, **kwargs)
    return executer
