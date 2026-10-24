from django import template
from django.core import signing
from .. import bd6
register=template.Library()
@register.simple_tag
def jeton_action(action):return signing.dumps([action._meta.model_name,str(action.pk),action.revision_sociale],salt=bd6.SEL)
