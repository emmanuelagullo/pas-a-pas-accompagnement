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
    for action,champ,mini,maxi in [('ajouter_niveau','niveaux',2,7),('ajouter_mesure','nombre_mesures',1,9),('ajouter_colonne','nombre_colonnes',0,11)]:
        if request.GET.get(action):
            try:n=int(data.get(champ) or mini)
            except (ValueError,TypeError):n=mini
            n=min(n+1,maxi);data[champ]=str(n)
    form=ExplorationForm(data,acteur=request.user);lignes=[];totaux={};nombre=0;selection=[];qualite_mesures=[]
    if form.is_valid():
        try:
            mesures=list(dict.fromkeys([form.cleaned_data['mesure'],*[form.cleaned_data.get('mesure'+str(i)) for i in range(2,10) if form.cleaned_data.get('mesure'+str(i))]]))
            labels=dict(form.fields['mesure'].choices)
            for mesure in mesures:
                lignes_mesure,totaux_mesure,selection=e.calculer(request.user,{**form.cleaned_data,'mesure':mesure})
                for ligne in lignes_mesure:
                    ligne['mesure']=labels[mesure];ligne['niveaux_affiches']=[v for i,v in enumerate(ligne['niveaux'],3) if form.cleaned_data.get('axe'+str(i))]
                lignes.extend(lignes_mesure)
                if len(lignes)>2000:raise ValidationError('Plus de 2 000 cellules pour les mesures réunies : réduisez les axes ou mesures. Aucun résultat tronqué.')
                inconnus=e.mesures.inconnus(selection,mesure)
                if inconnus is not None:qualite_mesures.append((labels[mesure],inconnus))
                totaux.update({(labels[mesure]+' — '+u if len(mesures)>1 else u):v for u,v in totaux_mesure.items()})
            nombre=len(selection)
            from .exploration_releve import relever
            colonnes,details=relever(form.cleaned_data,selection,request.user)

        except ValidationError as erreur:
            form.add_error(None,erreur);lignes=[];totaux={};selection=[];qualite_mesures=[]
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
            if request.GET.get('format')=='csv_detail':
                r=HttpResponse(content_type='text/csv; charset=utf-8');r['Content-Disposition']='attachment; filename="exploration-detail-fictive.csv"';w=csv.writer(r,delimiter=';');w.writerow(['Objet','Date du fait / début',*colonnes])
                for x in details:w.writerow([cellule_csv(v) for v in [x['id'],x['date'],*x['valeurs']]])
                return r
            if request.GET.get('format')=='pdf_detail':
                from .pdf_restitution import produire
                return produire(request,'Relevé détaillé — données fictives',['Population : '+dict(e.POPULATIONS)[form.cleaned_data['population']], 'Paramètres : '+str({k:str(v) for k,v in form.cleaned_data.items()}), 'Colonnes : '+' · '.join(colonnes),*[x['id']+' · '+str(x['date'])+' · '+' · '.join(x['valeurs']) for x in details]],'exploration-detail-fictive.pdf')
            if request.GET.get('format')=='csv':
                r=HttpResponse(content_type='text/csv; charset=utf-8');r['Content-Disposition']='attachment; filename="exploration-fictive.csv"';w=csv.writer(r,delimiter=';');w.writerow(['Population','Référence','Mesure','Axe','Croisement',*['Niveau '+str(i) for i in range(3,8)],'Unité','Valeur','Déclarants sans valeur connue pour cette mesure'])
                for x in lignes:w.writerow([cellule_csv(v) for v in [dict(e.POPULATIONS)[form.cleaned_data['population']],form.cleaned_data['reference'],x['mesure'],x['axe'],x['croisement'],*x['niveaux'],x['unite'],x['valeur'],x['inconnus']]])
                return r
            if request.GET.get('format')=='pdf':
                from .pdf_restitution import produire
                return produire(request,'Exploration — données fictives',[dict(e.POPULATIONS)[form.cleaned_data['population']],'Situation personnelle à la référence : '+str(form.cleaned_data['reference']),
                    'Période : '+str(form.cleaned_data['debut'])+' → '+str(form.cleaned_data['fin'])+' (fin exclue)',
                    'Paramètres : '+str({k:str(v) for k,v in form.cleaned_data.items()}),'Totaux distincts recalculés : '+str(totaux),
                    *[f'{x["mesure"]} — '+ ' · '.join([x['axe'],x['croisement'],*x['niveaux']])+f' : {x["valeur"]} {x["unite"]}' for x in lignes],
                    'Les ventilations multi-valeurs ne sont pas additives. Une première entrée connue n’est pas une première entrée absolue.'],'exploration-fictive.pdf')
    if not form.is_valid():colonnes=[];details=[]
    query={c:str(form.data.get(c,'')) for c in form.fields};page=Paginator(details if form.cleaned_data.get('affichage')=='detail' else lignes,50).get_page(request.GET.get('page'))
    from urllib.parse import urlencode
    return render(request,'exploration/rapport.html',{'form':form,'colonnes_detail':colonnes,'qualite_mesures':qualite_mesures,'champs_courants':[f for f in form if f.name in ('population','debut','fin','reference','periode','mesure','axe','croisement')],'champs_complementaires':[f for f in form if f.name not in ('population','debut','fin','reference','periode','mesure','axe','croisement')],'niveaux_actifs':[i for i in range(3,8) if form.data.get('axe'+str(i))],'page_obj':page,'query_rapport':urlencode(query),'totaux':totaux,'quantites_inconnues':sum(x['quantite'] is None for x in selection) if form.is_valid() else 0,'nombre':nombre,'modele':modele,
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


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def echanger_modele(request,pk=None):
    from . import modeles_echange as echange
    from .suivi import exiger
    from django.urls import reverse
    from .champs_saisie import FormulaireMetier
    exiger(request.user,'view_modelerapport','add_modelerapport')
    if pk is not None:
        modele=get_object_or_404(m.ModeleRapport,pk=pk,auteur=request.user)
        try:contenu=echange.exporter(request.user,modele)
        except ValidationError as erreur:return HttpResponse(' '.join(erreur.messages),status=422,content_type='text/plain; charset=utf-8')
        r=HttpResponse(contenu,content_type='application/json');r['Content-Disposition']='attachment; filename="modele-exploration.json"';return r
    class ImportForm(FormulaireMetier):
        fichier=forms.FileField(label='Fichier JSON de modèle personnel',help_text='Paramètres uniquement, 64 Kio maximum. Les droits et critères sont revalidés ; aucun résultat ni dossier n’est importé.')
    form=ImportForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        try:
            x=echange.importer(request.user,form.cleaned_data['fichier'].read(echange.MAX_MODELE+1))
        except ValidationError as erreur:form.add_error('fichier',erreur)
        else:return redirect(reverse('dossiers:explorer')+'?modele='+str(x.pk))
    return render(request,'exploration/importer.html',{'form':form})
