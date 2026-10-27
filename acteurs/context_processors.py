from django.urls import reverse
from django.utils import timezone
from .contexte import courant
from . import politique as p, services as s
from .models import Service, DossierService, PorteeObjet, Responsabilite


def acteurs(request):
    ctx=courant()
    if not ctx or not request.user.is_authenticated:return {}
    actif=p.active()
    result={'mode_acces_historique':not actif, 'controle_acteurs':actif, 'portee_statistiques_acteurs':ctx.statistiques}
    if not actif:return result
    hs=p.habilitations(request.user)
    services=Service.objects.filter(pk__in=hs.values('service_id')).select_related('etablissement')
    result.update(services_acteurs=services,service_acteurs=ctx.service_id)
    if ctx.service_id:
        h=hs.filter(service_id=ctx.service_id)
        if h.filter(statistiques_service=True).exists():
            result['rapport_service_acteurs']=reverse('statistiques')+'?rapport=synthese&portee_statistiques=service'
        if h.filter(statistiques_etablissement=True).exists():
            result['rapport_etablissement_acteurs']=reverse('statistiques')+'?rapport=synthese&portee_statistiques=etablissement'
    return result


def bloc(compte,objet,niveau='dossier'):
    if not p.active():return []
    hs=p.habilitations(compte)
    services=hs.values('service_id')
    if niveau=='dossier':
        nom=objet._meta.model_name
        ds=DossierService.objects.filter(service_id__in=services,**{nom:objet})
        if nom=='personne' and not ds.exists():
            from personnes.models import Appartenance
            ds=DossierService.objects.filter(service_id__in=services,menage_id__in=Appartenance.objects.filter(personne=objet).values('menage_id'))
    else:
        ds=DossierService.objects.filter(pk__in=PorteeObjet.objects.filter(modele=objet._meta.label_lower,identifiant=str(objet.pk)).values('dossier_id'),service_id__in=services)
    visibles=p.missions(compte).values('dossier_id')
    from django.db.models import Q
    ds=ds.filter(Q(service_id__in=p.pleines(compte))|Q(pk__in=visibles)|Q(en_attente=True)|Q(service_id__in=hs.filter(tache__in=['accueil','gestion']).values('service_id')))
    lignes=[]
    for d in ds.select_related('service'):
        cible=d if niveau=='dossier' else objet
        rs=list(s.responsables(d,cible).select_related('professionnel'))
        lignes.append({'dossier':d,'responsables':rs,'attendu':s.jeton(d),
            'relais_url':reverse('acteurs:relais_dossier',args=[d.pk]) if niveau=='dossier' else reverse('acteurs:relais_objet',args=[d.pk,niveau,objet.pk]),
            'attribution_url':(reverse('acteurs:attribuer_dossier',args=[d.pk]) if niveau=='dossier' else reverse('acteurs:attribuer_objet',args=[d.pk,niveau,objet.pk])) if s.peut_attribuer(compte,d,cible) else '',
            'peut_reprendre':d.en_attente and hs.filter(service=d.service,tache='social').exists()})
    return lignes
