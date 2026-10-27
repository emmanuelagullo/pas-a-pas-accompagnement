from django import template
from django.core.exceptions import PermissionDenied
from ..personnalisation_rapports import lien, limite_personnalisation as limite
register=template.Library()


def parametres_courants(context,source):
    request=context['request']
    params=request.GET.dict()
    modele=context.get('modele_actif') or context.get('modele_gestion') or context.get('rapport_cible') or context.get('modele_cible')
    if modele:params=modele.parametres.copy()
    form=context.get('form') or context.get('formulaire')
    if form and form.is_bound:params.update({k:v for k,v in form.data.items()})
    if source=='statistiques':
        params.update(rapport=context.get('rapport','synthese'),service=context.get('service_choisi',''),
                      lieu=context.get('lieu_choisi',''),regroupement=context.get('regroupement','mois_categorie'))
    return params


@register.simple_tag(takes_context=True)
def personnaliser_rapport(context,source):
    return lien(source,parametres_courants(context,source))


@register.simple_tag(takes_context=True)
def limite_personnalisation(context,source):
    return limite(source,parametres_courants(context,source))


@register.simple_tag(takes_context=True)
def deriver_rapport(context,source):
    from django.urls import reverse
    from urllib.parse import urlencode
    params=parametres_courants(context,source)
    cible=context.get('rapport_cible') or context.get('modele_gestion')
    if cible:
        from ..modeles_personnels import jeton
        params.update(modele_cible=str(cible.pk),attendu_modele=context.get('attendu_rapport') or context.get('attendu_modele') or jeton(context['request'].user,cible))
    return reverse('dossiers:rapport_composer',args=[source])+'?'+urlencode({k:v for k,v in params.items() if k not in ('modele','format','page')})


@register.simple_tag(takes_context=True)
def lien_rapport(context,url,source,**query):
    from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
    from ..exploration_releve import signer_retour
    from ..catalogue_rapports import SOURCES
    if source not in SOURCES:return url
    params=parametres_courants(context,source)
    params={k:v for k,v in params.items() if k not in ('format','retour_exploration')}
    params.update(_source_rapport=source,_editeur_rapport='1' if context.get('composition_source') else '')
    params['page']=str(context['page_obj'].number) if context.get('page_obj') is not None else context['request'].GET.get('page','1')
    cible=context.get('rapport_cible') or context.get('modele_gestion')
    if cible:params.update(modele_cible=str(cible.pk),attendu_modele=context.get('attendu_rapport') or context.get('attendu_modele',''))
    token=signer_retour(context['request'].user,params)
    u=urlsplit(url);p=dict(parse_qsl(u.query,keep_blank_values=True));p.update(query,retour_exploration=token)
    return urlunsplit((u.scheme,u.netloc,u.path,urlencode(p),u.fragment))


@register.simple_tag(takes_context=True)
def retour_statistiques(context):
    from ..exploration_releve import retour_verifie
    request=context.get('request')
    if request is None or not getattr(request,'user',None) or not request.user.is_authenticated:return None
    valeurs=context.get('dossier_valeurs') or {}
    token=request.GET.get('retour_exploration') or request.POST.get('retour_exploration') or valeurs.get('retour_exploration') or (valeurs.get('vue') or {}).get('retour_exploration')
    return retour_verifie(request.user,token)


@register.simple_tag(takes_context=True)
def composition_fidele(context,source):
    """Proposer uniquement une traduction validée avec les critères courants."""
    from django.core.exceptions import ValidationError,PermissionDenied
    from django.http import Http404
    from ..personnalisation_rapports import adapter
    if not context['request'].user.has_perm('personnes.view_personne'):return ''
    params=parametres_courants(context,source)
    try:adapter(context['request'].user,source,params)
    except (ValidationError,PermissionDenied,Http404,ValueError,TypeError):return ''
    return lien(source,params)


@register.simple_tag(takes_context=True)
def conserver_reglages(context,source):
    from django.core import signing
    from django.urls import reverse
    from urllib.parse import urlencode
    params=parametres_courants(context,source)
    params={k:str(v) if v is not None else '' for k,v in params.items() if k not in ('format','page','modele','modele_cible','attendu_modele','csrfmiddlewaretoken')}
    if source not in ('exploration','statistiques'):
        f=context.get('form') or context.get('formulaire')
        if f is not None:params={k:v for k,v in params.items() if k in set(f.fields)|{'periode','decalage_debut','decalage_fin','personne','menage','export_prioritaire'}}
    if source=='exploration':params.update(schema=1,exploration=True)
    elif source!='statistiques':params['_rapport_source']=source
    cible=context.get('rapport_cible') or context.get('modele_gestion') or context.get('modele_cible') or context.get('modele_actif')
    from ..modeles_personnels import jeton,etat
    attendu=context.get('attendu_rapport') or context.get('attendu_modele')
    if cible and not attendu:
        try:attendu=jeton(context['request'].user,cible)
        except PermissionDenied:attendu=''
    payload=dict(acteur=str(context['request'].user.pk),source=source,parametres=params,cible=cible.pk if cible else None,attendu=attendu,base=cible.parametres.copy() if cible else None,empreinte_base=(cible.empreinte_source if cible.nature=='personnalisation' else etat(cible)) if cible else '',nom_saisi=context.get('nom_rapport') or context.get('nom_modele_saisi') or '',editeur=bool(context.get('composition_source')),page=str(context['page_obj'].number) if context.get('page_obj') is not None else '1')
    token=signing.dumps(payload,salt='reglages-rapport-v1',compress=True)
    return reverse('dossiers:rapport_conserver')+'?'+urlencode({'definition':token})


@register.simple_tag
def definition_export(url):
    from urllib.parse import urlsplit,parse_qs
    return parse_qs(urlsplit(url).query).get('definition',[''])[0]


@register.simple_tag(takes_context=True)
def peut_conserver_reglages(context,source):
    from ..vues_rapports import peut_stockage
    acteur=context['request'].user
    return acteur.has_perms(['personnes.view_modelerapport','personnes.add_modelerapport']) if source=='exploration' else peut_stockage(acteur,source)


@register.simple_tag(takes_context=True)
def export_prioritaire(context,source):
    from ..presentation_exports import prioritaire
    return prioritaire(source,parametres_courants(context,source))


@register.simple_tag(takes_context=True)
def preference_export(context):
    return parametres_courants(context,context.get('composition_source','')).get('export_prioritaire','')
