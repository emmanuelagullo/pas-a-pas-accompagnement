"""Sélection des lignes à chaque exécution, y compris les relations inverses.

Aucune modification globale de l'ORM : ces gestionnaires appartiennent uniquement
aux modèles métier de Pas à Pas. Les gestionnaires de base des migrations restent
intégraux. Les copies physiques ne passent pas par une projection web.
"""
from django.core.exceptions import PermissionDenied
from django.db import models, transaction
from .contexte import courant


class QuerySetControle(models.QuerySet):
    def selection(self, ecriture=False):
        from .politique import filtre
        # Un QuerySet Django ordinaire évite toute réentrée du contrôle. Les filtres,
        # bornes, préchargements et itérateurs de la requête originale sont conservés.
        qs = models.QuerySet(model=self.model, query=self.query.clone(), using=self.db, hints=self._hints)
        qs._iterable_class = self._iterable_class
        qs._fields = self._fields
        qs._known_related_objects = self._known_related_objects
        qs._prefetch_related_lookups = self._prefetch_related_lookups
        qs.query.add_q(filtre(self.model, ecriture))
        ctx=courant()
        if ctx and ctx.export_demande and not ecriture:
            from .politique import active, REPERTOIRES, habilitations
            if active() and self.model._meta.model_name not in REPERTOIRES|{'modelerapport','importparametrage'}:
                from .models import PorteeObjet, DossierService
                identifiants=list(qs.values_list('pk',flat=True))
                services=set(PorteeObjet.objects.filter(modele=self.model._meta.label_lower,
                    identifiant__in=[str(pk) for pk in identifiants]).values_list('service_id',flat=True))
                autorises=set(habilitations(ctx.compte).values_list('service_id',flat=True))
                services &= autorises
                if not services and self.model._meta.model_name in ('personne','menage'):
                    services=set(DossierService.objects.filter(service_id__in=autorises,
                        **{self.model._meta.model_name+'_id__in':identifiants}).values_list('service_id',flat=True))
                ctx.services_export.update(services)
                if ctx.statistiques not in ('service','etablissement'):
                    exportables=set(habilitations(ctx.compte).filter(exporter=True).values_list('service_id',flat=True))
                    if not services.issubset(exportables):raise PermissionDenied('L’export n’est pas autorisé pour tous les services de cette sélection.')
        return qs

    def _fetch_all(self):
        from .politique import active
        if courant() is None or not active():return super()._fetch_all()
        ctx=courant()
        if getattr(self,'_contexte_resultats',None) is not ctx:
            self._result_cache=None
            self._contexte_resultats=ctx
        if self._result_cache is None:
            qs = self.selection()
            qs._fetch_all()
            self._result_cache = qs._result_cache
            self._prefetch_done = qs._prefetch_done

    def resolve_expression(self, *args, **kwargs):
        return self.selection().resolve_expression(*args, **kwargs)

    def count(self): return self.selection().count()
    def exists(self): return self.selection().exists()
    def aggregate(self, *args, **kwargs): return self.selection().aggregate(*args, **kwargs)
    def iterator(self, *args, **kwargs): return self.selection().iterator(*args, **kwargs)
    def update(self, **kwargs):
        from .politique import active
        if courant() and active():
            immuables={'personne','menage','accompagnement','accord','sejour','piece','fait','element','version','financement','document','auteur','cree_par'}
            if any(k.removesuffix('_id') in immuables for k in kwargs):
                raise PermissionDenied('Le rattachement et l’auteur ne se déplacent pas par une correction.')
        return self.selection(True).update(**kwargs)
    def delete(self):
        from .politique import active
        if courant() and active() and self.model._meta.model_name != 'modelerapport': raise PermissionDenied('Les données ne sont pas supprimées par un accès métier.')
        return self.selection(True).delete()
    def bulk_create(self, *args, **kwargs):
        from .politique import active
        if courant() and active(): raise PermissionDenied('La création groupée exige les services métier journalisés.')
        return super().bulk_create(*args, **kwargs)
    def bulk_update(self, *args, **kwargs):
        from .politique import active
        if courant() and active(): raise PermissionDenied('La correction groupée exige les services métier journalisés.')
        return super().bulk_update(*args, **kwargs)


class ManagerControle(models.Manager.from_queryset(QuerySetControle)):
    pass


def controler_manager(manager):
    """Préserver non_annules() et le filtrage des chronologies retirées."""
    cls = type(manager)
    class Controle(cls):
        def get_queryset(self):
            qs = super().get_queryset()
            qs.__class__ = type('RequeteControlee', (QuerySetControle, type(qs)), {}) if not isinstance(qs, QuerySetControle) else type(qs)
            return qs
    manager.__class__ = Controle
    return manager


class ModeleControle(models.Model):
    objects = ManagerControle()
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from .portees import preparer, enregistrer
        with transaction.atomic():
            creation=self._state.adding
            ctx=courant()
            from .politique import active
            if creation and ctx and active() and self.pk is not None:
                # Un UUID fourni à une création ne doit jamais provoquer l'UPDATE
                # implicite d'une ligne existante, même invisible au créateur.
                if models.QuerySet(model=type(self)).filter(pk=self.pk).exists():
                    raise PermissionDenied('Cette création existe déjà ; aucune donnée n’a été remplacée.')
            if ctx and active():
                if creation:
                    for nom in ('auteur','cree_par'):
                        if hasattr(self,nom+'_id') and getattr(self,nom+'_id') != ctx.compte.pk:
                            raise PermissionDenied('L’auteur de la saisie est le compte courant.')
                else:
                    noms=[f.attname for f in self._meta.fields if f.is_relation and f.name in
                        {'personne','menage','accompagnement','accord','sejour','piece','fait','element','version','financement','document','auteur','cree_par'}]
                    ancienne=models.QuerySet(model=type(self)).filter(pk=self.pk).values(*noms).first() if noms else None
                    if ancienne and any(getattr(self,n)!=ancienne[n] for n in noms):
                        raise PermissionDenied('Le rattachement et l’auteur sont conservés ; utilisez le parcours métier approprié.')
            origine = preparer(self)
            resultat = super().save(*args, **kwargs)
            enregistrer(self, origine)
            if creation and ctx and origine is not None:
                ctx.nouveaux.add((self._meta.label_lower,str(self.pk)))
            return resultat

    def delete(self, *args, **kwargs):
        from .politique import active
        if courant() and active(): raise PermissionDenied('Une annulation conserve les données.')
        return super().delete(*args, **kwargs)
