from acteurs.contexte import service_metier
"""Projection des mêmes objets/critères, avec colonnes explicitement choisies."""
from django.urls import reverse
from . import exploration as e


def cles_colonnes(d):
    cles=[d.get('colonne'+str(i)) for i in range(1,12) if d.get('colonne'+str(i))]
    return cles or [d['axe'],*([d['croisement']] if d['croisement'] else [])]


@service_metier
def relever(d,selection,acteur,*,liens=True):
    from urllib.parse import urlencode
    token=signer_retour(acteur,d) if liens else ''
    from . import models as m
    modeles={'sejours':m.Sejour,'fragments_sejour':m.Sejour,'affectations':m.Affectation,'repas':m.RepasDistribue,'aides':m.RemiseAide,'couts':m.LigneCout,'imputations':m.ImputationFinancement}
    objets={}
    if liens and d['population'] in modeles:
        qs=modeles[d['population']].objects.filter(pk__in=[x['id'] for x in selection])
        if d['population']=='affectations':qs=qs.select_related('sejour')
        if d['population'] in ('couts','imputations'):qs=qs.select_related('version__financement')
        objets={str(x.pk):x for x in qs}
        if set(objets)!={x['id'] for x in selection}:
            from django.core.exceptions import ValidationError
            raise ValidationError('Les faits ont changé pendant le calcul ; recalculez le rapport.')
    cles=cles_colonnes(d)
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
        elif population=='relations':
            relation=m.RelationPersonnelle.objects.get(pk=x['id']);url=reverse('dossiers:relations_personnelles',args=[relation.personne_a_id])
        elif population=='demandes':url=reverse('dossiers:parcours_element',args=['demandes',x['id']])
        elif x.get('prise') and x['menages']:url=reverse('dossiers:prise',args=['menage',next(iter(x['menages'])),x['prise']])
        elif len(x['personnes'])==1:url=reverse('dossiers:detail',args=['personne',next(iter(x['personnes']))])
        fragment=('relation-'+x['id']) if population=='relations' else '';query={}
        if not liens:pass
        elif population=='accords_hebergement':url=reverse('suivi:accord_hebergement',args=[x['id']])
        elif population=='accords_repas':url=reverse('suivi:accord_repas',args=[x['id']])
        elif population in ('sejours','fragments_sejour'):
            a=objets[x['id']];url=reverse('suivi:accord_hebergement',args=[a.accord_id]);fragment='sejour-'+x['id']
        elif population=='affectations':
            a=objets[x['id']];url=reverse('suivi:accord_hebergement',args=[a.sejour.accord_id]);fragment='affectation-'+x['id']
        elif population=='repas':
            a=objets[x['id']];url=reverse('suivi:accord_repas',args=[a.accord_id]);fragment='repas-'+x['id']
        elif population=='aides':
            a=objets[x['id']];url=reverse('dossiers:aide',args=[a.accord_id]);fragment='remise-'+x['id']
        elif population in ('couts','imputations'):
            a=objets[x['id']]
            f=a.version.financement
            url=reverse('dossiers:financement',args=[f.nature,getattr(f,f.nature+'_id')]);query['version']=a.version.version;fragment=('cout-' if population=='couts' else 'imputation-')+x['id']
        if not liens:url=None
        if url:url+='?'+urlencode({**query,'retour_exploration':token})+('#'+fragment if fragment else '')
        type_objet={'personnes':'Personne','menages':'Ménage','prises':'Prise en charge','demandes':'Demande d’accueil','sejours':'Épisode de séjour','accords_hebergement':'Autorisation d’hébergement','accords_repas':'Autorisation de repas','affectations':'Période de lieu','repas':'Distribution de repas','aides':'Remise de prestation','appels':'Appel 115','ressources':'Déclaration de ressource','dettes':'Déclaration de dette','couts':'Composante de coût','imputations':'Imputation'}.get(population,dict(e.POPULATIONS).get(population,'Déclaration'))
        noms=' ; '.join(sorted(x.get('_libelles_personnes',{}).get(p,'') for p in x['personnes']))
        libelle=type_objet+(' — '+noms if noms else ' — bénéficiaire non identifié')
        lignes.append(dict(id=x['id'],date=x['date'],valeurs=cellules,url=url,libelle=libelle))
    return colonnes,lignes


@service_metier
def signer_retour(acteur,d,*,justificatif=None):
    from django.core import signing
    params={k:str(v) if v is not None else '' for k,v in d.items()}
    return signing.dumps({'acteur':str(acteur.pk),'parametres':params,'justificatif':justificatif},salt='retour-exploration-v1',compress=True)


@service_metier
def retour_verifie(acteur,token):
    from django.core import signing
    from urllib.parse import urlencode
    if not token or len(token)>20000:return None
    try:d=signing.loads(token,salt='retour-exploration-v1',max_age=86400)
    except (signing.BadSignature,TypeError,ValueError):return None
    if not isinstance(d,dict) or d.get('acteur')!=str(acteur.pk):return None
    params=d.get('parametres')
    if not isinstance(params,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in params.items()):return None
    if params.get('_analyse_preuve'):
        return reverse('dossiers:analyse_preuves')+'?'+urlencode({'preuve':params['_analyse_preuve'],'page':params.get('page','1')})
    if params.get('_analyse_definition'):
        return reverse('dossiers:analyse')+'?'+urlencode({'definition':params['_analyse_definition'],'page':params.get('page','1'),'retour_assemblage':params.get('_analyse_retour_assemblage','')})
    if isinstance(d.get('justificatif'),str):
        return reverse('dossiers:explorer_justificatifs')+'?'+urlencode({'preuve':d['justificatif'],'page':params.get('page','1')})
    if params.get('_source_rapport'):
        from .catalogue_rapports import SOURCES
        source=params.pop('_source_rapport')
        if source not in SOURCES:return None
        editeur=params.pop('_editeur_rapport','')=='1'
        route=reverse('dossiers:rapport_composer',args=[source]) if editeur else reverse(SOURCES[source][1])
        return route+'?'+urlencode(params)
    return reverse('dossiers:explorer')+'?'+urlencode(params)
