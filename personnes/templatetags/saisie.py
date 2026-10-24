import re
from django import forms, template
from ..champs_saisie import adapter, PropositionInput
from ..models import PropositionSaisie
register=template.Library()


@register.simple_tag
def adapter_saisie(form, acteur):
    if not hasattr(form, 'fields'):return ''
    adapter(form)
    if not acteur.has_perm('personnes.view_propositionsaisie'):return ''
    noms=[n for n,f in form.fields.items() if n in dict(PropositionSaisie.CHAMPS)
          and type(f.widget) in (forms.TextInput,PropositionInput)]
    propositions={n:[] for n in noms}
    for x in PropositionSaisie.objects.filter(champ__in=noms,active=True):
        propositions[x.champ].append(x.valeur)
    for n in noms:
        if propositions[n]:form.fields[n].widget=PropositionInput(attrs=form.fields[n].widget.attrs,propositions=propositions[n])
    return ''


@register.filter
def telephone_lien(valeur):
    # Un ancien champ peut contenir plusieurs numéros ou une consigne : dans ce
    # cas garder le texte, sans fabriquer une destination d'appel.
    compact=re.sub(r'[\s().-]', '', str(valeur))
    return compact if re.fullmatch(r'\+?\d{5,20}',compact) else ''


@register.filter
def courriel_lien(valeur):
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    from urllib.parse import quote
    try:validate_email(valeur)
    except (ValidationError,TypeError):return ''
    return quote(valeur, safe='@')
