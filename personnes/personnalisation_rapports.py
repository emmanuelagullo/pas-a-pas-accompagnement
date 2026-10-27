"""Adaptateurs explicites de rapports ; aucun rapprochement approximatif."""
from datetime import date,timedelta
from urllib.parse import urlencode
from django.core.exceptions import ValidationError
from django.http import Http404
from django.urls import reverse
from django.utils import timezone
from . import models as m

SOURCES={'statistiques':'statistiques','financements':'dossiers:rapport_financements','appels':'dossiers:appels115',
         'personnel':'dossiers:rapport_a','parcours':'dossiers:rapport_parcours','aides':'dossiers:rapport_aides','hebergement':'dossiers:rapport_hebergement_individuel'}


def lien(source,params):
    if source not in SOURCES:raise Http404
    return reverse('dossiers:personnaliser_rapport',args=[source])+'?'+urlencode({k:v for k,v in params.items() if k not in ('page','format','modele')})


def limite_personnalisation(source,data):
    """Limites connues, expliquées avant le clic et revalidées par l'adaptateur."""
    if source not in SOURCES:raise Http404
    if source=='statistiques':
        if data.get('comparer')=='1' and data.get('rapport')!='ages':
            return 'La comparaison de périodes juxtapose plusieurs calculs. Elle n’est pas encore représentable comme une seule analyse ; le rapport courant reste disponible.'
        if data.get('rapport','synthese') not in ('repas','exploration_repas'):
            return 'Ce rapport combine des populations ou des règles de décompte qui ne sont pas encore représentables fidèlement dans une seule analyse (notamment nuits distinctes, mouvements ou durées civiles). Aucune approximation n’a été produite.'
    elif source=='appels':
        from django.forms import CheckboxInput
        if CheckboxInput().value_from_datadict(data,{},'annules') or str(data.get('q') or '').strip() or data.get('personne') or data.get('menage'):
            return 'L’inclusion des appels annulés, la recherche textuelle transversale ou le filtre de dossier ne sont pas encore repris fidèlement dans cet explorateur. Aucun critère n’a été abandonné silencieusement.'
    elif source!='financements':
        return 'Ce rapport conserve des règles et des informations propres qui ne sont pas encore reprises intégralement par cet adaptateur. Le rapport courant reste accessible ; aucune nouvelle analyse approximative n’a été créée.'
    return ''


def adapter(acteur,source,data):
    if source not in SOURCES:raise Http404
    p=dict(population='repas',mesure='quantite',axe='total',croisement='',classes='',filtre1='',operation1='egal',valeur1='',filtre2='',operation2='egal',valeur2='',reference=timezone.localdate().isoformat())
    filtres=[]
    def filtrer(c,v,op='egal'):
        if v not in (None,''):filtres.append((c,op,str(v)))
    if source=='statistiques':
        from .vues_statistiques import parametres_modele
        from .suivi import exiger
        exiger(acteur,'view_accompagnement','view_sejour','view_repasdistribue')
        d=parametres_modele(data);rapport=d['rapport']
        limite=limite_personnalisation(source,d)
        if limite:raise ValidationError(limite)
        p.update(debut=d['debut'],fin=d['fin'],periode=d['periode'],lignes_vides=True)
        p['axe']='type'
        if rapport=='exploration_repas':
            regroup=d['regroupement'];p['axe']='mois' if regroup!='categorie' else 'type'
            p['croisement']='type' if regroup=='mois_categorie' else ''
            if d['service']:filtrer('type',dict(m.AccordRepas.SERVICES)[d['service']])
    elif source=='financements':
        from .vues_financements import RapportForm
        from .financements import droit
        droit(acteur)
        f=RapportForm(data)
        if not f.is_valid():raise ValidationError('Les paramètres du rapport financier doivent être valides avant sa personnalisation.')
        d=f.cleaned_data;p.update(population=d['mode'],debut=d['debut'],fin=d['fin'])
        filtrer('phase',dict(m.LigneCout.PHASES)[d['phase']]);filtrer('nature_financement',d.get('nature'))
        for c,dest in [('reference','reference_calcul'),('devise','unite'),('unite','unite_facturee'),('categorie','etat'),('budget','budget')]:
            valeur=d.get(c)
            if c=='devise' and valeur:valeur=valeur.upper()+' / '+d['phase']
            filtrer(dest,valeur,'egal_sensible')
        for c in ('financeur','prescripteur','signataire'):filtrer(c+'_id',getattr(d.get(c),'pk',None))
        for mot in d.get('q','').split():filtrer('dossier',mot,'contient')
        # La devise et la phase restent une unité monétaire indivisible ; les
        # colonnes physiques ne changent pas le sens de la mesure Quantité.
        cols=['dossier','phase','quantite','unite']
        if d['mode']=='couts':cols+=['unite_facturee','quantite_facturee','prix_unitaire']
        p.update(nombre_colonnes=len(cols),**{'colonne'+str(i):c for i,c in enumerate(cols,1)})
    elif source=='appels':
        from .forms_exploration import AppelsRechercheForm
        from .appels115 import droit
        droit(acteur)
        f=AppelsRechercheForm(data)
        if not f.is_valid():raise ValidationError('Les critères du rapport d’appels doivent être valides.')
        d=f.cleaned_data
        limite=limite_personnalisation(source,{**d,'personne':data.get('personne'),'menage':data.get('menage')})
        if limite:raise ValidationError(limite)
        p.update(population='appels',mesure='objets',debut=d['debut'],fin=d['fin'])
        for c,dest in [('motif_principal','motif'),('lieu_appel','origine'),('secondaire','secondaire'),('reponse','reponse')]:filtrer(dest,d.get(c))
        if d.get('type_appelant'):filtrer('type',dict(m.VersionAppel115.TYPES)[d['type_appelant']])
        if d.get('etat_reponse'):filtrer('etat',dict(m.VersionAppel115._meta.get_field('etat_reponse').choices)[d['etat_reponse']])
        filtrer('heure',d.get('heure_min'),'gte');filtrer('heure',d.get('heure_max'),'lt')
    else:
        raise ValidationError(limite_personnalisation(source,data))
    if len(filtres)>20:raise ValidationError('Plus de vingt critères sont nécessaires pour ce rapport : personnalisation refusée sans perte silencieuse.')
    p['filtres']=max(2,len(filtres))
    for i,(c,op,v) in enumerate(filtres,1):p.update({f'filtre{i}':c,f'operation{i}':op,f'valeur{i}':v})
    p['reference']=str(p['fin']-timedelta(days=1)) if not isinstance(p['fin'],str) else (date.fromisoformat(p['fin'])-timedelta(days=1)).isoformat()
    return p


def signer_origine(acteur,source,params):
    from django.core import signing
    return signing.dumps(dict(acteur=str(acteur.pk),source=source,params={k:str(v) for k,v in params.items() if k not in ('page','format','modele')}),salt='origine-personnalisation-v1',compress=True)


def retour_origine(acteur,token):
    from django.core import signing
    try:p=signing.loads(token,salt='origine-personnalisation-v1',max_age=86400)
    except (signing.BadSignature,ValueError,TypeError):return None
    if not isinstance(p,dict) or p.get('acteur')!=str(acteur.pk) or p.get('source') not in SOURCES or not isinstance(p.get('params'),dict):return None
    return reverse(SOURCES[p['source']])+'?'+urlencode(p['params'])
