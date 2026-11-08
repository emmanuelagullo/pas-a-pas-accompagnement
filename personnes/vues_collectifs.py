"""Même formulaire en place et en pleine page ; retours construits côté serveur."""
from datetime import date, timedelta
from urllib.parse import urlencode
from django import forms
from django.http import Http404, JsonResponse
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
from .prestation_navigation import rendre as render

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
    p=None
    if pk:
        p=get_object_or_404(m.PrestationCollective,pk=pk,accompagnement=objet)
        v=p.courante;comp=v.composition;nature=p.nature
    else:comp=c.composition(objet,jour)
    if not cfg and not p:raise PermissionDenied('Les nouvelles saisies de groupe ne sont pas activées dans ce service.')
    if not cfg:
        from acteurs.profils_collectifs import defaut
        cfg=defaut()
    data=request.POST if request.method=='POST' else None
    url=reverse('dossiers:collectif_action',args=['prise' if isinstance(objet,m.Accompagnement) else 'menage',objet.pk,action])
    query={k:str(v) for k,v in {'pk':pk,'nature':nature}.items() if v}
    retour_page,token=retour_contexte(request,objet,action)
    if token:query['retour_col']=token
    url+='?'+urlencode(query)
    titre={'composition':'Composition et situation du ménage','creation':'Nouveau séjour' if nature=='hebergement' else 'Nouvelle période de repas','correction':'Modifier le séjour' if nature=='hebergement' else 'Modifier la période de repas','prolongation':'Prolonger','depart':'Enregistrer le départ','annulation':'Annuler la prestation','lieu':'Changer de lieu','absence':'Enregistrer une absence','retour':'Enregistrer le retour d’absence','annuler_mouvement':'Annuler un mouvement erroné'}.get(action)
    if action=='consultation':
        if not p:raise ValidationError('Choisissez une prestation.')
        suivi.exiger(acteur,'view_prestationcollective','view_versionprestationcollective','view_couvertcollectif','view_compositioncollective')
        calcul=None
        if nature=='restauration' and (v.fin or v.fin_prevue):
            try:calcul=c.bilan(v,v.debut,(v.fin or v.fin_prevue)+timedelta(days=1))
            except ValidationError:pass
        return {'prestation':p,'version':v,'composition':comp,'calcul':calcul,'titre':'Séjour' if nature=='hebergement' else 'Période de repas','retour':retour_page,'mouvements':p.mouvements.all() if acteur.has_perm('personnes.view_mouvementcollectif') else []}
    if not titre:raise ValidationError('Action inconnue.')
    if action=='composition':
        suivi.exiger(acteur,'view_compositioncollective','add_compositioncollective')
        form=f.CompositionForm(data,objet=objet,jour=jour)
        faire=lambda **d:c.renseigner(acteur,objet,**d)
    elif action in ('creation','correction'):
        if not isinstance(objet,m.Accompagnement) or not comp:raise ValidationError('Renseignez d’abord la composition du groupe.')
        if nature not in dict(m.PrestationCollective.NATURES):raise ValidationError('Choisissez la famille de prestation.')
        suivi.exiger(acteur,'view_prestationcollective','view_compositioncollective','view_versionprestationcollective','view_couvertcollectif','change_prestationcollective' if p else 'add_prestationcollective')
        if not p and cfg[nature]=='individuel':raise PermissionDenied('Utilisez le parcours individuel de cette famille.')
        form=f.PrestationForm(data,prise=objet,nature=nature,comp=comp,acteur=acteur,prestation=p)
        form.objet_periode = 'le séjour' if nature == 'hebergement' else 'la période de repas'
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
        def faire(attendu, date=None, motif="", **donnees):
            if action == "prolongation":
                donnees["fin_prevue"] = date
            elif action == "depart":
                donnees["fin"] = date
            return c.modifier(acteur, p, attendu, action, motif=motif, **donnees)
    return {'composition':action=='composition','resolution_periode':action in ('creation','correction'),'proposer_nouvelle_prise':action == 'creation' and nature == 'hebergement' and (comp.accompagnement_id is None or acteur.has_perm('personnes.add_compositioncollective')),'form':form,'titre':titre,'action_url':url,'retour':retour_page,'faire':faire}

@never_cache
@login_required
@require_http_methods(['GET','POST'])
def action(request,cible,pk,action):
    if cible not in ('prise','menage'):raise PermissionDenied
    objet=get_object_or_404(m.Accompagnement.objects.select_related('menage') if cible=='prise' else m.Menage.objects.all(),pk=pk)
    statut=200
    try:ctx=preparer(request,objet,action,request.GET.get('pk'),request.GET.get('nature'))
    except ValidationError as e:return render(request,'collectifs/erreur.html',{'erreur':' '.join(e.messages),'retour':retour(objet)},status=400)
    if request.method == 'POST' and request.headers.get('X-Verifier-Prestation') == '1':
        if action not in ('creation', 'correction'):
            raise Http404
        from .validation_prestations import diagnostic
        return diagnostic(ctx['form'], objet, 'fin_prevue', request=request, proposer_nouvelle_prise=ctx['proposer_nouvelle_prise'])
    if action=='consultation':
        if request.method!='GET':raise PermissionDenied
        return render(request,'collectifs/consultation.html',ctx)
    if request.method=='POST' and (request.GET.get('apercu')=='1' or request.POST.get('calculer')):
        resultat=apercu(ctx['form'],objet,request)
        if request.GET.get('apercu')=='1':return JsonResponse(resultat)
        ctx['calcul']=resultat['message']
        if ctx['form'].is_valid():
            data=ctx['form'].data.copy()
            for ligne in ctx['form'].cleaned_data.get('couverts',[]):data['couverts_'+ligne['categorie']]=str(ligne['nombre'])
            ctx['form'].data=data
        return render(request,'collectifs/form.html',{'formctx':ctx})
    if request.method=='POST' and ctx['form'].is_valid():
        donnees = ctx['form'].cleaned_data.copy()
        if action in ('creation', 'correction'):
            from .validation_prestations import preparer_resolution
            donnees['prise_confirmee'] = preparer_resolution(
                request, ctx['form'], objet, 'fin_prevue',
                proposer_nouvelle_prise=ctx['proposer_nouvelle_prise'],
            )
            nouvelle = bool(getattr(ctx['form'], 'proposer_nouvelle_prise', False) and request.POST.get('nouvelle_prise'))
            if request.POST.get('nouvelle_prise') and not nouvelle:
                ctx['form'].add_error(None, 'La nouvelle prise en charge ne peut plus être créée avec ces dates.')
                return render(request, 'collectifs/form.html', {'formctx': ctx}, status=409)
            if nouvelle:
                donnees['nouvelle_prise'] = True
            if getattr(ctx['form'], 'jeton_fin', None):
                return render(request, 'collectifs/form.html', {'formctx': ctx})
        try:resultat=ctx['faire'](**donnees)
        except (ValidationError,OperationalError) as e:
            if isinstance(e, ValidationError):
                from .validation_prestations import reporter_erreur
                reporter_erreur(ctx['form'], e)
            else:
                ctx['form'].add_error(None, 'Écriture non confirmée. Rechargez avant de réessayer.')
            statut = 409
        else:
            if action == 'creation' and nouvelle:
                reponse = redirect(retour(resultat.accompagnement) + '#hebergement')
                reponse['X-Nouvelle-Prise'] = '1'
                return reponse
            reponse=redirect(ctx['retour'])
            if isinstance(resultat,m.PrestationCollective):reponse['X-Prestation-Collective']=str(resultat.pk)
            return reponse
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

def apercu(form,objet,request):
    if not isinstance(form,f.PrestationForm) or form.nature!='restauration':return ({'message':''})
    prix={}
    try:
        jour=forms.DateField().clean(request.POST.get('debut'))
        if 'offre' in form.fields:
            offre=form.fields['offre'].queryset.filter(pk=request.POST.get('offre') or None).first()
            if offre:prix={('diner_'+code if repas=='diner' else code):str(t.montant) for (code,repas),t in c.tarifs_offre(request.user,offre,jour,request.POST.get('devise','EUR')).items()}
        elif 'prestataire' in form.fields:
            pr=form.fields['prestataire'].clean(request.POST.get('prestataire'))
            prix={code:str(t.montant) for code,t in c.tarifs_proposes(request.user,getattr(pr,'pk',None),jour,form.comp.categories,request.POST.get('devise','EUR')).items()}
    except (ValidationError,ValueError):pass
    if not form.is_valid():return ({'prix':prix,'message':'Calcul incomplet : vérifiez les champs et les dates.'})
    d=dict(form.cleaned_data)
    if form.prestation and 'fin' not in form.fields:d['fin']=form.prestation.courante.fin
    fin=d.get('fin') or d.get('fin_prevue')
    try:
        c.verifier_version(m.PrestationCollective(accompagnement=objet,nature='restauration'),m.VersionPrestationCollective(**{k:v for k,v in d.items() if k in c.VERSION}))
        r=c.calcul_repas(d,d['couverts'],d['debut'],fin+timedelta(days=1)) if fin else None
    except ValidationError as e:return ({'message':' '.join(e.messages)})
    def cout(repas):
        quantite=sum(x['nombre'] for x in d['couverts']);champ='prix_diner' if repas=='diner' else 'prix'
        lignes=[(x['nombre'],x.get(champ) if x.get(champ) is not None else x.get('prix')) for x in d['couverts']]
        if any(n and p is None for n,p in lignes):return 'prix incomplet'
        from decimal import Decimal, ROUND_HALF_UP
        return str(sum((n*p for n,p in lignes if p is not None),Decimal('0')).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))+' '+d['devise']+' pour le groupe'
    par=' · '.join(('Par déjeuner : '+cout('dejeuner'),) if d['dejeuner'] and not d['diner'] else ('Par dîner : '+cout('diner'),) if d['diner'] and not d['dejeuner'] else ('Par déjeuner : '+cout('dejeuner'),'par dîner : '+cout('diner')))
    if not fin:return {'prix':prix,'message':par+' · Total de la période non calculable sans date de fin.'}
    total='total incomplet — prix non renseigné' if r['prix_inconnus'] else 'total calculé : '+str(r['cout'])+' '+d['devise']
    return ({'prix':prix,'message':par+' · Période : '+str(r['dejeuners'])+' déjeuners + '+str(r['diners'])+' dîners · '+str(r['repas'])+' repas · '+total+'. Montants calculés sur la période accordée, pas des distributions.'})
