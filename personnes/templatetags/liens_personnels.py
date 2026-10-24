from django import template
register=template.Library()

@register.simple_tag
def presentation_lien(relation,personne):
    return {'libelle':relation.libelle_depuis(personne),'autre':relation.autre(personne)}
