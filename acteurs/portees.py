"""Rattachement des écritures à leur origine, dans leur transaction métier."""
from django.core.exceptions import PermissionDenied
from django.db import transaction
from .contexte import courant
from . import politique as p
from .models import PorteeObjet, DossierService, Responsabilite


def existante(objet):
    if objet is None or not objet.pk: return None
    return PorteeObjet.objects.filter(modele=objet._meta.label_lower, identifiant=str(objet.pk)).first()


def parent(objet):
    # Ordre du plus précis au plus général ; les journaux suivent le fait exact.
    priorites=('menage',) if objet._meta.model_name=='appartenance' else ()
    priorites+=('fait', 'piece', 'element', 'declaration', 'situation', 'coordonnees', 'complement', 'relation', 'designation', 'affectation', 'transmission', 'note', 'action_relais',
                'document', 'version', 'financement', 'accord_hebergement', 'accord_repas',
                'accord_aide', 'accord', 'sejour', 'accompagnement', 'personne', 'menage')
    autres=tuple(f.name for f in objet._meta.fields if f.is_relation and f.remote_field.model._meta.app_label=='personnes' and f.remote_field.model._meta.model_name not in p.REPERTOIRES)
    for nom in dict.fromkeys(priorites+autres):
        try:
            champ = objet._meta.get_field(nom)
        except Exception:
            continue
        if champ.is_relation and hasattr(champ,"attname") and getattr(objet, champ.attname, None):
            x = champ.remote_field.model._base_manager.get(pk=getattr(objet, champ.attname))
            origine = existante(x)
            ctx=courant()
            if x._meta.model_name in ('personne','menage') and ctx:
                # L'identité peut être réutilisée ; les nouveaux faits portent le
                # service explicitement choisi, pas celui de sa première création.
                service=p.service_creation(type(objet))
                dossiers=DossierService.objects.filter(service_id=service,**{x._meta.model_name:x})
                if x._meta.model_name=='personne' and not dossiers.exists():
                    from personnes.models import Appartenance
                    dossiers=DossierService.objects.filter(service_id=service,
                        menage_id__in=Appartenance._base_manager.filter(personne=x).values('menage_id'))
                ds=dossiers.first()
                if ds:return PorteeObjet(service_id=service,dossier=ds)
            if origine: return origine
    return None


def preparer(objet):
    ctx = courant()
    if not ctx or not p.active(): return None
    nom = objet._meta.model_name
    if nom in p.REPERTOIRES or nom in {'modelerapport', 'importparametrage'}:
        if not p.habilitations(ctx.compte).filter(tache__in=p.taches(type(objet))).exists(): raise PermissionDenied
        return None
    ancienne = existante(objet)
    if not objet._state.adding:
        p.exiger_objet(ctx.compte, objet, True)
        return ancienne
    origine = parent(objet)
    if origine:
        # Créer une prestation est possible sans reprendre le dossier : droit de
        # tâche dans le service, visibilité minimale du parent, aucune lecture sociale.
        if nom in ('accordhebergement', 'accordrepas', 'accordaide', 'accompagnement'):
            if not p.habilitations(ctx.compte).filter(service=origine.service, tache__in=p.taches(type(objet))).exists(): raise PermissionDenied
        elif not p.peut_renseigner(ctx.compte,origine,type(objet)):
            raise PermissionDenied('Vous ne pouvez pas renseigner cet élément.')
        return origine
    service_id = p.service_creation(type(objet))
    # Seules les identités et les contributions collectives peuvent naître sans parent.
    if nom not in ('personne', 'menage', 'transmission', 'actionrelais', 'appel115', 'tarifprestation', 'versiontarif'):
        raise PermissionDenied('Rattachez cette information à un dossier autorisé.')
    return PorteeObjet(service_id=service_id)


def enregistrer(objet, origine):
    ctx = courant()
    if not ctx or origine is None: return
    if existante(objet): return
    nom = objet._meta.model_name
    dossier = origine.dossier
    if nom in ('personne', 'menage') and not (nom=='personne' and ctx.creation=='dossier' and ctx.nature_creation=='menage'):
        dossier, _ = DossierService.objects.get_or_create(service_id=origine.service_id,
            **{nom:objet}, defaults={'cree_par':ctx.compte})
        prof = ctx.responsable_id or p.professionnel(ctx.compte)
        if prof and p.habilitations(ctx.compte).filter(service_id=origine.service_id, tache='social').exists():
            Responsabilite.objects.create(dossier=dossier, professionnel_id=prof, cree_par=ctx.compte)
            DossierService.objects.filter(pk=dossier.pk).update(en_attente=False)
    prise = origine.prise
    prestation_modele, prestation_id = origine.prestation_modele, origine.prestation_id
    if nom == 'accompagnement': prise = objet
    if nom in ('accordhebergement', 'accordrepas', 'accordaide'):
        prestation_modele, prestation_id = nom, objet.pk
    PorteeObjet.objects.create(modele=objet._meta.label_lower, identifiant=str(objet.pk),
        service_id=origine.service_id, dossier=dossier, prise=prise,
        prestation_modele=prestation_modele, prestation_id=prestation_id)
    if nom=='appartenance' and dossier and ('personnes.personne',str(objet.personne_id)) in ctx.nouveaux:
        PorteeObjet.objects.filter(modele='personnes.personne',identifiant=str(objet.personne_id),service_id=origine.service_id,dossier__isnull=True).update(dossier=dossier)
    if dossier and nom in ('accompagnement', 'accordhebergement', 'accordrepas', 'accordaide'):
        from .services import proposer_responsabilites
        proposer_responsabilites(ctx.compte, objet, dossier)
