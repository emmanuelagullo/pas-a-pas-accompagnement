"""Projection des mêmes objets/critères, avec colonnes explicitement choisies."""
from django.urls import reverse
from . import exploration as e


def relever(d,selection,acteur):
    from urllib.parse import urlencode
    token=signer_retour(acteur,d)
    cles=[d.get('colonne'+str(i)) for i in range(1,12) if d.get('colonne'+str(i))]
    if not cles:cles=[d['axe'],*([d['croisement']] if d['croisement'] else [])]
    colonnes=[e.DIMENSIONS[c] for c in cles];lignes=[]
    for x in selection:
        cellules=[]
        for c in cles:
            if e.personnelle(c) and x['personnes']:
                valeurs={v for p in x['personnes'] for v in x['_par_personne'][p].get(c,[]) if v not in (None,'')}
            else:valeurs=set(e.valeurs(x,c))
            cellules.append(' ; '.join(sorted(map(str,valeurs))) if valeurs else e.INCONNU)
        population=d['population'];url=None
        if population in ('personnes','menages'):url=reverse('dossiers:detail',args=['personne' if population=='personnes' else 'menage',x['id']])
        elif population=='appels':url=reverse('dossiers:appel115',args=[x['id']])
        elif population=='demandes':url=reverse('dossiers:parcours_element',args=['demandes',x['id']])
        elif x.get('prise') and x['menages']:url=reverse('dossiers:prise',args=['menage',next(iter(x['menages'])),x['prise']])
        elif len(x['personnes'])==1:url=reverse('dossiers:detail',args=['personne',next(iter(x['personnes']))])
        if url:url+='?'+urlencode({'retour_exploration':token})
        type_objet={'personnes':'Personne','menages':'Ménage','prises':'Prise en charge','demandes':'Demande d’accueil','sejours':'Épisode de séjour','accords_hebergement':'Autorisation d’hébergement','accords_repas':'Autorisation de repas','affectations':'Période de lieu','repas':'Distribution de repas','aides':'Remise de prestation','appels':'Appel 115','ressources':'Déclaration de ressource','dettes':'Déclaration de dette','couts':'Composante de coût','imputations':'Imputation'}[population]
        noms=' ; '.join(sorted(x.get('_libelles_personnes',{}).get(p,'') for p in x['personnes']))
        libelle=type_objet+(' — '+noms if noms else ' — bénéficiaire non identifié')
        lignes.append(dict(id=x['id'],date=x['date'],valeurs=cellules,url=url,libelle=libelle))
    return colonnes,lignes


def signer_retour(acteur,d):
    from django.core import signing
    params={k:str(v) if v is not None else '' for k,v in d.items()}
    return signing.dumps({'acteur':str(acteur.pk),'parametres':params},salt='retour-exploration-v1',compress=True)


def retour_verifie(acteur,token):
    from django.core import signing
    from urllib.parse import urlencode
    if not token or len(token)>20000:return None
    try:d=signing.loads(token,salt='retour-exploration-v1',max_age=86400)
    except (signing.BadSignature,TypeError,ValueError):return None
    if not isinstance(d,dict) or d.get('acteur')!=str(acteur.pk):return None
    params=d.get('parametres')
    if not isinstance(params,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in params.items()):return None
    return reverse('dossiers:explorer')+'?'+urlencode(params)
