from django import template
from django.utils.safestring import mark_safe
from personnes import prestation_navigation as nav
register = template.Library()

@register.simple_tag(takes_context=True)
def prestation_ouvrir(context, genre, pk):
    return nav.adresse(context.get('prestation_cadre') or context, str(genre)+':'+str(pk))

@register.simple_tag(takes_context=True)
def prestation_imprimer(context, genre, pk):
    return nav.adresse(context.get('prestation_cadre') or context, str(genre)+':'+str(pk), impression=True)

@register.simple_tag(takes_context=True)
def prestation_hote(context, genre, pk):
    cle = str(genre)+':'+str(pk)
    contenu = context.get('prestation_panneau','') if context.get('prestation_ouverte') == cle else ''
    from django.utils.html import format_html
    return format_html('<div id="prestation-hebergement-{}" class="prestation-hote" data-prestation-hote="{}">{}</div>',pk,cle,contenu) if genre == 'hebergement' else format_html('<div class="prestation-hote" data-prestation-hote="{}">{}</div>',cle,contenu)

class Locales(template.Node):
    def __init__(self, corps): self.corps=corps
    def render(self, context): return nav.localiser(self.corps.render(context), context)

@register.tag
def prestations_locales(parser, token):
    corps=parser.parse(('endprestations_locales',)); parser.delete_first_token()
    return Locales(corps)

@register.simple_tag(takes_context=True)
def prestation_frise(context, url):
    if not context.get('prise') or not context.get('parametres_prestations'):
        return {'url':url,'local':False}
    from urllib.parse import urlsplit
    from django.urls import resolve, Resolver404
    from django.core.exceptions import ObjectDoesNotExist
    try:
        cible=nav.resoudre(urlsplit(url).path); nom=cible.view_name; pk=cible.kwargs.get('pk')
        if nom == 'suivi:accord_hebergement':
            fragment=urlsplit(url).fragment
            if fragment.startswith('sejour-'):cle='sejour:'+fragment[7:]
            elif fragment.startswith(('affectation-','absence-')):
                champ='lieux_dossier' if fragment.startswith('affectation-') else 'absences_dossier'
                identifiant=fragment.split('-',1)[1]
                sejour=next(s for s in context['sejours_dossier'] if any(str(x.pk)==identifiant for x in getattr(s,champ,[])))
                cle='sejour:'+str(sejour.pk)
            else:cle='hebergement:'+str(pk)
        elif nom == 'suivi:accord_repas':cle='repas:'+str(pk)
        elif nom == 'dossiers:aide':
            aide=next(a for a in context['prestations_aides_visibles'] if str(a.pk)==str(pk));cle='aide_'+aide.nature+':'+str(pk)
        elif nom=='dossiers:collectif_action':
            from urllib.parse import parse_qsl
            cle='commun:'+dict(parse_qsl(urlsplit(url).query)).get('pk','')
        else:return {'url':url,'local':False}
        nav.cible(context,cle)
        return {'url':nav.adresse(context,cle),'local':True}
    except (Resolver404,nav.Http404,ValueError,LookupError,ObjectDoesNotExist,StopIteration):
        return {'url':url,'local':False}


@register.simple_tag(takes_context=True)
def hebergement_individuels_ouverts(context, groupe):
    cle=context.get('prestation_ouverte','')
    if cle.startswith('hebergement:'):return False
    identifiant=cle[7:] if cle.startswith('sejour:') else context['request'].GET.get('sejour','')
    return any(str(s.pk)==identifiant for s in groupe['sejours'])

@register.simple_tag(takes_context=True)
def preparer_prestations(context):
    from personnes.prestations_presentation import initialiser
    initialiser(context)
    return ''

@register.simple_tag(takes_context=True)
def creation_prestation(context,famille):
    from personnes.prestations_presentation import creation
    return creation(context,famille)

@register.inclusion_tag('dossiers/_prestation_ligne.html',takes_context=True)
def ligne_prestation(context,objet,genre):
    from personnes.prestations_presentation import ligne
    return {**context.flatten(),'ligne':ligne(context,objet,genre)}

@register.inclusion_tag('dossiers/_prestation_actions.html',takes_context=True)
def actions_prestation(context,famille):
    from personnes.prestations_presentation import actions
    return {**context.flatten(),'actions':actions(context,famille)}
