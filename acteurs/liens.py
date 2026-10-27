from django.core.exceptions import PermissionDenied
from .contexte import courant
from . import politique as p


def verifier(sender,instance,action,reverse,model,pk_set,**kwargs):
    if action not in ('pre_add','pre_remove','pre_clear') or instance._meta.app_label!='personnes':return
    ctx=courant()
    if not ctx or not p.active():return
    p.exiger_objet(ctx.compte,instance,True)
    if model._meta.app_label=='personnes' and pk_set:
        from .contexte import perimetre
        accessibles=set(model.objects.filter(pk__in=pk_set).values_list('pk',flat=True))
        if accessibles!=set(pk_set):raise PermissionDenied('Un bénéficiaire est hors du périmètre autorisé.')
