"""Signaux internes regroupés ; un signal ne vaut jamais autorisation."""
from django.apps import apps
from django.db import transaction
from django.db.models import F,Q
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from . import politique as p,services as s
from .models import Notification,Responsabilite,LienCompteProfessionnel,PorteeObjet,DemandeRattachement
from .contexte import perimetre

PRESTATIONS={'accordhebergement','accordrepas','accordaide'}
SUIVI={'personne','menage','accompagnement','situationpersonnelle','situationsociale','commentairedossier',
    'coordonneespersonnelles','declarationfamiliale','complementidentite','relationpersonnelle',
    'situationadministrative','ressourcepersonnelle','dettepersonnelle','pieceadministrative',
    'couverturesociale','protectionjuridique','notepartagee','informationsaccompagnement','bilansocial','evenementsocial'}


def emettre(auteur,compte,dossier,nature,cle,origine=None,responsabilite=None):
    if compte.pk==auteur.pk or not compte.is_active or not p.habilitations(compte).filter(service=dossier.service).exists():return
    x,cree=Notification.objects.get_or_create(compte=compte,dossier=dossier,cle=cle,defaults={'nature':nature,'origine':origine,'responsabilite':responsabilite})
    if not cree:Notification.objects.filter(pk=x.pk).update(modifie_le=timezone.now(),lu_le=None,occurrences=F('occurrences')+1,revision=F('revision')+1)
    return x


def attribution(sender,instance,created,raw=False,**kwargs):
    if sender is not Responsabilite or raw or not created or not p.active():return
    x=instance;cible=x.cible
    origine=PorteeObjet.objects.filter(modele=cible._meta.label_lower,identifiant=str(cible.pk)).first() if cible is not x.dossier else None
    for lien in LienCompteProfessionnel.objects.filter(professionnel_id=x.professionnel_id).select_related('compte'):
        emettre(x.cree_par,lien.compte,x.dossier,'attribution','attribution:'+str(x.pk),origine,x)


def equipe(dossier,origine=None):
    condition=Q(prise__isnull=True,hebergement__isnull=True,repas__isnull=True,aide__isnull=True)
    if origine and origine.prise_id:condition|=Q(prise_id=origine.prise_id)
    rs=Responsabilite.objects.filter(p.periode(timezone.now()),annule_le__isnull=True,dossier=dossier).filter(condition)
    return LienCompteProfessionnel.objects.filter(professionnel_id__in=rs.values('professionnel_id')).select_related('compte')


def saisie(auteur,objet,creation):
    nom=objet._meta.model_name
    if not p.active() or nom not in PRESTATIONS|SUIVI or (nom in PRESTATIONS and not creation):return
    origine=PorteeObjet.objects.filter(modele=objet._meta.label_lower,identifiant=str(objet.pk)).select_related('dossier').first()
    if not origine or not origine.dossier_id:return
    nature='prestation' if nom in PRESTATIONS else 'modification'
    for lien in equipe(origine.dossier,origine):emettre(auteur,lien.compte,origine.dossier,nature,'fait:'+objet._meta.label_lower+':'+str(objet.pk),origine)


def demande(auteur,dossier,pk):
    for lien in equipe(dossier):emettre(auteur,lien.compte,dossier,'demande','demande:'+str(pk))


def visibles(compte):
    if not p.active() or not compte.is_active:return []
    # Un contexte de totaux statistiques ne doit jamais élargir les signaux.
    with perimetre(compte,statistiques='accessibles',reperage=False,export_demande=False):
        hs=p.habilitations(compte)
        xs=Notification.objects.filter(compte=compte,dossier__service_id__in=hs.values('service_id')).select_related('dossier__personne','dossier__menage','origine','responsabilite').order_by('-modifie_le','-pk')
        pleins=set(hs.filter(tache='social',service__politique__in=['collectif','lecture']).values_list('service_id',flat=True))
        missions=p.missions(compte)
        suivis=set(missions.filter(prise__isnull=True,hebergement__isnull=True,repas__isnull=True,aide__isnull=True).values_list('dossier_id',flat=True))
        courantes=set(missions.values_list('pk',flat=True))
        demandes={'demande:'+str(pk) for pk in DemandeRattachement.objects.filter(etat='attente',dossier__service_id__in=hs.values('service_id')).values_list('pk',flat=True)}
        lectures={};resultat=[]
        for x in xs:
            if x.nature=='demande' and x.cle not in demandes:continue
            o=x.origine
            if o:
                if o.modele not in lectures:
                    try:model=apps.get_model(o.modele)
                    except (LookupError,ValueError):continue
                    lectures[o.modele]=set(p.portees(compte,model).filter(modele=o.modele).values_list('pk',flat=True)) if compte.has_perm(model._meta.app_label+'.view_'+model._meta.model_name) else set()
                autorise=o.pk in lectures[o.modele]
            else:
                racine=x.dossier.personne or x.dossier.menage
                model=type(racine)
                autorise=(x.dossier.service_id in pleins or x.dossier_id in suivis) and compte.has_perm(model._meta.app_label+'.view_'+model._meta.model_name) and model.objects.filter(pk=racine.pk).exists()
            if not autorise:continue
            if x.responsabilite_id and x.responsabilite_id not in courantes and x.dossier.service_id not in pleins:continue
            ds=x.dossier;nature='personne' if ds.personne_id else 'menage';pk=ds.personne_id or ds.menage_id
            x.url=reverse('dossiers:prise',args=[nature,pk,o.prise_id]) if o and o.prise_id else reverse('dossiers:detail',args=[nature,pk])
            x.attendu=s.jeton(x);resultat.append(x)
        return resultat


@transaction.atomic
def lire(compte,pk,attendu):
    x=next((x for x in visibles(compte) if x.pk==pk),None)
    if x is None:raise PermissionDenied
    s.reserver(x,attendu);x.lu_le=timezone.now();x.save(update_fields=['lu_le'])
    return x
