from django import template
from ..personnalisation_rapports import lien, limite_personnalisation as limite
register=template.Library()


def parametres_courants(context,source):
    request=context['request']
    params=request.GET.dict()
    modele=context.get('modele_actif')
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
