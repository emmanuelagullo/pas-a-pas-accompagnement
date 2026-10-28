from django import template
from personnes import aides as service,models as m
register=template.Library()


@register.inclusion_tag('aides/_direct.html',takes_context=True)
def aides_directes(context,prise):
    if not context['request'].user.has_perms(service.LECTURE):return {}
    qs=m.AccordAide.objects.filter(accompagnement=prise).prefetch_related('beneficiaires')
    groupes=[(n,t,list(qs.filter(nature=n))) for n,t in m.TypeAide.NATURES]
    return {'frises_actives': context.get('frises_actives'), 'frises_objets':context.get('frises_objets', {}), 'peut_ajouter':context['request'].user.has_perm('personnes.add_accordaide'),'groupes':groupes,'prise':prise,'request':context['request'],'query': 'contexte_dossier='+__import__('urllib.parse',fromlist=['quote']).quote(prise.navigation.get('contexte_dossier',''))}


@register.inclusion_tag('aides/_jour.html',takes_context=True)
def aides_du_jour(context):
    from django.db.models import Q
    from django.utils import timezone
    if not context['request'].user.has_perms(service.LECTURE):return {}
    date=context.get('date') or timezone.localdate()
    qs=m.AccordAide.objects.filter(annule_le__isnull=True,debut__lte=date,accompagnement__debut__lte=date).filter(Q(fin__isnull=True)|Q(fin__gt=date)).filter(Q(accompagnement__fin__isnull=True)|Q(accompagnement__fin__gt=date)).select_related('accompagnement__menage')
    return {'accords':qs[:80],'date_service':date.isoformat(),'peut_remettre':context['request'].user.has_perm('personnes.add_remiseaide')}


@register.simple_tag
def journaux_c(objet,acteur):
    from datetime import date
    from decimal import Decimal
    from personnes.presentation_dossier_complet import valeur
    from django.utils.dateparse import parse_date,parse_datetime
    noms={'accordrepas':('view_revisionservicerepas',m.AccordRepas),'typeaide':('view_revisiontypeaide',m.TypeAide),'accordaide':('view_revisionaide',m.AccordAide),'lieuhebergement':('view_revisionlieu',m.LieuHebergement),'repasdistribue':('view_revisionrepas',m.RepasDistribue)}
    nom=objet._meta.model_name
    if nom not in noms or not acteur.has_perm('personnes.'+noms[nom][0]):return []
    def etats(xs,j):
        out=[]
        for x in xs:
            modele=m.UsageAide if 'version' in x and nom=='accordaide' else m.RemiseAide if nom=='accordaide' and j.remise_id else noms[nom][1]
            lignes=[]
            for c,v in x.items():
                if c=='id':continue
                if c=='jours_semaine':
                    lignes.append(('Jours autorisés',', '.join(['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'][i] for i in v) if v else 'Tous les jours'));continue
                if c=='beneficiaires':lignes.append(('Personnes concernées',' ; '.join(p.get('libelle','') for p in v)));continue
                if c=='beneficiaire' and isinstance(v,dict):lignes.append(('Personne concernée',v.get('libelle','')));continue
                try:f=modele._meta.get_field(c)
                except Exception:continue
                if isinstance(v,str):
                    if f.get_internal_type()=='DateField':v=parse_date(v)
                    elif f.get_internal_type()=='DateTimeField':v=parse_datetime(v)
                    elif f.get_internal_type()=='DecimalField':v=Decimal(v)
                lignes.append((f.verbose_name,valeur(f,v)))
            out.append(lignes)
        return out
    return [{'revision':j,'avant':etats(j.avant,j),'apres':etats(j.apres,j)} for j in (objet.revisions_service if nom=='accordrepas' else objet.revisions).select_related('auteur')]
