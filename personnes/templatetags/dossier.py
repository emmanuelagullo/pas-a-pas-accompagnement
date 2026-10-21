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
    if query:
        url += '?' + urlencode(query)
    return url
