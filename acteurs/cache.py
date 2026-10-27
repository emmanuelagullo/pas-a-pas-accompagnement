"""Mémoire limitée à la requête ; jamais un cache de droits entre requêtes."""
from django.db import models
from .contexte import courant


def invalider(*args, **kwargs):
    ctx=courant()
    if ctx:
        generation=ctx.memo.get('generation',0)+1
        ctx.memo.clear();ctx.memo['generation']=generation


def mutation_organisation(sender,**kwargs):
    if sender._meta.app_label=='acteurs':invalider()


class RequeteOrganisation(models.QuerySet):
    def update(self,**kwargs):
        invalider();return super().update(**kwargs)
    def delete(self):
        invalider();return super().delete()
    def bulk_create(self,*args,**kwargs):
        invalider();return super().bulk_create(*args,**kwargs)
    def bulk_update(self,*args,**kwargs):
        invalider();return super().bulk_update(*args,**kwargs)


class ModeleOrganisation(models.Model):
    objects=models.Manager.from_queryset(RequeteOrganisation)()
    class Meta:abstract=True
