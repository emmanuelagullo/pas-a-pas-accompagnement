"""Cellules vides d'un domaine métier connu, sans observations inventées."""
from itertools import product
from django.core.exceptions import ValidationError
from . import models as m


def completer_repas(d,axes,ventilation):
    from .exploration import accepte
    if d['population']!='repas' or d['mesure'] not in ('quantite','objets','personnes','menages') or any(c and c not in ('mois','type','total') for c in axes):
        raise ValidationError('Les lignes vides concernent les repas, leurs mois/services et des sommes ou effectifs. Désactivez ce choix pour une autre analyse.')
    if d.get('classes') or d.get('classes_croisement') or any(d.get('classes'+str(i)) for i in range(3,8)):
        raise ValidationError('Les mois et services sans distribution ne sont pas des classes numériques.')
    mois=[];jour=d['debut'].replace(day=1)
    while jour<d['fin']:
        mois.append(jour.strftime('%Y-%m'))
        if len(mois)>24:raise ValidationError('Les lignes de repas sans distribution sont limitées à 24 mois.')
        if jour.month==12:jour=jour.replace(year=jour.year+1,month=1)
        else:jour=jour.replace(month=jour.month+1)
    for mois,service in product(mois,[label for _,label in m.AccordRepas.SERVICES]):
        x={'valeurs':{'mois':[mois],'type':[service]}}
        if any(not accepte(x,d.get('filtre'+str(i)),d.get('operation'+str(i)),d.get('valeur'+str(i),''))
               for i in range(1,(d.get('filtres') or 2)+1) if d.get('filtre'+str(i)) in ('mois','type')):continue
        chemin=tuple((mois if c=='mois' else service if c=='type' else 'Ensemble','') for c in axes)
        unite='repas' if d['mesure']=='quantite' else ''
        ventilation.setdefault((*chemin,unite),{})
