"""Même formulaire en place et en pleine page ; retours construits côté serveur."""
from datetime import date, timedelta
from urllib.parse import urlencode
from django import forms
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse, resolve
from django.core import signing
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import OperationalError
from django.utils import timezone
from . import models as m, collectifs as c, forms_collectifs as f, suivi

def retour(objet):
    if isinstance(objet,m.Accompagnement):return reverse('dossiers:prise',args=['menage',objet.menage_id,objet.pk])
    return reverse('dossiers:detail',args=['menage',objet.pk])

def retour_contexte(request,objet,action):
    ancre='#condition-sociale' if action=='composition' else '#titre-prestations'
    match=resolve(request.path_info)
    if match.view_name in ('dossiers:detail','dossiers:prise'):
        query=request.GET.copy()
        for cle in ('col_action','col_pk','col_nature','retour_col'):query.pop(cle,None)
        destination=request.path+('?' + query.urlencode() if query else '')+ancre
        return destination,signing.dumps([str(objet.pk),destination],salt='retour-collectif-v1')
    token=request.GET.get('retour_col','')
    if token:
        try:
            identifiant,destination=signing.loads(token,salt='retour-collectif-v1',max_age=86400)
            if identifiant==str(objet.pk):return destination,token
        except (signing.BadSignature,ValueError,TypeError):pass
    return retour(objet)+ancre,''

def preparer(request,objet,action,pk=None,nature=None):
    acteur=request.user;jour=timezone.localdate();cfg=c.profil(objet)
    if not cfg:raise PermissionDenied('Le parcours collectif n’est pas activé dans ce service.')
    p=None
    if pk:
        p=get_object_or_404(m.PrestationCollective,pk=pk,accompagnement=objet)
        v=p.courante;comp=v.composition;nature=p.nature
    else:comp=c.composition(objet,jour)
    data=request.POST if request.method=='POST' else None
    url=reverse('dossiers:collectif_action',args=['prise' if isinstance(objet,m.Accompagnement) else 'menage',objet.pk,action])
    query={k:str(v) for k,v in {'pk':pk,'nature':nature}.items() if v}
    retour_page,token=retour_contexte(request,objet,action)
    if token:query['retour_col']=token
    url+='?'+urlencode(query)
    titre={'composition':'Composition et situation du ménage','creation':'Nouvelle prestation collective','correction':'Corriger la prestation','prolongation':'Prolonger','depart':'Enregistrer le départ','annulation':'Annuler la prestation','lieu':'Changer de lieu','absence':'Enregistrer une absence','retour':'Enregistrer le retour d’absence','annuler_mouvement':'Annuler un mouvement erroné'}.get(action)
    if not titre:raise ValidationError('Action inconnue.')
    if action=='composition':
        suivi.exiger(acteur,'view_compositioncollective','add_compositioncollective')
        form=f.CompositionForm(data,objet=objet,jour=jour)
        faire=lambda **d:c.renseigner(acteur,objet,**d)
    elif action in ('creation','correction'):
        if not isinstance(objet,m.Accompagnement) or not comp:raise ValidationError('Renseignez d’abord la composition du groupe.')
        if nature not in dict(m.PrestationCollective.NATURES):raise ValidationError('Choisissez la famille de prestation.')
        suivi.exiger(acteur,'view_prestationcollective','view_compositioncollective','view_versionprestationcollective','view_couvertcollectif','change_prestationcollective' if p else 'add_prestationcollective')
        if cfg[nature]=='individuel':raise PermissionDenied('Utilisez le parcours individuel de cette famille.')
        form=f.PrestationForm(data,prise=objet,nature=nature,comp=comp,acteur=acteur,prestation=p)
        if p:
            def faire(attendu,couverts,**d):return c.modifier(acteur,p,attendu,'correction',couverts=couverts,**d)
        else:
            def faire(attendu,couverts,**d):return c.creer(acteur,objet,nature,comp,attendu,couverts,**d)
    elif action in ('lieu','absence'):
        if not p:raise ValidationError('Choisissez une prestation.')
        suivi.exiger(acteur,'add_mouvementcollectif','view_mouvementcollectif','change_prestationcollective')
        form=f.MouvementForm(data,prestation=p,action=action,acteur=acteur)
        faire=lambda **d:c.mouvement(acteur,p,action=action,**d)
    elif action in ('retour','annuler_mouvement'):
        if not p:raise ValidationError('Choisissez une prestation.')
        suivi.exiger(acteur,'change_mouvementcollectif','view_mouvementcollectif','change_prestationcollective')
        form=f.ActionForm(data,prestation=p,action='annulation' if action=='annuler_mouvement' else 'depart')
        if action=='retour':form.fields['date'].label='Date du retour d’absence'
        form.fields['mouvement']=forms.ModelChoiceField(p.mouvements.filter(annule_le__isnull=True,**({'nature':'absence','fin__isnull':True} if action=='retour' else {})))
        faire=lambda mouvement,attendu,date=None,motif='':c.reviser_mouvement(acteur,p,mouvement,attendu,date,action=='annuler_mouvement',motif)
    else:
        if not p:raise ValidationError('Choisissez une prestation.')
        suivi.exiger(acteur,'change_prestationcollective','view_prestationcollective','view_versionprestationcollective','view_couvertcollectif')
        form=f.ActionForm(data,prestation=p,action=action)
        def faire(attendu,date=None,motif=''):
            return c.modifier(acteur,p,attendu,action,motif=motif,**({'fin_prevue':date} if action=='prolongation' else {'fin':date} if action=='depart' else {}))
    return {'form':form,'titre':titre,'action_url':url,'retour':retour_page,'faire':faire}

@never_cache
@login_required
@require_http_methods(['GET','POST'])
def action(request,cible,pk,action):
    if cible not in ('prise','menage'):raise PermissionDenied
    objet=get_object_or_404(m.Accompagnement.objects.select_related('menage') if cible=='prise' else m.Menage.objects.all(),pk=pk)
    statut=200
    try:ctx=preparer(request,objet,action,request.GET.get('pk'),request.GET.get('nature'))
    except ValidationError as e:return render(request,'collectifs/erreur.html',{'erreur':' '.join(e.messages),'retour':retour(objet)},status=400)
    if request.method=='POST' and ctx['form'].is_valid():
        try:ctx['faire'](**ctx['form'].cleaned_data)
        except (ValidationError,OperationalError) as e:
            ctx['form'].add_error(None,' '.join(e.messages) if isinstance(e,ValidationError) else 'Écriture non confirmée. Rechargez avant de réessayer.');statut=409
        else:return redirect(ctx['retour'])
    elif request.method=='POST':statut=400
    return render(request,'collectifs/form.html',{'formctx':ctx},status=statut)

@never_cache
@login_required
@require_http_methods(['GET'])
def bilan(request,pk):
    suivi.exiger(request.user,'view_prestationcollective','view_versionprestationcollective','view_couvertcollectif','view_compositioncollective')
    prise=get_object_or_404(m.Accompagnement,pk=pk)
    try:
        debut=forms.DateField().clean(request.GET.get('debut') or prise.debut)
        fin=forms.DateField().clean(request.GET.get('fin') or timezone.localdate()+timedelta(days=1))
        lignes=[]
        for p in prise.prestations_collectives.all():
            v=p.courante;lignes.append({'prestation':p,'version':v,'volumes':c.bilan(v,debut,fin)})
    except (ValidationError,ValueError) as e:return render(request,'collectifs/erreur.html',{'erreur':str(e),'retour':retour(prise)},status=400)
    return render(request,'collectifs/bilan.html',{'prise':prise,'lignes':lignes,'debut':debut,'fin':fin,'retour':retour(prise)})
