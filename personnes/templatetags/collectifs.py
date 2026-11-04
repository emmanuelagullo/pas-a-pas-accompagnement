from urllib.parse import urlencode
from django import template
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone
from personnes import collectifs as c, models as m
from personnes import vues_collectifs as vues

register=template.Library()

def lien(request,action,pk='',nature=''):
    query=request.GET.copy()
    for k in ('col_action','col_pk','col_nature'):query.pop(k,None)
    query['col_action']=action
    if pk:query['col_pk']=str(pk)
    if nature:query['col_nature']=nature
    return request.path+'?'+query.urlencode()+'#collectif-form'

@register.simple_tag(takes_context=True)
def profil_collectif(context):
    objet=context.get('prise') or context.get('objet')
    if not isinstance(objet,(m.Menage,m.Accompagnement)):return None
    return c.profil(objet)

@register.inclusion_tag('collectifs/social.html',takes_context=True)
def social_collectif(context):
    request=context['request'];objet=context.get('prise') or context.get('objet');cfg=c.profil(objet)
    if not cfg or not request.user.has_perm('personnes.view_compositioncollective'):return {}
    jour=context.get('condition_jour') or timezone.localdate();comp=c.composition(objet,jour)
    formctx=None
    if request.GET.get('col_action')=='composition':
        try:formctx=vues.preparer(request,objet,'composition')
        except (PermissionDenied,ValidationError):pass
    nombres=c.effectifs(comp,jour) if comp else {}
    labels={x['code']:x['libelle'] for x in comp.categories} if comp else {}
    labels['inconnu']='Âge non précisé'
    return {'cfg':cfg,'comp':comp,'effectifs':[(labels[k],n) for k,n in nombres.items()],
        'formctx':formctx,'url':lien(request,'composition') if request.user.has_perm('personnes.add_compositioncollective') else '',
        'histoires':m.CompositionCollective.objects.filter(menage=comp.menage,service=comp.service,accompagnement=comp.accompagnement).order_by('-debut','-pk') if comp else [],'request':request}

@register.inclusion_tag('collectifs/prestations.html',takes_context=True)
def prestations_collectives(context):
    request=context['request'];prise=context.get('prise')
    if not prise:return {}
    cfg=c.profil(prise)
    if not cfg or not request.user.has_perms(['personnes.view_prestationcollective','personnes.view_versionprestationcollective','personnes.view_couvertcollectif']):return {}
    cartes=[]
    for p in prise.prestations_collectives.all():
        v=p.courante
        if not v:continue
        actions=[]
        if v.action!='annulation' and request.user.has_perm('personnes.change_prestationcollective'):
            actions=[('correction','Corriger'),('prolongation','Prolonger'),('annulation','Annuler')]
            if p.nature=='restauration' and not v.fin:actions.insert(1,('depart','Terminer'))
            if p.nature=='hebergement' and v.arrivee and not v.fin:
                actions.insert(1,('depart','Enregistrer le départ'))
                if request.user.has_perm('personnes.add_mouvementcollectif'):actions.extend([('lieu','Changer de lieu'),('absence','Absence')])
                if request.user.has_perm('personnes.change_mouvementcollectif'):actions.extend([('retour','Retour d’absence'),('annuler_mouvement','Annuler un mouvement')])
        cartes.append({'p':p,'v':v,'nombre':sum(c.effectifs(v.composition,v.composition.debut).values()),'actions':[(l,lien(request,a,p.pk)) for a,l in actions],
            'mouvements':p.mouvements.all() if request.user.has_perm('personnes.view_mouvementcollectif') else [],
            'versions':p.versions.all()})
    formctx=None
    action=request.GET.get('col_action','')
    if action and action!='composition':
        try:formctx=vues.preparer(request,prise,action,request.GET.get('col_pk'),request.GET.get('col_nature'))
        except ValidationError as e:formctx={'erreur':' '.join(e.messages)}
    return {'cfg':cfg,'cartes':cartes,'formctx':formctx,'prise':prise,'request':request,
        'nouveaux':[(lib,lien(request,'creation',nature=n)) for n,lib in m.PrestationCollective.NATURES if cfg[n]!='individuel'] if request.user.has_perm('personnes.add_prestationcollective') else [],
        'bilan_url':reverse('dossiers:collectif_bilan',args=[prise.pk])}
