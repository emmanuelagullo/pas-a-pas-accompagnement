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
    from .recherche import FILTRES
    statistiques=request.resolver_match and request.resolver_match.view_name in ('statistiques','dossiers:rapports_accueil')
    from .statistiques import FILTRES as MODES
    defaut=next((k for k,v in MODES.items() if v==ctx.statistiques),'tous')
    filtre=request.GET.get('filtre',defaut)
    result.update(filtres_dossiers_acteurs=FILTRES,filtre_acteurs=filtre if filtre in dict(FILTRES) else 'tous')
    hs=p.habilitations(request.user)
    result['peut_ouvrir_dossiers_acteurs']=hs.exclude(tache='coordination').exists()
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
        corriger=hs.filter(service=d.service,corriger_autrui=True).exists()
        moi=p.professionnel(compte)
        for r in rs:
            r.fin_url=reverse('acteurs:terminer',args=[r.pk]) if r.professionnel_id==moi or corriger else ''
        historique=Responsabilite.objects.filter(dossier=d,**s.selection_cible(d,cible)).filter(Q(fin__lte=timezone.now())|Q(annule_le__isnull=False)).select_related('professionnel').order_by('-debut')[:20]
        personnels=[r for r in rs if r.professionnel_id==moi]
        portee={'dossier':'ce dossier','prise':'cette prise en charge'}.get(niveau,'cette prestation')
        if personnels:
            role=personnels[0].role
            vous=('Vous suivez '+portee if role=='suivi' else
                  'Vous assurez un remplacement sur '+portee if role=='suppleance' else
                  'Vous intervenez ponctuellement sur '+portee)
        elif niveau!='dossier' and p.missions(compte).filter(dossier=d,prise__isnull=True,hebergement__isnull=True,repas__isnull=True,aide__isnull=True).exists():
            vous='Vous suivez le dossier ; aucune mission distincte sur '+portee
        elif p.missions(compte).filter(dossier=d).exists():
            vous='Vous intervenez sur une prise en charge ou une prestation de ce dossier'
        elif hs.filter(service=d.service,tache='accueil').exists():
            vous='Vous assurez l’accueil · '+d.service.libelle
        elif hs.filter(service=d.service,tache='gestion').exists():
            vous='Vous assurez la gestion des prestations · '+d.service.libelle
        else:
            vous='Vous ne faites pas partie de l’équipe de suivi · '+d.service.libelle
        lignes.append({'vous':vous,'portee':portee,'dossier':d,'responsables':rs,'historique':historique,'attendu':s.jeton(d),
            'peut_relayer':any(r.professionnel_id==moi for r in rs) or corriger,
            'peut_prendre':corriger and any(r.professionnel_id!=moi for r in rs),
            'relais_url':reverse('acteurs:relais_dossier',args=[d.pk]) if niveau=='dossier' else reverse('acteurs:relais_objet',args=[d.pk,niveau,objet.pk]),
            'attribution_url':(reverse('acteurs:attribuer_dossier',args=[d.pk]) if niveau=='dossier' else reverse('acteurs:attribuer_objet',args=[d.pk,niveau,objet.pk])) if s.peut_attribuer(compte,d,cible) else '',
            'demandes':d.demandes_rattachement.filter(etat='attente').select_related('professionnel') if niveau=='dossier' and s.peut_attribuer(compte,d,d) else [],
            'demander_url':reverse('acteurs:demander_rattachement',args=[d.pk]) if niveau=='dossier' and d.service.etablissement.reperage_identites and hs.filter(service=d.service,tache='social').exists() and not p.missions(compte).filter(dossier=d,prise__isnull=True,hebergement__isnull=True,repas__isnull=True,aide__isnull=True).exists() and not d.demandes_rattachement.filter(demandeur=compte,etat='attente').exists() else '',
            'peut_reprendre':d.en_attente and hs.filter(service=d.service,tache='social').exists()})
    return lignes
