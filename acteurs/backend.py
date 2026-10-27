"""Une habilitation explicite de tâche, bornée au service par les sélections métier."""
from django.apps import apps
from django.core.exceptions import PermissionDenied
from .contexte import courant
from . import politique as p


class HabilitationsBackend:
    def authenticate(self, request, **kwargs): return None
    def has_perm(self, user_obj, perm, obj=None):
        if not perm.startswith('personnes.') or not p.active(): return False
        code=perm.split('.',1)[1]
        registre={}
        for model in apps.get_app_config('personnes').get_models():
            for action_defaut in model._meta.default_permissions:
                registre[action_defaut+'_'+model._meta.model_name]=(action_defaut,model)
            for code_metier,libelle in model._meta.permissions:
                registre[code_metier]=(code_metier,model)
        if code not in registre:raise PermissionDenied
        action,modele=registre[code]
        nom=modele._meta.model_name
        if action == 'delete' and nom != 'modelerapport': raise PermissionDenied
        hs = p.habilitations(user_obj)
        ctx = courant()
        if ctx and ctx.statistiques in ('service','etablissement') and action=='view':
            option='statistiques_etablissement' if ctx.statistiques=='etablissement' else 'statistiques_service'
            if hs.filter(service_id=ctx.service_id,**{option:True}).exists():return True
        if not hs.filter(tache__in=p.taches(modele)).exists(): raise PermissionDenied
        # Les capacités sensibles demeurent distinctes de la participation au suivi.
        if action == 'exporter' and not hs.filter(exporter=True).exists(): raise PermissionDenied
        if obj is not None: p.exiger_objet(user_obj,obj,action!='view')
        return True
