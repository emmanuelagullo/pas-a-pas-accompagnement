"""Règles civiles explicites, recalculées à l'ouverture, fin toujours exclue."""
from datetime import date,timedelta

PERIODES={
 'aujourdhui':"Aujourd’hui",'hier':'Hier','demain':'Demain',
 'semaine':'Semaine en cours, jusqu’à aujourd’hui','semaine_civile':'Semaine civile entière',
 'semaine_precedente':'Semaine précédente',
 'mois':'Mois en cours, jusqu’à aujourd’hui','mois_civil':'Mois civil entier','mois_precedent':'Mois précédent',
 'trimestre':'Trimestre en cours, jusqu’à aujourd’hui','trimestre_civil':'Trimestre civil entier','trimestre_precedent':'Trimestre précédent',
 'annee':'Année en cours, jusqu’à aujourd’hui','annee_civile':'Année civile entière','annee_precedente':'Année précédente',
 'douze_mois':'Douze derniers mois glissants','sept_jours':'Sept derniers jours, aujourd’hui inclus',
 'trente_jours':'Trente derniers jours, aujourd’hui inclus','jours_relatifs':'Autres bornes en jours relatifs','date_relative':'Autre date relative',
}


def mois_suivant(jour,n=1):
    v=jour.year*12+jour.month-1+n
    return date(v//12,v%12+1,1)


def bornes_periode(code,aujourd_hui,*,decalage_debut=-6,decalage_fin=1):
    lendemain=aujourd_hui+timedelta(days=1);mois=aujourd_hui.replace(day=1)
    semaine=aujourd_hui-timedelta(days=aujourd_hui.weekday())
    trimestre=date(aujourd_hui.year,3*((aujourd_hui.month-1)//3)+1,1)
    fixes={'aujourdhui':(aujourd_hui,lendemain),'hier':(aujourd_hui-timedelta(days=1),aujourd_hui),'demain':(lendemain,lendemain+timedelta(days=1)),
      'semaine':(semaine,lendemain),'semaine_civile':(semaine,semaine+timedelta(days=7)), 'semaine_precedente':(semaine-timedelta(days=7),semaine),
      'mois':(mois,lendemain),'mois_civil':(mois,mois_suivant(mois)),'mois_precedent':(mois_suivant(mois,-1),mois),
      'trimestre':(trimestre,lendemain),'trimestre_civil':(trimestre,mois_suivant(trimestre,3)),'trimestre_precedent':(mois_suivant(trimestre,-3),trimestre),
      'annee':(date(aujourd_hui.year,1,1),lendemain),'annee_civile':(date(aujourd_hui.year,1,1),date(aujourd_hui.year+1,1,1)),
      'annee_precedente':(date(aujourd_hui.year-1,1,1),date(aujourd_hui.year,1,1)),
      # Compatibilité exacte de l'ancienne règle (mois civils jusqu'à aujourd'hui).
      'douze_mois':(mois_suivant(mois,-11),lendemain),
      'sept_jours':(aujourd_hui-timedelta(days=6),lendemain),'trente_jours':(aujourd_hui-timedelta(days=29),lendemain)}
    if code in ('jours_relatifs','date_relative'):
        a=int(decalage_debut if decalage_debut not in (None,'') else -6);b=a+1 if code=='date_relative' else int(decalage_fin if decalage_fin not in (None,'') else 1)
        if not -36600<=a<b<=36601:raise ValueError('Les bornes relatives doivent être ordonnées, entre −36600 et +36600 jours.')
        return aujourd_hui+timedelta(days=a),aujourd_hui+timedelta(days=b)
    if code not in fixes:raise ValueError('Période relative inconnue.')
    return fixes[code]


def resoudre(params,jour=None):
    from django.utils import timezone
    p=params.copy()
    if p.get('periode'):
        a,b=bornes_periode(p['periode'],jour or timezone.localdate(),decalage_debut=p.get('decalage_debut',-6),decalage_fin=p.get('decalage_fin',1))
        p.update(debut=a.isoformat(),fin=b.isoformat(),reference=(b-timedelta(days=1)).isoformat())
        if 'date' in p:p['date']=p['reference']
    return p


def suggerer(params,jour):
    """Une proposition seulement : elle reste affichée et confirmée par la personne."""
    if params.get('periode'):return params['periode']
    if 'date' in params and 'debut' not in params:
        try:ecart=(date.fromisoformat(str(params['date']))-jour).days
        except (ValueError,TypeError):return ''
        return {0:'aujourdhui',-1:'hier',1:'demain'}.get(ecart,'date_relative' if abs(ecart)<=7 else '')
    try:a=date.fromisoformat(str(params['debut']));b=date.fromisoformat(str(params['fin']))
    except (KeyError,ValueError,TypeError):return ''
    for code in ('aujourdhui','hier','demain','mois','mois_precedent','semaine','semaine_precedente','annee','annee_precedente','mois_civil','semaine_civile','sept_jours','trente_jours'):
        if (a,b)==bornes_periode(code,jour):return code
    return '' # Une période historique arbitraire reste fixe par défaut.
