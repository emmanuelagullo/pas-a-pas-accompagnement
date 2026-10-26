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
    correspondances={'naissance_ville':'ville','naissance_pays':'pays'}
    model=getattr(getattr(form,'_meta',None),'model',None)
    aliases={'RessourcePersonnelle':{'libelle':'nature_ressource'},'DettePersonnelle':{'creancier':'type_creancier'},'CouvertureSociale':{'libelle':'nature_couverture'}}
    if model:correspondances.update(aliases.get(model.__name__,{}))
    noms=[n for n,f in form.fields.items() if correspondances.get(n,n) in dict(PropositionSaisie.CHAMPS)
          and type(f.widget) in (forms.TextInput,PropositionInput)]
    propositions={n:[] for n in noms}
    for x in PropositionSaisie.objects.filter(champ__in=[correspondances.get(n,n) for n in noms],active=True):
        for n in noms:
            if correspondances.get(n,n)==x.champ:propositions[n].append(x.valeur)
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


@register.simple_tag
def separer_precisions(form):
    from copy import copy
    principal, precisions = copy(form), copy(form)
    principaux = {n: f for n, f in form.fields.items() if n not in ('source', 'motif') or f.required}
    secondaires = {n: f for n, f in form.fields.items() if n in ('source', 'motif') and not f.required}
    principal.fields, precisions.fields = principaux, secondaires
    # BoundField cache belongs to the form instance used for rendering.
    principal._bound_fields_cache, precisions._bound_fields_cache = {}, {}
    if form.is_bound:
        from django.forms.utils import ErrorDict
        precisions._errors = ErrorDict({n: e for n, e in form.errors.items() if n in secondaires})
    return {'principal': principal, 'precisions': precisions, 'present': bool(secondaires),
            'erreurs': any(form[n].errors for n in secondaires)}
