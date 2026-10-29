"""Assemblages personnels de définitions photographiées, sans partage d'accès."""
from copy import deepcopy
from django.core.exceptions import ValidationError, PermissionDenied
from django.urls import reverse
from acteurs.contexte import service_metier
from . import models as m, analyses, modeles_personnels as gestion


def defaut():
    return dict(parties=[],periode='',debut='',fin='',filtre='',export_prioritaire='pdf')


def lire(params):
    if params.get('schema')!=2 or params.get('assemblage') is not True:raise ValidationError('Version d’assemblage non prise en charge.')
    d=analyses.lire({**params,'analyse':True})
    if set(d)-{'parties','periode','debut','fin','decalage_debut','decalage_fin','filtre','export_prioritaire'}:raise ValidationError('Paramètre d’assemblage inconnu.')
    return d


def parametres(d):
    return dict(schema=2,assemblage=True,definition=analyses.encoder(d),export_prioritaire=d.get('export_prioritaire','pdf'))


@service_metier
def photographier(acteur,request,*,modele=None,cle=None):
    if acteur.pk!=request.user.pk:raise PermissionDenied
    if modele is not None:
        if modele.auteur_id!=request.user.pk:raise PermissionDenied
        gestion.exiger(request.user,modele)
        if modele.parametres.get('assemblage'):raise ValidationError('Ajoutez les parties séparément : les assemblages ne sont pas imbriqués.')
        from .vues_rapports import source_modele
        source=source_modele(modele);params=gestion.valider(request.user,modele.parametres)
        return dict(titre=modele.nom,description=modele.description,source=source,parametres=params,modele=modele.pk,empreinte=gestion.etat(modele),periode_commune=False)
    from .catalogue_rapports import catalogue
    proposition=next((r for r in catalogue(request.user) if r['cle']==cle),None)
    if proposition is None:raise PermissionDenied
    from .vues_rapports import reponse_source,parametres_response
    params={'rapport':proposition['rapport']} if proposition.get('rapport') else {}
    r=reponse_source(request,proposition['source'],params)
    return dict(titre=proposition['titre'],description='',source=proposition['source'],parametres=parametres_response(r,proposition['source'],params),modele=None,empreinte='',periode_commune=False)


@service_metier
def valider(acteur,d):
    d=deepcopy(d)
    lire(parametres(d))
    from .presentation_exports import valider as valider_export
    valider_export(d.get('export_prioritaire',''))
    if d.get('filtre','tous') not in ('','tous','mes','service','attente'):raise ValidationError('Sélection de dossiers inconnue.')
    parties=d.get('parties')
    if not isinstance(parties,list) or len(parties)>12:raise ValidationError('Un assemblage comporte au plus douze parties.')
    for partie in parties:
        if not isinstance(partie,dict) or set(partie)-{'titre','description','source','parametres','modele','empreinte','periode_commune'}:raise ValidationError('Partie d’assemblage invalide.')
        if not isinstance(partie.get('titre'),str) or not partie['titre'].strip() or len(partie['titre'])>160:raise ValidationError('Nommez chaque partie (160 caractères au plus).')
        if not isinstance(partie.get('description',''),str) or len(partie.get('description',''))>6000:raise ValidationError('Description de partie invalide.')
        if not isinstance(partie.get('parametres'),dict):raise ValidationError('Paramètres de partie invalides.')
        if not isinstance(partie.get('periode_commune',False),bool):raise ValidationError('Choix de période commune invalide.')
        if partie.get('modele') is not None and (not isinstance(partie['modele'],int) or isinstance(partie['modele'],bool) or partie['modele']<=0):raise ValidationError('Référence du modèle d’origine invalide.')
        if not isinstance(partie.get('empreinte',''),str) or len(partie.get('empreinte',''))>64:raise ValidationError('Version de modèle invalide.')
        source=partie.get('source')
        if source=='analyse':
            contenu=analyses.valider(acteur,analyses.lire(partie['parametres']))
            analyses.calculer(acteur,contenu)
            partie['parametres']=analyses.parametres(contenu)
        elif source=='exploration':
            from .modeles_echange import valider as valider_exploration
            partie['parametres']=valider_exploration(acteur,partie['parametres'])
        else:
            from .catalogue_rapports import SOURCES
            if source not in SOURCES:raise ValidationError('Source de partie non prise en charge.')
            from .vues_rapports import valider_source
            partie['parametres']=valider_source(acteur,{**partie['parametres'],'_rapport_source':source})
    if len(analyses.encoder(d).encode())>analyses.MAX_DEFINITION:raise ValidationError('L’assemblage dépasse 64 Kio.')
    return d


def appliquer_periode(d,partie):
    p=deepcopy(partie['parametres'])
    if not partie.get('periode_commune'):return p
    from .periodes_rapports import resoudre
    commun={k:d[k] for k in ('periode','debut','fin','decalage_debut','decalage_fin') if k in d}
    try:commun=resoudre(commun)
    except (ValueError,TypeError,OverflowError):raise ValidationError('La période commune est invalide.')
    if not commun.get('debut') or not commun.get('fin'):raise ValidationError('Renseignez la période commune avant de l’appliquer.')
    if partie['source']=='analyse':
        contenu=analyses.lire(p);contenu.update(commun);return analyses.parametres(contenu)
    if 'debut' not in p or 'fin' not in p:raise ValidationError('Cette partie utilise une date de référence, pas une période. Conservez son réglage propre.')
    p.update(commun)
    return p


@service_metier
def documents(acteur,request,d):
    if acteur.pk!=request.user.pk:raise PermissionDenied
    d=valider(request.user,d);docs=[]
    from .exports_rapports import document
    from .vues_analyses import document as document_analyse,url_analyse
    from .catalogue_rapports import SOURCES
    from acteurs.statistiques import selection
    from urllib.parse import urlencode
    for partie in d['parties']:
        params=appliquer_periode(d,partie)
        if d.get('filtre'):params['filtre']=d['filtre']
        source=partie['source']
        if source=='analyse':
            contenu=analyses.lire(params);contenu['filtre']=params.get('filtre',contenu.get('filtre','tous'))
            with selection(request.user,contenu,'analyse'):
                resultat=analyses.calculer(request.user,contenu)
                doc=document_analyse(resultat,partie['titre'],partie.get('description',''))
            url=url_analyse(contenu)
        else:
            doc=document(request,dict(source=source,parametres=params),inclure_description=False)
            doc['titre']=partie['titre'];doc['description']=partie.get('description','')
            url=reverse('dossiers:explorer')+'?'+urlencode(params) if source=='exploration' else reverse(SOURCES[source][1])+'?'+urlencode(params)
        # Aucun résultat ni donnée de dossier n'est stocké dans la définition.
        from django.core import signing
        from urllib.parse import urlsplit,urlunsplit,parse_qsl
        donnees=request.POST if request.method=='POST' else request.GET
        retour=signing.dumps(dict(acteur=str(request.user.pk),definition=d,cible=donnees.get('cible') or donnees.get('modele'),partie=len(docs)+1),salt='retour-assemblage-v2',compress=True)
        u=urlsplit(url);q=dict(parse_qsl(u.query));q['retour_assemblage']=retour
        doc['url']=urlunsplit((u.scheme,u.netloc,u.path,urlencode(q),u.fragment));doc['origine_modifiee']=False;doc['origine_absente']=False
        if partie.get('modele'):
            original=m.ModeleRapport.objects.filter(pk=partie['modele'],auteur=request.user).first()
            doc['origine_absente']=original is None
            doc['origine_modifiee']=original is not None and gestion.etat(original)!=partie.get('empreinte')
        docs.append(doc)
    return docs


def structure(d):
    """La résolution quotidienne d'une période ne change pas le modèle composé."""
    resultat=[]
    from .traduction_analyses import structure as structure_analyse
    for partie in d['parties']:
        p=partie['parametres']
        if partie['source']=='analyse':definition=structure_analyse(analyses.lire(p))
        else:definition={k:v for k,v in p.items() if k not in ('debut','fin','date','reference','periode','decalage_debut','decalage_fin','filtre','export_prioritaire')}
        resultat.append(dict(source=partie['source'],definition=definition,titre=partie['titre']))
    return resultat
