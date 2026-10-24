from django import template
from django.db.models import Q
from django.utils import timezone
from personnes import parcours as s
register=template.Library()


@register.simple_tag
def rubriques_parcours(acteur,objet,jour=None):
    out=[]
    jour=jour or timezone.localdate()
    for code,r in s.RUBRIQUES.items():
        if not acteur.has_perms(s.droits(code)):continue
        qs=s.a_date(code,jour).filter(**{'element__'+k:v for k,v in s.cible_q(objet).items()})
        if objet._meta.model_name=='personne':qs=s.a_date(code,jour).filter(Q(element__personne=objet)|Q(element__beneficiaires=objet)).distinct()
        if not acteur.has_perm('personnes.view_menage'):qs=qs.filter(element__menage__isnull=True)
        repere=qs.first() if code=='suivi' else None
        out.append((code,r.titre,qs.count(),repere.get_etat_display() if repere else ''))
    return out


@register.simple_tag
def lecture_rapport_parcours(acteur):
    return any(acteur.has_perms(s.droits(c)) for c in s.RUBRIQUES)


@register.simple_tag
def demandes_resume(acteur,objet,jour=None):
    if not acteur.has_perms(s.droits('demandes')):return []
    qs=s.a_date('demandes',jour or timezone.localdate()).filter(etat__in=['attente','acceptee'],element__accompagnement__isnull=True)
    if objet._meta.model_name=='personne':qs=qs.filter(Q(element__personne=objet)|Q(element__beneficiaires=objet)).distinct()
    else:qs=qs.filter(element__menage=objet)
    if not acteur.has_perm('personnes.view_menage'):qs=qs.filter(element__menage__isnull=True)
    return list(qs.select_related('element__personne','element__menage').order_by('-debut','pk')[:3])
