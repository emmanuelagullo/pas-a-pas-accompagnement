"""Catalogue, composition depuis une définition fidèle et gestion personnelle."""
from copy import copy
from urllib.parse import urlencode
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.http import QueryDict,Http404
from django.shortcuts import render,redirect,get_object_or_404
from django.urls import reverse,resolve
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from . import models as m,catalogue_rapports as c,modeles_personnels as s

UI={'csrfmiddlewaretoken','nom','action_modele','modele','modele_cible','attendu_modele','derive','page','format','composer_librement'}


def source_modele(x):return x.parametres.get(c.CLE_SOURCE) or ('exploration' if x.parametres.get('exploration') else 'statistiques')


def lecture(acteur,x):
    source=source_modele(x)
    if source=='exploration':
        from .modeles_echange import valider
        valider(acteur,x.parametres)
    elif not c.accessible(acteur,source,x.parametres.get('rapport')):raise PermissionDenied


def peut_stockage(acteur,source):
    if source=='statistiques':return c.accessible(acteur,source)
    return acteur.has_perms(['personnes.view_modelerapport','personnes.add_modelerapport'])


def reponse_source(request,source,donnees):
    if source not in c.SOURCES:raise Http404
    if not c.accessible(request.user,source,donnees.get('rapport')):raise PermissionDenied
    if source=='statistiques':
        from .vues_statistiques import RAPPORTS
        if donnees.get('rapport') and donnees['rapport'] not in RAPPORTS:raise Http404
        if not donnees.get('rapport'):donnees={**donnees,'rapport':'synthese'}
    if source=='appels':
        for cle in ('personne','menage'):
            if donnees.get(cle) and not request.user.has_perm('personnes.view_'+cle):raise PermissionDenied
    from .periodes_rapports import resoudre
    try:donnees=resoudre(donnees)
    except (ValueError,TypeError,OverflowError):raise ValidationError('Règle de dates relatives invalide.')
    req=copy(request);req.method='GET';req.GET=QueryDict('',mutable=True)
    for k,v in donnees.items():req.GET[k]=v
    req.POST=QueryDict('')
    from django.urls import get_script_prefix
    chemin=reverse(c.SOURCES[source][1]);prefixe=get_script_prefix().rstrip('/')
    if prefixe and chemin.startswith(prefixe+'/'):chemin=chemin[len(prefixe):]
    vue=resolve(chemin)
    return vue.func(req,**vue.kwargs)


def parametres_response(reponse,source,donnees):
    ctx=getattr(reponse,'context_data',None)
    if not ctx:raise ValidationError('Ce rapport n’a pas produit de définition éditable.')
    f=ctx.get('form') or ctx.get('formulaire')
    if f is None or not f.is_valid():raise ValidationError('Corrigez les critères du rapport avant de l’enregistrer.')
    if source=='statistiques':
        from .vues_statistiques import parametres_modele
        params={**donnees,**dict(f.data.items())}
        for cle,valeur in [('rapport',ctx['rapport']),('regroupement',ctx['regroupement']),('service',ctx['service_choisi']),('lieu',ctx['lieu_choisi'])]:params.setdefault(cle,valeur)
        try:return parametres_modele(params)
        except (ValueError,TypeError) as e:raise ValidationError(str(e))
    p={k:str(f.data.get(k,'')) for k in f.fields}
    # Les cibles de journal d'appels portent en plus sur le dossier choisi.
    if source=='appels':
        from uuid import UUID
        for cle,modele in [('personne',m.Personne),('menage',m.Menage)]:
            if donnees.get(cle):
                try:pk=UUID(str(donnees[cle]))
                except (ValueError,TypeError):raise ValidationError('Cible du rapport invalide.')
                if not modele.objects.filter(pk=pk).exists():raise ValidationError('Cible du rapport introuvable.')
                p[cle]=str(pk)
    for cle in ('periode','decalage_debut','decalage_fin'):
        if donnees.get(cle) is not None:p[cle]=str(donnees[cle])
    p[c.CLE_SOURCE]=source
    return p


def valider_source(acteur,p):
    from django.http import HttpRequest
    source=p.get(c.CLE_SOURCE)
    r=HttpRequest();r.method='GET';r.path='/';r.user=acteur;r.session={}
    reponse=reponse_source(r,source,{k:v for k,v in p.items() if k!=c.CLE_SOURCE})
    return parametres_response(reponse,source,p)


@never_cache
@require_http_methods(['GET'])
@login_required
def accueil(request):
    rapports=c.catalogue(request.user)
    if not rapports and not request.user.has_perm('personnes.view_personne'):raise PermissionDenied
    personnels=list(m.ModeleRapport.objects.filter(auteur=request.user))
    for x in personnels:x.url_rapport=c.ouvrir(x)
    return render(request,'rapports/accueil.html',{'rapports':rapports,'personnels':personnels})


@never_cache
@require_http_methods(['GET'])
@login_required
def nouveau(request):
    if request.GET.get('modele'):
        x=get_object_or_404(m.ModeleRapport,pk=request.GET['modele'],auteur=request.user);lecture(request.user,x)
        return redirect(c.ouvrir(x)+'&derive=1')
    choix=c.catalogue(request.user)
    if request.GET.get('depart'):
        r=next((r for r in choix if r['cle']==request.GET['depart']),None)
        if r is None:raise Http404
        params={'rapport':r['rapport']} if r.get('rapport') else {}
        if request.GET.get('composer_librement')=='1':params['composer_librement']='1'
        return redirect(reverse('dossiers:rapport_composer',args=[r['source']])+'?'+urlencode(params))
    if not choix and not request.user.has_perm('personnes.view_personne'):raise PermissionDenied
    composables=[x for x in choix if x['source'] in ('financements','appels') or x.get('rapport') in ('repas','exploration_repas')] if request.user.has_perm('personnes.view_personne') else []
    personnels=m.ModeleRapport.objects.filter(auteur=request.user)
    return render(request,'rapports/nouveau.html',{'rapports':choix,'composables':composables,'personnels':personnels})


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def composer(request,source):
    if source not in c.SOURCES:raise Http404
    valeurs=request.POST if request.method=='POST' else request.GET
    cible=None
    pk=valeurs.get('modele') or valeurs.get('modele_cible')
    if pk:
        cible=get_object_or_404(m.ModeleRapport,pk=pk,auteur=request.user)
        if source_modele(cible)!=source:raise Http404
        lecture(request.user,cible)
    donnees=cible.parametres.copy() if cible and request.GET.get('modele') else {k:v for k,v in valeurs.items() if (k not in UI or k in ('page','format')) and k!=c.CLE_SOURCE}
    donnees.pop(c.CLE_SOURCE,None)
    if request.method=='GET':
        for cle in ('page','format'):
            if request.GET.get(cle):donnees[cle]=request.GET[cle]
    else:donnees.pop('format',None)
    if source in ('coordonnees','familles','identite') and not donnees:
        from django.utils import timezone
        donnees['date']=timezone.localdate().isoformat()
    try:reponse=reponse_source(request,source,donnees)
    except ValidationError as erreur:return render(request,'exploration/personnalisation_refusee.html',{'erreur':erreur,'retour':reverse('dossiers:rapports_accueil')},status=400)
    if not hasattr(reponse,'context_data'):return reponse
    ctx=reponse.context_data;statut=200;erreur=''
    if request.method=='GET' and request.GET.get('composer_librement')=='1':
        from .personnalisation_rapports import adapter,lien
        try:
            p=parametres_response(reponse,source,donnees)
            p.pop(c.CLE_SOURCE,None)
            adapter(request.user,source,p)
        except (ValidationError,ValueError) as erreur:
            return render(request,'exploration/personnalisation_refusee.html',{'erreur':erreur,'retour':reverse(c.SOURCES[source][1])+'?'+urlencode({k:v for k,v in donnees.items() if k not in ('format','page')})},status=422)
        return redirect(lien(source,p))
    ticket=valeurs.get('attendu_modele','')
    stockable=peut_stockage(request.user,source)
    if cible and stockable and request.method=='GET' and 'attendu_modele' not in valeurs:ticket=s.jeton(request.user,cible)
    if request.method=='POST':
        if not stockable:raise PermissionDenied
        try:
            params=parametres_response(reponse,source,donnees);nom=s.nom_valide(request.POST.get('nom',''))
            if request.POST.get('action_modele')=='remplacer':
                if cible is None:raise ValidationError('Choisissez votre modèle personnel à remplacer.')
                x=s.changer(request.user,cible,ticket,nom,params)
            elif request.POST.get('action_modele')=='creer':
                if m.ModeleRapport.objects.filter(auteur=request.user).count()>=30:raise ValidationError('Limite de 30 modèles personnels atteinte.')
                x=m.ModeleRapport.objects.create(auteur=request.user,nom=nom,parametres=params)
            else:raise ValidationError('Choisissez explicitement Enregistrer un second modèle ou Remplacer.')
        except ValidationError as e:erreur=' ; '.join(e.messages);statut=409 if isinstance(e,s.ConflitModele) else 400
        else:return redirect(c.ouvrir(x))
    f=ctx.get('form') or ctx.get('formulaire')
    params={k:v for k,v in (f.data.items() if f is not None else donnees.items()) if k not in UI}
    for cle in ('personne','menage'):
        if source=='appels' and donnees.get(cle):params[cle]=donnees[cle]
    ctx.update(composition_source=source,rapport_cible=cible,attendu_rapport=ticket,nom_rapport=request.POST.get('nom',cible.nom if cible else ''),parametres_composition=params,erreur_composition=erreur,peut_enregistrer_rapport=stockable)
    if cible:
        for cle in ('query','query_rapport'):
            if cle in ctx:ctx[cle]=ctx[cle]+('&' if ctx[cle] else '')+urlencode({'modele_cible':cible.pk,'attendu_modele':ticket})
    reponse.status_code=statut
    return reponse


class ConservationForm(forms.Form):
    definition=forms.CharField(widget=forms.HiddenInput)
    nom=forms.CharField(label='Nom',max_length=100)
    nature=forms.ChoiceField(label='Conserver',choices=[('personnalisation','Une personnalisation — mes réglages habituels'),('modele','Un modèle — la définition du calcul et de sa présentation'),('ensemble','Un modèle et sa personnalisation')])
    nom_modele=forms.CharField(label='Nom du nouveau modèle (si vous conservez les deux)',max_length=100,required=False)
    from .periodes_rapports import PERIODES
    periode=forms.ChoiceField(label='Dates à retrouver lors des prochaines ouvertures',choices=[('','Garder les dates fixes'),*PERIODES.items()],required=False)
    decalage_debut=forms.IntegerField(label='Début en jours par rapport à aujourd’hui (autres bornes)',min_value=-36600,max_value=36600,required=False,initial=-6)
    decalage_fin=forms.IntegerField(label='Fin exclue en jours par rapport à aujourd’hui (autres bornes)',min_value=-36600,max_value=36600,required=False,initial=1)
    description=forms.CharField(label='Description du modèle (facultative)',max_length=6000,required=False,widget=forms.Textarea(attrs={'rows':3}))


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def conserver(request):
    from django.core import signing
    valeurs=request.POST if request.method=='POST' else request.GET
    token=valeurs.get('definition','')
    try:
        d=signing.loads(token,salt='reglages-rapport-v1',max_age=86400)
        if not isinstance(d,dict) or d.get('acteur')!=str(request.user.pk):raise signing.BadSignature()
    except (signing.BadSignature,TypeError,ValueError):return render(request,'rapports/conserver.html',{'erreur':'Cette définition n’est plus vérifiable. Revenez au rapport pour conserver vos réglages.'},status=409)
    cible=get_object_or_404(m.ModeleRapport,pk=d['cible'],auteur=request.user) if d.get('cible') else None
    source=d.get('source')
    if source not in (*c.SOURCES,'exploration'):raise Http404
    if source=='exploration':
        from .suivi import exiger
        exiger(request.user,'view_modelerapport','add_modelerapport')
    elif not peut_stockage(request.user,source):raise PermissionDenied
    initial={'definition':token,'nom':d.get('nom_saisi') or (cible.nom if cible else ''), 'nature':cible.nature if cible and cible.nature=='personnalisation' else 'modele' if source=='exploration' and not cible else 'personnalisation','description':cible.description if cible else ''}
    from .periodes_rapports import suggerer
    from django.utils import timezone
    initial.update(periode=suggerer(d['parametres'],timezone.localdate()),decalage_debut=d['parametres'].get('decalage_debut',-6),decalage_fin=d['parametres'].get('decalage_fin',1))
    f=ConservationForm(request.POST if request.method=='POST' else None,initial=initial);statut=200
    if 'date' in d['parametres'] and 'debut' not in d['parametres']:
        if initial.get('periode')=='date_relative' and not d['parametres'].get('periode'):
            from datetime import date
            initial['decalage_debut']=(date.fromisoformat(str(d['parametres']['date']))-timezone.localdate()).days
            f.initial['decalage_debut']=initial['decalage_debut']
        f.fields['periode'].choices=[('','Garder la date fixe'),*[(k,v) for k,v in f.fields['periode'].choices if k in ('aujourdhui','hier','demain','date_relative')]]
        f.fields['decalage_debut'].label='Date en jours par rapport à aujourd’hui'
        f.fields['decalage_fin'].widget=forms.HiddenInput()

    if request.method=='POST' and f.is_valid():
        try:
            from .periodes_rapports import resoudre
            params=d['parametres'].copy();params.update(periode=f.cleaned_data['periode'],decalage_debut=f.cleaned_data.get('decalage_debut') if f.cleaned_data.get('decalage_debut') is not None else -6,decalage_fin=f.cleaned_data.get('decalage_fin') if f.cleaned_data.get('decalage_fin') is not None else 1)
            try:params=resoudre(params)
            except (ValueError,OverflowError,TypeError) as e:raise ValidationError(str(e))
            params=s.valider(request.user,params)
            if request.POST.get('action')=='remplacer':
                if cible is None or cible.nature!=f.cleaned_data['nature']:raise ValidationError('Pour conserver un autre type de définition, enregistrez une nouvelle entrée.')
                x=s.changer(request.user,cible,d.get('attendu'),f.cleaned_data['nom'],params,description=f.cleaned_data['description'])
            elif request.POST.get('action')=='creer':
                if m.ModeleRapport.objects.filter(auteur=request.user).count()>=30:raise ValidationError('Limite de 30 définitions personnelles atteinte.')
                parent=(cible.modele_source if cible.nature=='personnalisation' else cible) if cible else None
                nature=f.cleaned_data['nature']
                structure=lambda p:{k:str(v) for k,v in p.items() if k in ('rapport','population','mesure','nombre_mesures','nombre_colonnes','niveaux','sous_totaux') or k.startswith(('mesure','axe','croisement','classes','colonne'))}
                if nature=='personnalisation' and cible and structure(params)!=structure(s.valider(request.user,d.get('base') or cible.parametres)):
                    raise ValidationError('Le calcul ou le classement a changé. Conservez un nouveau modèle, seul ou avec sa personnalisation.')
                from django.db import transaction
                with transaction.atomic():
                    if nature=='ensemble':
                        if not f.cleaned_data.get('nom_modele'):raise ValidationError('Nommez le modèle à conserver avec la personnalisation.')
                        if m.ModeleRapport.objects.filter(auteur=request.user).count()>28:raise ValidationError('Deux places sont nécessaires pour conserver les deux définitions.')
                        parent=m.ModeleRapport.objects.create(auteur=request.user,nom=f.cleaned_data['nom_modele'],nature='modele',description=f.cleaned_data['description'],parametres=params,source_catalogue=source)
                        nature='personnalisation'
                    empreinte=(s.etat(parent) if f.cleaned_data['nature']=='ensemble' else d.get('empreinte_base') or s.etat(parent)) if parent else ''
                    x=m.ModeleRapport.objects.create(auteur=request.user,nom=f.cleaned_data['nom'],nature=nature,description=f.cleaned_data['description'] if nature=='modele' else '',parametres=params,
                        modele_source=parent if nature=='personnalisation' else None,empreinte_source=empreinte if nature=='personnalisation' else '',source_catalogue=source+(':'+str(params.get('rapport','')) if source=='statistiques' else ''))
            else:raise ValidationError('Choisissez explicitement Enregistrer ou Remplacer.')
        except ValidationError as e:f.add_error(None,e.messages);statut=409 if isinstance(e,s.ConflitModele) else 400
        else:return redirect(c.ouvrir(x))
    route=reverse('dossiers:explorer') if source=='exploration' else reverse('dossiers:rapport_composer',args=[source]) if d.get('editeur') else reverse(c.SOURCES[source][1])
    reprise={**d['parametres'],'page':d.get('page','1')}
    if cible:reprise.update(modele_cible=cible.pk,attendu_modele=d.get('attendu',''))
    retour=route+'?'+urlencode(reprise)
    return render(request,'rapports/conserver.html',{'form':f,'cible':cible,'retour':retour},status=statut)
