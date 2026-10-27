from django import template
from acteurs.context_processors import bloc
register=template.Library()

@register.inclusion_tag('acteurs/bloc.html',takes_context=True)
def responsabilites(context,objet,niveau='dossier'):
    from django.core import signing
    from urllib.parse import urlencode
    request=context['request']
    lignes=bloc(request.user,objet,niveau)
    for ligne in lignes:
        token=signing.dumps({'compte':str(request.user.pk),'dossier':str(ligne['dossier'].pk),'url':request.get_full_path()},salt='retour-acteurs-v1',compress=True)
        query='?'+urlencode({'retour_acteurs':token})
        ligne['relais_url']+=query
        if ligne['attribution_url']:ligne['attribution_url']+=query
        ligne['retour_acteurs']=token
    return {'lignes':lignes,'niveau':niveau}


@register.simple_tag(takes_context=True)
def qualification_hebergement(context,accord,lieu,jour):
    from acteurs import politique as p, services as s
    from acteurs.models import PorteeObjet
    if not p.active():return ''
    origine=PorteeObjet.objects.filter(modele=accord._meta.label_lower,identifiant=str(accord.pk)).select_related('service__etablissement__organisme').first()
    if not origine:return 'Non déterminé'
    return s.qualifier_hebergement(origine.service.etablissement,lieu,jour)
