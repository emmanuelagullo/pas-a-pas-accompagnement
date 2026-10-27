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

UI={'csrfmiddlewaretoken','nom','action_modele','modele','modele_cible','attendu_modele','derive','page','format'}


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
    personnels=m.ModeleRapport.objects.filter(auteur=request.user)
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
        return redirect(reverse('dossiers:rapport_composer',args=[r['source']])+'?'+urlencode({'rapport':r['rapport']} if r.get('rapport') else {}))
    if not choix and not request.user.has_perm('personnes.view_personne'):raise PermissionDenied
    return render(request,'rapports/nouveau.html',{'rapports':choix,'personnels':m.ModeleRapport.objects.filter(auteur=request.user)})


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
    reponse=reponse_source(request,source,donnees)
    if not hasattr(reponse,'context_data'):return reponse
    ctx=reponse.context_data;statut=200;erreur=''
    ticket=valeurs.get('attendu_modele','')
    stockable=peut_stockage(request.user,source)
    if cible and stockable and request.method=='GET' and 'attendu_modele' not in valeurs:ticket=s.jeton(request.user,cible)
    if request.method=='POST':
        if not stockable:raise PermissionDenied
        try:
            params=parametres_response(reponse,source,donnees);nom=s.nom_valide(request.POST.get('nom',''))
            if request.POST.get('action_modele')=='remplacer':
                if cible is None:raise ValidationError('Choisissez votre rapport personnel à remplacer.')
                x=s.changer(request.user,cible,ticket,nom,params)
            elif request.POST.get('action_modele')=='creer':
                if m.ModeleRapport.objects.filter(auteur=request.user).count()>=30:raise ValidationError('Limite de 30 modèles personnels atteinte.')
                x=m.ModeleRapport.objects.create(auteur=request.user,nom=nom,parametres=params)
            else:raise ValidationError('Choisissez explicitement Enregistrer un second rapport ou Remplacer.')
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
