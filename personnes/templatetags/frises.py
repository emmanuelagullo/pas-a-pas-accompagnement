from django import template
register = template.Library()


@register.simple_tag(takes_context=True)
def frise_objet(context, objet):
    if not objet or not context.get('frises_actives'):
        return None
    return context.get('frises_objets', {}).get((objet._meta.model_name, str(objet.pk)))


@register.simple_tag
def cle_frise(objet):
    return objet._meta.model_name + '-' + str(objet.pk) if objet else ''
