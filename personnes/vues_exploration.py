import csv
from datetime import timedelta
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from . import models as m,exploration as e
from .forms_exploration import ExplorationForm
from .exports import cellule_csv


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def explorer(request):
    e.disponibles(request.user)
    modele=get_object_or_404(m.ModeleRapport,pk=request.GET['modele'],auteur=request.user) if request.GET.get('modele') else None
    data=(modele.parametres.copy() if modele else (request.POST.copy() if request.method=='POST' else request.GET.copy()))
    if modele and not data.get('exploration'):return redirect('statistiques')
    if modele and data.get('schema')!=1:return HttpResponse('Version du modèle non prise en charge ; aucun résultat calculé.',status=409)
    jour=timezone.localdate()
    for c,v in dict(population='personnes',debut=jour.replace(day=1).isoformat(),fin=(jour+timedelta(days=1)).isoformat(),reference=jour.isoformat(),mesure='objets',axe='total',croisement='',classes='',filtre1='',operation1='egal',valeur1='',filtre2='',operation2='egal',valeur2='').items():data.setdefault(c,v)
    if data.get('periode'):
        from .vues_statistiques import bornes_periode
        try:
            debut,fin=bornes_periode(data['periode'],jour);data.update(debut=debut.isoformat(),fin=fin.isoformat(),reference=(fin-timedelta(days=1)).isoformat())
        except ValueError:pass
    if request.GET.get('ajouter_filtre'):
        try:n=int(data.get('filtres') or 2)
        except ValueError:n=2
        n=min(n+1,20);data['filtres']=str(n)
        data.setdefault('filtre'+str(n),'');data.setdefault('operation'+str(n),'egal');data.setdefault('valeur'+str(n),'')
    form=ExplorationForm(data,acteur=request.user);lignes=[];totaux={};nombre=0;selection=[]
    if form.is_valid():
        try:lignes,totaux,selection=e.calculer(request.user,form.cleaned_data);nombre=len(selection)
        except ValidationError as erreur:form.add_error(None,erreur)
        else:
            if request.method=='POST':
                from .suivi import exiger
                exiger(request.user,'add_modelerapport','view_modelerapport')
                nom=request.POST.get('nom','').strip()
                if not nom or len(nom)>100:form.add_error(None,'Nommez ce modèle (100 caractères au plus).')
                elif m.ModeleRapport.objects.filter(auteur=request.user).count()>=30:form.add_error(None,'Limite de 30 modèles atteinte ; retirez un ancien modèle avant d’en ajouter.')
                else:
                    params={k:str(v) if v is not None else '' for k,v in form.cleaned_data.items()};params.update(schema=1,exploration=True)
                    x=m.ModeleRapport.objects.create(auteur=request.user,nom=nom,parametres=params)
                    from django.urls import reverse
                    return redirect(reverse('dossiers:explorer')+'?modele='+str(x.pk))
            if request.GET.get('format')=='csv':
                r=HttpResponse(content_type='text/csv; charset=utf-8');r['Content-Disposition']='attachment; filename="exploration-fictive.csv"';w=csv.writer(r,delimiter=';');w.writerow(['Population','Référence','Mesure','Axe','Croisement','Unité','Valeur'])
                for x in lignes:w.writerow([cellule_csv(v) for v in [dict(e.POPULATIONS)[form.cleaned_data['population']],form.cleaned_data['reference'],form.cleaned_data['mesure'],x['axe'],x['croisement'],x['unite'],x['valeur']]])
                return r
            if request.GET.get('format')=='pdf':
                from .pdf_restitution import produire
                return produire(request,'Exploration — données fictives',[dict(e.POPULATIONS)[form.cleaned_data['population']],'Situation personnelle à la référence : '+str(form.cleaned_data['reference']),
                    'Période : '+str(form.cleaned_data['debut'])+' → '+str(form.cleaned_data['fin'])+' (fin exclue)',
                    'Paramètres : '+str({k:str(v) for k,v in form.cleaned_data.items()}),'Totaux distincts recalculés : '+str(totaux),
                    *[f'{x["axe"]} · {x["croisement"]} : {x["valeur"]} {x["unite"]}' for x in lignes],
                    'Les ventilations multi-valeurs ne sont pas additives. Une première entrée connue n’est pas une première entrée absolue.'],'exploration-fictive.pdf')
    query={c:str(form.data.get(c,'')) for c in form.fields};page=Paginator(lignes,50).get_page(request.GET.get('page'))
    from urllib.parse import urlencode
    return render(request,'exploration/rapport.html',{'form':form,'page_obj':page,'query_rapport':urlencode(query),'totaux':totaux,'quantites_inconnues':sum(x['quantite'] is None for x in selection) if form.is_valid() else 0,'nombre':nombre,'modele':modele,
        'modeles':[x for x in m.ModeleRapport.objects.filter(auteur=request.user) if x.parametres.get('exploration')]})


@never_cache
@require_http_methods(['POST'])
@login_required
def supprimer_modele(request,pk):
    from .suivi import exiger
    exiger(request.user,'view_modelerapport','add_modelerapport')
    x=get_object_or_404(m.ModeleRapport,pk=pk,auteur=request.user)
    if not x.parametres.get('exploration'):
        from django.http import Http404
        raise Http404
    x.delete()
    return redirect('dossiers:explorer')
