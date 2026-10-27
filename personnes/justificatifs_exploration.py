"""Justification des cellules calculées, sans reconstruire des filtres textuels."""
from collections import defaultdict
from decimal import Decimal
import hashlib
import json
from urllib.parse import urlencode
from django.core import signing
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import Http404
from django.urls import reverse
from . import exploration as e, mesures_exploration as mesures
from .forms_exploration import ExplorationForm
from .exploration_releve import relever, signer_retour

SEL='justificatifs-exploration-v1'


def canonique(x):
    def normaliser(v):
        if isinstance(v,dict):return {str(k):normaliser(val) for k,val in v.items()}
        if isinstance(v,set):return sorted((normaliser(val) for val in v),key=str)
        if isinstance(v,(tuple,list)):return [normaliser(val) for val in v]
        return v
    return json.dumps(normaliser(x),sort_keys=True,ensure_ascii=False,default=str,separators=(',',':'))


def empreinte(objets):
    return hashlib.sha256(canonique(sorted([
        (x['id'],sorted(map(str,x['personnes'])),sorted(map(str,x['menages'])),str(x['date']),
         str(mesures.quantite_retenue(x)),x['valeurs'],x.get('_par_personne'),x.get('_fragments'),x.get('_quantites_personnelles'))
        for x in objets],key=lambda x:x[0])).encode()).hexdigest()


def totaux_cellules(totaux,selection,code):
    quantitatif=code in ('quantite','minimum','maximum','moyenne')
    return [dict(_cellule={'total':u},_objets=[x for x in selection if not quantitatif or x['unite']==u],
        valeur=v,unite=u) for u,v in totaux.items()]


def lien(acteur,params,code,cellule,page=1):
    # Les périodes relatives sont figées pour expliquer ce calcul précis ; le
    # retour à l'analyse garde l'expression relative du formulaire d'origine.
    d={k:str(v) if v is not None else '' for k,v in params.items()}
    payload=dict(acteur=str(acteur.pk),params=d,mesure=code,cellule=cellule['_cellule'],
                 empreinte=empreinte(cellule['_objets']),page=str(page))
    token=signing.dumps(payload,salt=SEL,compress=True)
    return reverse('dossiers:explorer_justificatifs')+'?'+urlencode({'preuve':token})


def lire(acteur,token):
    if not token or len(token)>50000:raise Http404('Justificatif non vérifiable.')
    try:p=signing.loads(token,salt=SEL,max_age=86400)
    except (signing.BadSignature,ValueError,TypeError):raise Http404('Justificatif périmé ou non vérifiable.')
    if not isinstance(p,dict) or p.get('acteur')!=str(acteur.pk):raise Http404
    data=p.get('params')
    if not isinstance(data,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in data.items()):raise Http404
    f=ExplorationForm({**data,'periode':''},acteur=acteur)
    if not f.is_valid():raise ValidationError('Les paramètres ne sont plus utilisables avec vos droits actuels.')
    code=p.get('mesure')
    if code not in dict(f.fields['mesure'].choices):raise Http404
    rows,totaux,xs=e.calculer(acteur,{**f.cleaned_data,'mesure':code},contributions=True)
    toutes=[*rows,*totaux_cellules(totaux,xs,code)]
    cellule=next((r for r in toutes if canonique(r['_cellule'])==canonique(p.get('cellule'))),None)
    if cellule is None or empreinte(cellule['_objets'])!=p.get('empreinte'):
        erreur=ValidationError('Les données ont changé depuis ce chiffre. Revenez à l’analyse et recalculez avant d’ouvrir ses justificatifs.')
        erreur.retour=retour_analyse(p)
        raise erreur
    return p,f,cellule


def retour_analyse(p):
    return reverse('dossiers:explorer')+'?'+urlencode({**p['params'],'page':p.get('page','1')})


def contributions(acteur,d,code,cellule,token,page=1):
    xs=cellule['_objets'];lignes=[]
    # Chaque lien désigne un objet de la sélection signée et revalidée.
    def objet(x):return reverse('dossiers:explorer_fait')+'?'+urlencode({'preuve':token,'objet':x['id'],'page':page})
    def ajouter(x,libelle,valeur,periode=None):
        if len(lignes)>=10000:raise ValidationError('Plus de 10 000 contributions : réduisez la sélection. Aucun détail tronqué.')
        lignes.append(dict(libelle=libelle,valeur=valeur,periode=periode or str(x['date']),url=objet(x),objet=x['id']))
    noms={p:nom for x in xs for p,nom in x.get('_libelles_personnes',{}).items()}
    if code in ('personnes','menages',*mesures.PERSONNES,*mesures.FAMILLE):
        par_identite=defaultdict(list)
        for x in xs:
            for pk in x['menages' if code=='menages' else 'personnes']:
                if code in mesures.PERSONNES and not mesures.mesurer([{**x,'personnes':{pk}}],code):continue
                par_identite[pk].append(x)
        familiaux=mesures.valeurs_familiales(xs,code) if code in mesures.FAMILLE else {}
        for pk,faits in sorted(par_identite.items(),key=lambda v:str(v[0])):
            valeur=familiaux.get(pk) if code in mesures.FAMILLE else 1
            # Une identité contribue une fois ; les autres faits restent accessibles à zéro.
            for i,x in enumerate(faits):
                ajouter(x,(noms.get(pk,str(pk)))+(' — déjà compté dans cette partie' if i else ''),valeur if i==0 else 0)
    elif code in mesures.NUITEES or code=='quantite' and any('_fragments' in x for x in xs):
        personnes={p.pk:p for p in e.m.Personne.objects.filter(pk__in={p for x in xs for p in x['personnes']})}
        for x in xs:
            for debut,fin,beneficiaires in x['_fragments']:
                for pk in sorted(beneficiaires & x['personnes'],key=str):
                    valeur=mesures.ventiler_nuitees(personnes[pk],debut,fin)[list(mesures.NUITEES).index(code)] if code in mesures.NUITEES else (fin-debut).days
                    ajouter(x,noms.get(pk,str(pk)),valeur,f'{debut} → {fin} (fin exclue)')
    else:
        for x in xs:
            if code=='objets':valeur=1
            elif code in ('adultes_declares','enfants_declares','grossesses_declarees'):
                vs=x['valeurs'].get(code,[]);valeur=sum(vs) if vs else None
            else:valeur=mesures.quantite_retenue(x)
            ajouter(x,' · '.join(noms.get(p,str(p)) for p in sorted(x['personnes'],key=str)) or 'Bénéficiaire non identifié',valeur)
    regle=('Une identité distincte compte une seule fois dans cette partie ; ses autres faits ne s’ajoutent pas.'
           if code in ('personnes','menages',*mesures.PERSONNES) else
           'Une valeur par déclarant distinct ; les valeurs inconnues sont exclues, pas remplacées par zéro.' if code in mesures.FAMILLE else
           'Âge exact à chaque nuit civile ; les âges inconnus restent séparés. Les absences ne sont pas déduites.' if code in mesures.NUITEES else
           'Minimum, maximum ou moyenne des quantités connues par objet, après sélection ; ne pas additionner le résultat aux contributions.' if code in ('minimum','maximum','moyenne') else
           'Quantités des objets retenus, séparées par unité. Une remise ou un coût collectif reste entier ; les nuitées suivent les bénéficiaires retenus.' if code=='quantite' else
           'Un objet retenu compte une fois ; les cellules multivaluées ne s’additionnent pas.' if code=='objets' else
           'Effectifs déclarés par appel, non dédoublonnés entre les appels ; les inconnus ne sont pas des zéros.')
    return lignes,regle


def fiche_objet(acteur,d,cellule,identifiant,token,page):
    x=next((x for x in cellule['_objets'] if x['id']==identifiant),None)
    if x is None:raise Http404
    _,lignes=relever(d,[x],acteur)
    # Destination exacte existante, avec une fiche justificative pour les objets
    # qui ne possèdent pas encore de route propre (distribution, ligne de coût…).
    native=lignes[0]['url']
    if native:
        from urllib.parse import urlsplit,urlunsplit,parse_qsl
        u=urlsplit(native);q=dict(parse_qsl(u.query,keep_blank_values=True))
        q['retour_exploration']=signer_retour(acteur,{'page':page},justificatif=token)
        native=urlunsplit((u.scheme,u.netloc,u.path,urlencode(q),u.fragment))
    cles=[c for c in x['valeurs'] if c!='total' and c in e.disponibles(acteur)]
    lignes=[]
    for c in cles:
        projection={**d,**{'colonne'+str(i):'' for i in range(1,12)},'colonne1':c}
        _,rs=relever(projection,[x],acteur,liens=False)
        lignes.append((e.DIMENSIONS[c],rs[0]['valeurs'][0]))
    return x,lignes,native
