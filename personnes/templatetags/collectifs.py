from urllib.parse import urlencode
from django import template
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone
from personnes import collectifs as c, models as m
from personnes import vues_collectifs as vues
from acteurs.profils_collectifs import defaut

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

@register.simple_tag(takes_context=True)
def social_collectif(context):
    request=context['request'];objet=context.get('prise') or context.get('objet')
    if not isinstance(objet,(m.Menage,m.Accompagnement)):return {}
    cfg=c.profil(objet)
    actif=bool(cfg)
    if not request.user.has_perm('personnes.view_compositioncollective'):return {}
    if not cfg:
        try:service=c.service_objet(objet)
        except ValidationError:return {}
        if not m.CompositionCollective.objects.filter(menage=objet.menage if isinstance(objet,m.Accompagnement) else objet,service=service).exists():return {}
    cfg=cfg or defaut()
    jour=context.get('condition_jour') or timezone.localdate();comp=c.composition(objet,jour)
    formctx=None
    if request.GET.get('col_action')=='composition':
        try:formctx=vues.preparer(request,objet,'composition')
        except (PermissionDenied,ValidationError):pass
    nombres=c.effectifs(comp,jour) if comp else {}
    labels={x['code']:x['libelle'] for x in comp.categories} if comp else {}
    labels['inconnu']='Âge non précisé'
    rubriques = []
    for code, titre, champs in (
        ('coordonnees', 'Coordonnées', ('telephone', 'courriel')),
        ('logement', 'Logement', ('logement',)),
        ('ressources', 'Ressources', ('revenu',)),
        ('dettes', 'Dettes', ('dette',)),
        ('projet', 'Projet du ménage', ('projet',)),
    ):
        if any(champ in cfg['rubriques'] for champ in champs):
            rubriques.append({
                'ancre': 'condition-menage-' + code, 'titre': titre,
                'champs': [(m.CompositionCollective._meta.get_field(champ).verbose_name,
                            getattr(comp, champ, None)) for champ in champs],
                'renseignee': any(getattr(comp, champ, None) not in (None, '') for champ in champs),
            })
    return {'rubriques': rubriques, 'cfg':cfg,'comp':comp,'effectifs':[(labels[k],n) for k,n in nombres.items()],
        'formctx':formctx,'url':lien(request,'composition') if actif and request.user.has_perm('personnes.add_compositioncollective') else '',
        'histoires':m.CompositionCollective.objects.filter(menage=comp.menage,service=comp.service,accompagnement=comp.accompagnement).order_by('-debut','-pk') if comp else [],'request':request}

@register.simple_tag(takes_context=True)
def historique_collectif(context,nature):
    prise=context.get('prise')
    return bool(prise and context['request'].user.has_perm('personnes.view_prestationcollective') and prise.prestations_collectives.filter(nature=nature).exists())

@register.simple_tag(takes_context=True)
def repere_age(context, personne, collectif):
    if not collectif.get('cfg') or not personne.date_naissance or personne.precision_naissance != 'exacte':
        return ''
    age = c.age_exact(personne.date_naissance, context.get('condition_jour') or timezone.localdate())
    return 'Adulte' if age >= 18 else 'Mineur'
