"""Analyses à mesures indépendantes, sur le registre métier existant.

Pas de jointure multiplicative : chaque mesure garde ses objets et son unité.
Les critères relationnels retiennent des identités, jamais des copies de faits.
"""
from copy import deepcopy
from datetime import timedelta
import json
from django.core.exceptions import ValidationError
from django.utils import timezone
from acteurs.contexte import service_metier
from . import exploration as e
from .forms_exploration import ExplorationForm

MAX_DEFINITION = 65536


def encoder(definition):
    return json.dumps(definition, ensure_ascii=False, separators=(',', ':'), default=str)


def lire(params):
    if params.get('schema') != 2 or params.get('analyse') is not True:
        raise ValidationError('Version de composition non prise en charge.')
    texte = params.get('definition', '')
    if not isinstance(texte, str) or len(texte.encode()) > MAX_DEFINITION:
        raise ValidationError('La composition dépasse 64 Kio.')
    try:
        d = json.loads(texte)
    except (ValueError, TypeError):
        raise ValidationError('Définition de composition invalide.')
    if not isinstance(d, dict):
        raise ValidationError('Une définition structurée est nécessaire.')
    if 'export_prioritaire' in params:d['export_prioritaire']=params['export_prioritaire']
    return d


def parametres(d):
    return dict(schema=2, analyse=True, definition=encoder(d),
                export_prioritaire=d.get('export_prioritaire', ''))


def defaut():
    jour = timezone.localdate()
    return dict(debut=jour.replace(day=1).isoformat(), fin=(jour+timedelta(days=1)).isoformat(),
                reference=jour.isoformat(), periode='', decalage_debut=-6,decalage_fin=1, reference_mode='commune',
                affichage='synthese', lignes='personnes', colonnes=[], axes=['total'],
                sous_totaux=False, combinaison='toutes', criteres=[],
                mesures=[dict(titre='Repas distribués', source='repas', mesure='quantite')])


@service_metier
def configuration(acteur, d, partie, *, classement=True):
    source=partie.get('source')
    from .suivi import exiger
    if source in e.DECLARATIONS:exiger(acteur,*e.GROUPES[source][2])
    elif source in ('sejours','fragments_sejour'):exiger(acteur,'view_menage','view_accompagnement','view_accordhebergement','view_sejour')
    elif source=='affectations':exiger(acteur,'view_menage','view_accompagnement','view_accordhebergement','view_sejour','view_affectation','view_lieuhebergement')
    elif source=='prises':exiger(acteur,'view_menage','view_accompagnement')
    elif source in ('accords_repas','accords_hebergement'):exiger(acteur,'view_menage','view_accompagnement','view_accordrepas' if source=='accords_repas' else 'view_accordhebergement')
    elif source=='repas':
        from .repas import droit
        droit(acteur,'view_repasdistribue')
    elif source=='aides':
        from .aides import droit
        droit(acteur)
    elif source=='appels':
        from .appels115 import droit
        droit(acteur)
    elif source in ('couts','imputations'):
        from .financements import droit
        droit(acteur)
    elif source=='demandes':
        from .parcours import exiger as exiger_parcours
        exiger_parcours(acteur,'demandes')
    elif source=='relations':
        from .relations_personnelles import DROITS_LECTURE
        exiger(acteur,*DROITS_LECTURE)
    if partie.get('mesure')=='nuits_hors_absences':exiger(acteur,'view_absence')
    axes=d.get('axes') or ['total']
    p=dict(population=partie.get('source'), mesure=partie.get('mesure','objets'),
           debut=d.get('debut'), fin=d.get('fin'), reference=d.get('reference'),
           reference_mode=d.get('reference_mode','commune'), axe=axes[0] if classement else 'total',
           croisement=axes[1] if classement and len(axes)>1 else '', niveaux=max(2,len(axes)) if classement else 2,
           sous_totaux=d.get('sous_totaux',False) if classement else False,
           mouvement=partie.get('mouvement','chevauche'), portion=partie.get('portion','selection'),
           cohorte=partie.get('cohorte','tous'), classes='', classes_croisement='',
           lignes_vides=partie.get('lignes_vides',False), filtres=max(2,len(partie.get('filtres',[]))))
    if classement:
        for i,axe in enumerate(axes[2:],3):p['axe'+str(i)]=axe
        for i,texte in enumerate(d.get('classes',[])):
            p['classes' if i==0 else 'classes_croisement' if i==1 else 'classes'+str(i+1)]=texte
    for i in range(1,p['filtres']+1):
        f=partie.get('filtres',[])[i-1] if i<=len(partie.get('filtres',[])) else {}
        p.update({f'filtre{i}':f.get('champ',''),f'operation{i}':f.get('operation','egal'),f'valeur{i}':f.get('valeur','')})
    colonnes=d.get('colonnes',[]) if not classement else []
    p.update(nombre_colonnes=len(colonnes))
    for i,col in enumerate(colonnes,1):p['colonne'+str(i)]=col
    f=ExplorationForm(p,acteur=acteur)
    if not f.is_valid():raise ValidationError(' ; '.join(str(f.fields[k].label or k)+': '+', '.join(v) for k,v in f.errors.items()))
    return f.cleaned_data


@service_metier
def valider(acteur, definition, *, figer=False):
    if not isinstance(definition,dict):raise ValidationError('Définition structurée invalide.')
    d=deepcopy(definition)
    permis={'debut','fin','reference','periode','decalage_debut','decalage_fin','reference_mode','affichage','lignes','colonnes','axes','classes','sous_totaux','combinaison','criteres','mesures','filtre','export_prioritaire'}
    for cle in ('debut','fin','reference','periode','reference_mode','affichage','lignes','combinaison','filtre','export_prioritaire'):
        if cle in d and not isinstance(d[cle],str):raise ValidationError('Valeur invalide pour '+cle+'.')
    if set(d)-permis:raise ValidationError('Un paramètre de composition est inconnu.')
    if d.get('affichage') not in ('synthese','detail'):raise ValidationError('Choisissez la présentation du résultat.')
    if d.get('lignes') not in dict(e.POPULATIONS):raise ValidationError('Choisissez ce que représente une ligne détaillée.')
    for cle,maximum in [('colonnes',11),('axes',7),('classes',7),('criteres',20),('mesures',12)]:
        if not isinstance(d.get(cle,[]),list) or len(d.get(cle,[]))>maximum:raise ValidationError('Nombre de '+cle+' non pris en charge.')
    if any(not isinstance(c,str) for c in d.get('classes',[])):raise ValidationError('Classes numériques invalides.')
    if not d.get('mesures'):raise ValidationError('Ajoutez au moins une mesure.')
    if d.get('combinaison','toutes') not in ('toutes','une'):raise ValidationError('Combinaison de critères inconnue.')
    if not isinstance(d.get('sous_totaux',False),bool):raise ValidationError('Choix des sous-totaux invalide.')
    from .presentation_exports import valider as export_valide
    export_valide(d.get('export_prioritaire',''))
    if 'filtre' in d and d['filtre'] not in ('tous','mes','service','attente'):raise ValidationError('Sélection de dossiers inconnue.')
    if d.get('periode'):
        from .periodes_rapports import bornes_periode
        try:
            debut,fin=bornes_periode(d['periode'],timezone.localdate(),decalage_debut=d.get('decalage_debut',-6),decalage_fin=d.get('decalage_fin',1))
        except (ValueError,TypeError,OverflowError):raise ValidationError('Période relative invalide.')
        d.update(debut=debut.isoformat(),fin=fin.isoformat(),reference=(fin-timedelta(days=1)).isoformat())
        if figer:d['periode']=''
    autorise=e.disponibles(acteur)
    for cle in ('axes','colonnes'):
        choix=e.disponibles(acteur,informations=True) if cle=='colonnes' else autorise
        if any(not isinstance(c,str) or c not in choix for c in d.get(cle,[])):raise ValidationError('Information indisponible dans '+cle+'.')
    for partie in [*d.get('criteres',[]),*d['mesures']]:
        if not isinstance(partie,dict) or set(partie)-{'titre','source','mesure','mouvement','portion','cohorte','lignes_vides','filtres','relation','mode'}:raise ValidationError('Partie de calcul invalide.')
        if not isinstance(partie.get('titre',''),str) or len(partie.get('titre',''))>160:raise ValidationError('Titre de mesure trop long.')
        fs=partie.get('filtres',[])
        if not isinstance(fs,list) or len(fs)>20 or any(not isinstance(f,dict) or set(f)-{'champ','operation','valeur'} for f in fs):raise ValidationError('Filtres de partie invalides.')
        configuration(acteur,d,partie)
    for c in d.get('criteres',[]):
        if c.get('relation','personne') not in ('personne','menage','prise') or c.get('mode','avec') not in ('avec','sans'):raise ValidationError('Relation ou condition inconnue.')
    configuration(acteur,d,dict(source=d['lignes'],mesure='objets'),classement=False)
    if len(encoder(d).encode())>MAX_DEFINITION:raise ValidationError('La composition dépasse 64 Kio.')
    return d


def indexer(xs,relation):
    index=set()
    for x in xs:
        index.update(x['personnes'] if relation=='personne' else x['menages'] if relation=='menage' else [x['prise']] if x.get('prise') else [])
    return index


@service_metier
def selecteur(acteur,d):
    tests=[]
    for c in d.get('criteres',[]):
        cfg=configuration(acteur,d,{**c,'mesure':'objets'},classement=False)
        _,_,xs=e.calculer(acteur,cfg)
        relation=c.get('relation','personne')
        tests.append((relation,c.get('mode','avec'),indexer(xs,relation)))
    def retenir(xs):
        if not tests:return xs
        retenus=[]
        for x in xs:
            def accepte(personne):
                reponses=[]
                for relation,mode,ids in tests:
                    cles={personne} if relation=='personne' and personne is not None else x['menages'] if relation=='menage' else {x['prise']} if relation=='prise' and x.get('prise') else set()
                    # Sans identité de relation connue, on ne peut affirmer son absence.
                    ok=bool(cles) and (bool(cles & ids) if mode=='avec' else not bool(cles & ids))
                    reponses.append(ok)
                return any(reponses) if d.get('combinaison')=='une' else all(reponses)
            if x['personnes']:
                ps={p for p in x['personnes'] if accepte(p)}
                if not ps:continue
                x={**x,'personnes':ps}
            elif not accepte(None):continue
            retenus.append(x)
        return retenus
    return retenir


@service_metier
def calculer(acteur,definition):
    d=valider(acteur,definition)
    retenir=selecteur(acteur,d)
    resultats=[]
    for n,partie in enumerate(d['mesures']):
        cfg=configuration(acteur,d,partie)
        rows,totaux,xs=e.calculer(acteur,cfg,contributions=True,selectionner=retenir)
        if not totaux and cfg['mesure']=='quantite' and cfg['population'] in ('repas','sejours','fragments_sejour','affectations'):
            totaux={'repas' if cfg['population']=='repas' else 'personne-nuit affectée à un lieu (absences non déduites)' if cfg['population']=='affectations' else 'personne-nuit de séjour (absences non déduites)':0}
        resultats.append(dict(index=n,titre=partie.get('titre') or dict(ExplorationForm(acteur=acteur).fields['mesure'].choices)[cfg['mesure']],configuration=cfg,lignes=rows,totaux=totaux,objets=xs))
    if sum(len(r['lignes']) for r in resultats)>2000:raise ValidationError('Plus de 2 000 cellules : réduisez les classements ou la période. Aucun résultat tronqué.')
    details=[]
    if d['affichage']=='detail':
        from collections import defaultdict
        for r in resultats:
            index=defaultdict(list)
            for f in r['objets']:
                cles=f['personnes'] if d['lignes']=='personnes' else f['menages'] if d['lignes']=='menages' else [f['id']] if r['configuration']['population']==d['lignes'] else [f.get('prise')] if f.get('prise') else []
                for cle in cles:index[cle].append(f)
            r['_index_detail']=index
        base=configuration(acteur,d,dict(source=d['lignes'],mesure='objets'),classement=False)
        _,_,xs=e.calculer(acteur,base,contributions=True,selectionner=retenir)
        if len(xs)>2000:raise ValidationError('Plus de 2 000 lignes détaillées : réduisez les filtres. Aucun résultat tronqué.')
        from .exploration_releve import relever
        _,projections=relever(base,xs,acteur,liens=False)
        for x,projection in zip(xs,projections):
            if not d.get('colonnes'):projection['valeurs']=[]
            cellules=[];justifications=[]
            for r in resultats:
                cfg=r['configuration']
                def relier(faits):
                    return [{**f,'personnes':f['personnes'] & x['personnes']} for f in faits if f['personnes'] & x['personnes']] if d['lignes']=='personnes' else [f for f in faits if f['menages'] & x['menages']] if d['lignes']=='menages' else [f for f in faits if f['id']==x['id']] if cfg['population']==d['lignes'] else [f for f in faits if x.get('prise') is not None and f.get('prise')==x['prise']]
                # Même sélection par mesure, sans recompter les autres bénéficiaires.
                p={**cfg,'axe':'total','croisement':'','niveaux':2,'sous_totaux':False}
                for i in range(3,8):p.pop('axe'+str(i),None)
                candidats=r['_index_detail'].get(next(iter(x['personnes'])) if d['lignes']=='personnes' and x['personnes'] else next(iter(x['menages'])) if d['lignes']=='menages' and x['menages'] else x['id'] if cfg['population']==d['lignes'] else x.get('prise'),[])
                faits=relier(candidats)
                _,totaux,_=e.agreger(p,faits)
                if not totaux:
                    compter=cfg['mesure'] in ('objets','personnes','menages','participations',*e.mesures.NUITS_DISTINCTES)
                    flux=cfg['mesure']=='quantite' and cfg['population'] not in e.DECLARATIONS
                    unites=list(r['totaux']) or ['repas' if cfg['population']=='repas' else 'personne-nuit de séjour (absences non déduites)' if cfg['population'] in ('sejours','fragments_sejour') else cfg['mesure']]
                    totaux={u:0 if compter or flux else None for u in unites}
                cellules.append(totaux)
                justifications.append([dict(_cellule={'detail':x['id'],'unite':u},_objets=[f for f in faits if cfg['mesure'] not in ('quantite','minimum','maximum','moyenne') or f['unite']==u],valeur=v,unite=u) for u,v in totaux.items()])
            details.append(dict(objet=x,projection=projection,mesures=cellules,justifications=justifications))
    return dict(definition=d,mesures=resultats,details=details,colonnes=[e.DIMENSIONS[c] for c in d.get('colonnes',[])])
