from django import template
from .. import dossier_complet as s
register=template.Library()

@register.simple_tag
def rapport_a_autorise(acteur):
    return acteur.has_perms(s.ADMIN_LECTURE) or any(acteur.has_perms(s.droits_lecture(c)) for c in s.RUBRIQUES)
