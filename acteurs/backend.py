"""Une habilitation explicite de tâche, bornée au service par les sélections métier."""
from django.apps import apps
from functools import lru_cache
from django.core.exceptions import PermissionDenied
from .contexte import courant
from . import politique as p


class HabilitationsBackend:
    def authenticate(self, request, **kwargs): return None
    def has_perm(self, user_obj, perm, obj=None):
        if not perm.startswith('personnes.') or not p.active(): return False
        code=perm.split('.',1)[1]
        registre=registre_permissions()
        if code not in registre:raise PermissionDenied
        action,modele=registre[code]
        nom=modele._meta.model_name
        if action == 'delete' and nom != 'modelerapport': raise PermissionDenied
        ctx = courant()
        if not user_obj.is_active:raise PermissionDenied
        cle=('permissions',user_obj.pk)
        if ctx and cle in ctx.memo:hs=ctx.memo[cle]
        else:
            hs=list(p.habilitations(user_obj).values('tache','service_id','exporter','statistiques_service','statistiques_etablissement'))
            if ctx:ctx.memo[cle]=hs
        if ctx and ctx.statistiques in ('service','etablissement') and action=='view':
            option='statistiques_etablissement' if ctx.statistiques=='etablissement' else 'statistiques_service'
            if any(h['service_id']==ctx.service_id and h[option] for h in hs):return True
        if not any(h['tache'] in p.taches(modele) for h in hs):raise PermissionDenied
        if action=='exporter' and not any(h['exporter'] for h in hs):raise PermissionDenied
        if obj is not None: p.exiger_objet(user_obj,obj,action!='view')
        return True


@lru_cache(maxsize=1)
def registre_permissions():
    registre={}
    for model in apps.get_app_config('personnes').get_models():
        for action in model._meta.default_permissions:registre[action+'_'+model._meta.model_name]=(action,model)
        for code,libelle in model._meta.permissions:registre[code]=(code,model)
    return registre
