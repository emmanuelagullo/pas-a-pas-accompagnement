"""Un ordre stable et sans doublon sur la seule population déjà autorisée."""
from collections import defaultdict
from django.utils import timezone
from personnes import models as m
from . import politique as p
from .models import DossierService, Service

FILTRES=[('tous','Tous'),('mes','Mes dossiers'),('service','Mon service'),('attente','En attente')]
LIBELLES={0:'En attente',1:'Mes dossiers',2:'Service',3:'Établissement',4:'Autres dossiers accessibles'}


def classer(compte,objets,nature,filtre='tous',service=None):
    population=list(objets)
    ids=[x.pk for x in population]
    from django.db.models import Q
    from . import reperage
    ds=list(DossierService.objects.filter(Q(service_id__in=p.habilitations(compte).values('service_id'))|Q(pk__in=reperage.dossiers(compte).values('pk')),
        **{nature+'_id__in':ids}).select_related('service'))
    propres=set(p.missions(compte).values_list('dossier_id',flat=True))
    par_objet=defaultdict(list)
    for d in ds:par_objet[getattr(d,nature+'_id')].append(d)
    prises=m.Accompagnement.objects.filter(**({'menage_id__in':ids} if nature=='menage' else {'beneficiaires__pk__in':ids})).distinct().prefetch_related('beneficiaires')
    periodes=defaultdict(list)
    for a in prises:
        cibles=[a.menage_id] if nature=='menage' else [x.pk for x in a.beneficiaires.all()]
        for identifiant in cibles:periodes[identifiant].append(a)
    etablissement=Service.objects.filter(pk=service).values_list("etablissement_id",flat=True).first() if service else None
    resultat=[]
    for x in population:
        liens=par_objet[x.pk]
        # Une identité d'un membre peut être visible par le dossier du ménage.
        if nature=='personne' and not liens:
            menages=m.Appartenance.objects.filter(personne=x).values_list('menage_id',flat=True)
            liens=list(DossierService.objects.filter(menage_id__in=menages,service_id__in=p.habilitations(compte).values('service_id')).select_related('service'))
        attente=any(d.en_attente for d in liens)
        moi=any(d.pk in propres for d in liens)
        du_service=any(service is None or d.service_id==service for d in liens)
        if filtre=='attente' and not attente or filtre=='mes' and not moi or filtre=='service' and not du_service:continue
        du_etablissement=etablissement is not None and any(d.service.etablissement_id==etablissement for d in liens)
        groupe=0 if attente else 1 if moi else 2 if du_service else 3 if du_etablissement else 4
        x.acteur_groupe=LIBELLES[groupe]
        actifs=any(a.debut<=timezone.localdate() and (not a.fin or a.fin>timezone.localdate()) for a in periodes[x.pk])
        fins=[a.fin.toordinal() for a in periodes[x.pk] if a.fin]
        creation=getattr(x,'cree_le',None)
        x.ordre_acteurs=(groupe,0 if actifs else 1,0 if actifs else -max(fins,default=0),-creation.timestamp() if creation else 0,str(x.pk))
        resultat.append(x)
    return sorted(resultat,key=lambda x:x.ordre_acteurs)
