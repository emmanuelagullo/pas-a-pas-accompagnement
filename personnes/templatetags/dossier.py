from urllib.parse import urlencode
from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def dossier_url(context, nom, *args, **query):
    url = reverse(nom, args=args)
    token = context.get('contexte_dossier')
    if token:
        query['contexte_dossier'] = token
    request=context.get('request')
    retour_stats=request.GET.get('retour_exploration') if request else None
    if retour_stats:query['retour_exploration']=retour_stats
    if query:
        url += '?' + urlencode(query)
    return url
