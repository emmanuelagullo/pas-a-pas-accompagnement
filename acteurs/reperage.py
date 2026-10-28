"""Répertoire d'identités explicite ; aucune ouverture des faits sociaux."""
from django.db import transaction
from django.db.models import Q,F
from django.core.exceptions import PermissionDenied,ValidationError
from django.utils import timezone
from . import politique as p,services as s
from .contexte import courant,perimetre
from .models import DossierService,PorteeObjet,DemandeRattachement


def dossiers(compte):
    hs=p.habilitations(compte).filter(tache__in=['social','accueil','gestion'],service__etablissement__reperage_identites=True)
    return DossierService.objects.filter(service__etablissement_id__in=hs.values('service__etablissement_id'))


def identites(compte,nature):
    ds=dossiers(compte)
    ids=set(ds.exclude(**{nature+'__isnull':True}).values_list(nature+'_id',flat=True))
    if nature=='personne':
        from personnes.models import Appartenance
        # Lecture technique minimale : seuls les identifiants d'appartenance du répertoire autorisé.
        ids.update(Appartenance._base_manager.filter(menage_id__in=ds.values('menage_id')).values_list('personne_id',flat=True))
    return ids


def equipes(compte,nature,pk):
    ds=dossiers(compte)
    if nature=='personne':
        from personnes.models import Appartenance
        ds=ds.filter(Q(personne_id=pk)|Q(menage_id__in=Appartenance._base_manager.filter(personne_id=pk).values('menage_id')))
    else:ds=ds.filter(menage_id=pk)
    return ds.select_related('service__etablissement')


def prises(compte):
    return PorteeObjet.objects.filter(modele='personnes.accompagnement',service_id__in=p.habilitations(compte).filter(tache__in=['social','accueil','gestion']).values('service_id'),dossier_id__in=dossiers(compte).values('pk')).values_list('identifiant',flat=True)


def limite(compte,objet):
    ctx=courant()
    if not p.active() or not ctx or not ctx.reperage:return False
    with perimetre(compte,reperage=False):return not type(objet).objects.filter(pk=objet.pk).exists()


def membres(compte,menage,jour=None):
    from personnes.models import Appartenance
    if menage.pk not in identites(compte,'menage'):raise PermissionDenied
    qs=Appartenance._base_manager.filter(menage=menage)
    if jour:qs=qs.filter(p.periode(jour))
    return set(qs.values_list('personne_id',flat=True))


def menages_correspondants(compte,mot):
    from personnes.models import Personne,Appartenance
    ctx=courant()
    if not p.active() or not ctx or not ctx.reperage or ctx.statistiques or ctx.export_demande:return []
    ids=Personne._base_manager.filter(pk__in=identites(compte,'personne')).filter(Q(designation__icontains=mot)|Q(prenom__icontains=mot)).values('pk')
    return list(Appartenance._base_manager.filter(menage_id__in=dossiers(compte).values('menage_id'),personne_id__in=ids).values_list('menage_id',flat=True))


def reserver_menage(compte,objet,menage,revision):
    from personnes.models import Menage
    ctx=courant()
    if not p.active() or not ctx or ctx.creation!='prise' or not ctx.reperage:return False
    with perimetre(compte,reperage=False):
        if Menage.objects.filter(pk=menage.pk).exists():return False
    if menage.pk not in identites(compte,'menage'):raise PermissionDenied
    if objet._meta.model_name=='menage' and objet.pk!=menage.pk:raise PermissionDenied
    if objet._meta.model_name=='personne' and objet.pk not in membres(compte,menage):raise PermissionDenied
    if not p.habilitations(compte).filter(service_id=ctx.service_id,tache='social').exists():raise PermissionDenied
    if revision is None or Menage._base_manager.filter(pk=menage.pk,revision=revision).update(revision=F('revision')+1)!=1:raise s.Conflit('Le ménage a changé. Rechargez avant de confirmer.')
    DossierService.objects.get_or_create(service_id=ctx.service_id,menage=menage,defaults={'cree_par':compte})
    return True


def reserver_prise(prise,revision=None):
    from personnes.models import Accompagnement
    ctx=courant()
    if not ctx or not p.active() or ctx.creation!='prestation' or ctx.reperage!='prestation':return None
    with perimetre(ctx.compte,reperage=False):
        if Accompagnement.objects.filter(pk=prise.pk).exists():return None
    if str(prise.pk) not in {str(x) for x in prises(ctx.compte)}:raise PermissionDenied
    origine=PorteeObjet.objects.get(modele=prise._meta.label_lower,identifiant=str(prise.pk))
    if origine.service_id!=ctx.service_id:raise PermissionDenied('Choisissez le service de cette prise en charge.')
    # Seul le compteur technique est réservé ; aucune modification de contenu.
    qs=Accompagnement._base_manager.filter(pk=prise.pk)
    if revision is not None:qs=qs.filter(revision_sociale=revision)
    if qs.update(revision_sociale=F('revision_sociale')+1)!=1:raise s.Conflit('La prise a changé. Rechargez avant de confirmer.')
    return Accompagnement.objects.get(pk=prise.pk)


def disponibles(compte,dossier):return p.habilitations(compte).filter(service=dossier.service,tache='social').exists()


def page(request,objet,nature):
    from django.shortcuts import render
    from personnes.models import TypeAide
    lignes=[]
    for ds in equipes(request.user,nature,objet.pk):
        lignes.append({'dossier':ds,'responsables':s.responsables(ds,ds).select_related('professionnel'),
            'demande':ds.demandes_rattachement.filter(demandeur=request.user,etat='attente').first(),'demander':disponibles(request.user,ds)})
    with perimetre(request.user,reperage='prestation'):periodes=list(objet.accompagnements.all().order_by('-debut'))
    return render(request,'acteurs/identite.html',{'objet':objet,'nature':nature,'equipes':lignes,'periodes':periodes,
        'nouvelle_prise':p.habilitations(request.user).filter(service_id=courant().service_id,tache='social').exists(),
        'aides':TypeAide.NATURES if request.user.has_perm('personnes.add_accordaide') else [],
        'nouveau_hebergement':request.user.has_perm('personnes.add_accordhebergement'),'nouveau_repas':request.user.has_perm('personnes.add_accordrepas')})


@transaction.atomic
def demander(compte,dossier):
    if not p.active() or not dossiers(compte).filter(pk=dossier.pk).exists() or not disponibles(compte,dossier):raise PermissionDenied
    DossierService.objects.filter(pk=dossier.pk).update(revision=F('revision')+1);dossier.refresh_from_db()
    if p.missions(compte).filter(dossier=dossier,prise__isnull=True,hebergement__isnull=True,repas__isnull=True,aide__isnull=True).exists():raise ValidationError('Vous faites déjà partie de ce suivi.')
    demande,_=DemandeRattachement.objects.get_or_create(dossier=dossier,demandeur=compte,etat='attente',defaults={'professionnel_id':p.professionnel(compte)})
    return demande


@transaction.atomic
def decider(compte,demande,accepter,attendu,attendu_dossier):
    dossier=demande.dossier
    if not p.active() or not s.peut_attribuer(compte,dossier,dossier):raise PermissionDenied
    s.reserver(demande,attendu)
    if demande.etat!='attente':raise s.Conflit('Cette demande a déjà reçu une réponse.')
    if accepter:
        if not dossiers(demande.demandeur).filter(pk=dossier.pk).exists() or not disponibles(demande.demandeur,dossier) or p.professionnel(demande.demandeur)!=demande.professionnel_id:raise ValidationError('Cette personne n’a plus les tâches autorisées dans ce service. Aucune attribution effectuée.')
        s.ajouter_responsabilite(compte,dossier,dossier,demande.professionnel,timezone.localdate(),'suivi',attendu_dossier)
    else:s.reserver(dossier,attendu_dossier)
    demande.etat='acceptee' if accepter else 'refusee';demande.decide_par=compte;demande.decide_le=timezone.now();demande.save(update_fields=['etat','decide_par','decide_le'])
    s.journal(compte,dossier.service,'demande_rattachement',{'demande':demande.pk},{'etat':demande.etat},dossier)
    return demande
