from . import precisions_correction as precision
from django.template.response import TemplateResponse
import csv,json
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404,render
from django.http import HttpResponse,Http404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods,require_safe
from . import models as m,aides as s,bd6,dossier
from .forms_aides import TypeForm,AccordForm,RemiseForm,UsageForm
from .forms_hebergement import date_champ
from .champs_saisie import FormulaireMetier
from .vues_bd6 import traiter
from .exports import cellule_csv


def nav(request,a):
    ctx=dossier.lire(request,a) or dossier.creer(request,a,None,None)
    p={k:request.GET[k][:6000] for k in ('contexte_dossier','date_service','retour','retour_exploration') if k in request.GET}
    q=urlencode(p)
    if p.get('retour')=='jour':
        from .retour_service import url_jour
        ctx['retour_dossier']=url_jour(p.get('date_service'))
    return ctx,p,q


def url_accord(a,q):return reverse('dossiers:aide',args=[a.pk])+('?'+q if q else '')


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def catalogue(request,pk=None):
    from .suivi import exiger
    exiger(request.user,'view_typeaide','view_revisiontypeaide')
    objet=get_object_or_404(m.TypeAide,pk=pk) if pk else None
    f=None
    if pk or request.GET.get('nouveau'):
        exiger(request.user,'change_typeaide' if pk else 'add_typeaide')
        f=TypeForm(request.POST if request.method=='POST' else None,instance=objet,initial={'attendu':bd6.jeton(objet) if objet else s.jeton_catalogue()})
        if objet:precision.preparer(f)
        def action(**d):return s.cataloguer(request.user,objet=objet,**d)
        return traiter(request,f,'Définir un type d’aide',action,reverse('dossiers:types_aides'),objet or 'Catalogue des aides',
            explication='Unité et libellé seront conservés dans chaque accord. Modifier ce catalogue ne réécrit aucun accord ni remise existante.')
    return render(request,'aides/catalogue.html',{'types':m.TypeAide.objects.all().prefetch_related('revisions__auteur')})


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def accorder(request,pk,nature):
    s.droit(request.user,'add_accordaide')
    if nature not in dict(m.TypeAide.NATURES):raise Http404
    a=get_object_or_404(m.Accompagnement,pk=pk);ctx,p,q=nav(request,a)
    f=AccordForm(request.POST if request.method=='POST' else None,accompagnement=a,nature=nature,
        initial={'debut':max(a.debut,date_retenue(request,a)),'attendu':bd6.jeton(a),'beneficiaires':list(a.beneficiaires.values_list('pk',flat=True))})
    def action(**d):
        d.pop('motif',None)
        return s.accorder(request.user,a,**d)
    return traiter(request,f,'Autoriser — '+dict(m.TypeAide.NATURES)[nature],action,lambda x:url_accord(x,q),a.menage,
        catalogue_aides=reverse('dossiers:types_aides'),annuler=ctx.get('retour_dossier') or reverse('suivi:accompagnement',args=[a.pk]),
        explication='Autorisation distincte de la remise. Quantité globale pour les personnes cochées. Si la liste est vide, définir d’abord le type dans le catalogue des aides.')


@never_cache
@require_safe
@login_required
def fiche(request,pk):
    s.droit(request.user)
    a=get_object_or_404(m.AccordAide.objects.select_related('accompagnement__menage','prestataire','financeur'),pk=pk)
    ctx,p,q=nav(request,a.accompagnement);remises=list(a.remises.prefetch_related('beneficiaires','usages'))
    total=s.total(a);reste=a.quantite-total if a.quantite is not None else None
    return render(request,'aides/fiche.html',{'accord':a,'remises':remises,'total':total,'reste':reste,'query':q,
        'retour':ctx.get('retour_dossier') or reverse('suivi:accompagnement',args=[a.accompagnement_id]),
        'peut_realiser':a.debut<=timezone.localdate() and a.accompagnement.debut<=timezone.localdate(),'journaux':a.revisions.select_related('auteur'),'impression':request.GET.get('edition')=='impression',**ctx})


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def action(request,pk,action,remise_pk=None):
    s.droit(request.user)
    a=get_object_or_404(m.AccordAide,pk=pk);ctx,p,q=nav(request,a.accompagnement);url=url_accord(a,q)
    r=get_object_or_404(a.remises,pk=remise_pk) if remise_pk else None
    token=bd6.jeton(a)
    if action=='annuler':
        s.droit(request.user,'annuler_remiseaide' if r else 'annuler_accordaide')
        f=FormulaireMetier(request.POST if request.method=='POST' else None)
        f.fields['motif']=forms.CharField(label='Pourquoi cette saisie était-elle une erreur ?',max_length=240)
        f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=token)
        fn=lambda **d:s.annuler(request.user,a,remise=r.pk if r else None,**d)
    elif action in ('remettre','corriger_remise'):
        s.droit(request.user,'change_remiseaide' if r else 'add_remiseaide')
        initial={'date':r.date if r else date_remise_proposee(request,a),'quantite':r.quantite if r else None,'source':r.source if r else '',
            'beneficiaires':list((r or a).beneficiaires.values_list('pk',flat=True)),'attendu':token}
        f=RemiseForm(request.POST if request.method=='POST' else None,accord=a,initial=initial)
        if r:f.fields['beneficiaires'].disabled=True
        fn=lambda **d:s.remettre(request.user,a,correction=r.pk if r else None,**d)
    elif action=='usage' and r:
        s.droit(request.user,'add_usageaide')
        f=UsageForm(request.POST if request.method=='POST' else None,initial={'date':timezone.localdate(),'attendu':token})
        f.fields['motif'].required=False
        fn=lambda **d:s.constater(request.user,a,remise=r.pk,**d)
    elif action in ('corriger','prolonger'):
        s.droit(request.user,'change_accordaide')
        f=AccordForm(request.POST if request.method=='POST' else None,accompagnement=a.accompagnement,instance=a,initial={'attendu':token})
        f.fields.pop('type_aide');f.fields.pop('beneficiaires');f.fields['motif'].required=action=='prolonger'
        if action=='prolonger':
            for c in s.CHAMPS:
                if c not in ('fin','source'):f.fields[c].disabled=True
        fn=lambda **d:s.modifier(request.user,a,prolongation=action=='prolonger',**d)
    else:raise Http404
    if p.get('retour')=='jour':url=ctx.get('retour_dossier') or url
    return traiter(request,f,{'remettre':'Enregistrer une réalisation','corriger_remise':'Corriger une réalisation','annuler':'Annuler une saisie erronée','usage':'Constater l’utilisation déclarée','corriger':'Corriger l’autorisation','prolonger':'Prolonger l’autorisation'}[action]+' — '+a.libelle,fn,url,a.accompagnement.menage,
        explication='Unité : '+a.unite+'. '+a.precision+' Quantité globale, jamais multipliée par bénéficiaire. Les textes et versions restent conservés.')


class RapportForm(FormulaireMetier):
    debut=date_champ('Du (inclus)');fin=date_champ('Au (exclu)')
    nature=forms.ChoiceField(label='Prestation',choices=[('','Toutes les aides complémentaires'),*m.TypeAide.NATURES,('repas','Repas distribués')],required=False)
    q=forms.CharField(label='Nom de personne ou ménage',max_length=160,required=False)
    unite=forms.CharField(label='Unité exacte',max_length=40,required=False)
    prestataire_repas=forms.CharField(label='Prestataire de repas : libellé exact',max_length=160,required=False)
    service_repas=forms.ChoiceField(label='Service de repas',choices=[('','Tous'),*m.AccordRepas.SERVICES],required=False)
    categorie=forms.CharField(label='Catégorie déclarée de repas exacte',max_length=80,required=False)
    financeur=forms.ModelChoiceField(m.Partenaire.objects.all(),required=False)
    prestataire=forms.ModelChoiceField(m.Partenaire.objects.all(),required=False)
    mode=forms.ChoiceField(label='Compter',choices=[('remises','Réalisations dans la période'),('accords','Autorisations chevauchant la période')])
    def clean(self):
        d=super().clean()
        if d.get('fin') and d.get('debut') and d['fin']<=d['debut']:raise forms.ValidationError('La fin exclue doit suivre le début.')
        return d


@never_cache
@require_safe
@login_required
def rapport(request):
    s.droit(request.user)
    params=request.GET.copy();jour=timezone.localdate();params.setdefault('debut',jour.replace(day=1).isoformat());params.setdefault('fin',(jour+timedelta(days=1)).isoformat());params.setdefault('mode','remises')
    f=RapportForm(params);lignes=[];totaux={}
    if params.get('nature')=='repas':
        for champ in ('financeur','prestataire','unite'):f.fields.pop(champ,None)
        if params.get('mode')=='accords':f.fields.pop('categorie',None)
    else:
        for champ in ('prestataire_repas','service_repas','categorie'):f.fields.pop(champ,None)
    if f.is_valid():
        d=f.cleaned_data;repas=d['nature']=='repas';accords=d['mode']=='accords'
        if repas:
            from .repas import droit
            droit(request.user,'view_repasdistribue')
            if accords:
                qs=m.AccordRepas.objects.filter(annule_le__isnull=True,debut__lt=d['fin']).filter(Q(fin__isnull=True)|Q(fin__gt=d['debut'])).select_related('accompagnement__menage').prefetch_related('beneficiaires')
            else:
                qs=m.RepasDistribue.objects.filter(annule_le__isnull=True,date__gte=d['debut'],date__lt=d['fin']).select_related('accord__accompagnement__menage','beneficiaire')
                if d.get('categorie'):qs=qs.filter(categorie_declaree__iexact=d['categorie'])
            prefixe='' if accords else 'accord__'
            if d.get('prestataire_repas'):qs=qs.filter(**{prefixe+'prestataire__iexact':d['prestataire_repas']})
            if d.get('service_repas'):qs=qs.filter(**{prefixe+'service':d['service_repas']})

        else:
            qs=m.AccordAide.objects.filter(annule_le__isnull=True,debut__lt=d['fin']).filter(Q(fin__isnull=True)|Q(fin__gt=d['debut'])) if accords else m.RemiseAide.objects.filter(annule_le__isnull=True,accord__annule_le__isnull=True,date__gte=d['debut'],date__lt=d['fin'])
            prefixe='' if accords else 'accord__'
            for c in ('nature','unite','financeur','prestataire'):
                if d.get(c):qs=qs.filter(**{prefixe+c:d[c]})
            qs=qs.select_related(prefixe+'accompagnement__menage').prefetch_related('beneficiaires')
        if d['q']:
            chemin='accompagnement__' if accords else 'accord__accompagnement__'
            for mot in d['q'].split():qs=qs.filter(Q(**{chemin+'menage__libelle__icontains':mot})|Q(**{chemin+'beneficiaires__designation__icontains':mot})|Q(**{chemin+'beneficiaires__prenom__icontains':mot})).distinct()
        for x in qs.order_by('pk'):
            a=x if accords else x.accord
            unit=('repas autorisé théorique' if accords else 'repas') if repas else a.unite
            libelle=a.get_service_display() if repas else a.libelle
            personnes=[x.beneficiaire] if repas and not accords else list(x.beneficiaires.all())
            if repas and accords:
                jour=max(a.debut,d['debut']);borne=min(a.fin or d['fin'],d['fin']);nombre=0
                while jour<borne:
                    if not a.jours_semaine or jour.weekday() in a.jours_semaine:nombre+=1
                    jour+=timedelta(days=1)
                quantite=nombre*len(personnes)
            else:quantite=x.quantite
            cle=(libelle,unit,getattr(x,'categorie_declaree','') if repas else '',a.nature if not repas else 'repas',str(a.type_aide_id) if not repas else a.service)
            if quantite is not None:totaux[cle]=totaux.get(cle,Decimal('0'))+quantite
            lignes.append({'id':x.pk,'accord':a,'date':a.debut if accords else x.date,'libelle':libelle,'unite':unit,'quantite':quantite,
                'personnes':personnes,'categorie':getattr(x,'categorie_declaree','') if repas else '',
                'valeur_bon':a.valeur_bon if not repas else None,'devise':a.devise if not repas else '',
                'url':(reverse('suivi:accord_repas',args=[a.pk]) if repas else url_accord(a,''))+('' if accords else ('#repas-' if repas else '#remise-')+str(x.pk))})
        if request.GET.get('format')=='csv':
            response=HttpResponse(content_type='text/csv; charset=utf-8');response['Content-Disposition']='attachment; filename="prestations.csv"'
            w=csv.writer(response,delimiter=';');w.writerow(['mode','element_id','accord_id','date','libelle','unite','quantite','beneficiaires_ids','categorie','valeur_faciale_unitaire','devise'])
            for x in lignes:w.writerow([d['mode'],x['id'],x['accord'].pk,x['date'].isoformat(),cellule_csv(x['libelle']),cellule_csv(x['unite']),x['quantite'] if x['quantite'] is not None else '',','.join(str(p.pk) for p in x['personnes']),cellule_csv(x['categorie']),x['valeur_bon'] if x['valeur_bon'] is not None else '',x['devise']])
            return response
    params.pop('format',None);params.pop('page',None)
    return TemplateResponse(request,'aides/rapport.html',{'form':f,'page_obj':Paginator(lignes,40).get_page(request.GET.get('page')),'nombre':len(lignes),'totaux':list(totaux.items()),'query_rapport':params.urlencode()})


def date_retenue(request,accompagnement=None):
    from .vues_hebergement import jour_hebergement
    return jour_hebergement(request,accompagnement)


def date_remise_proposee(request,accord):
    jour=max(accord.debut,date_retenue(request,accord.accompagnement))
    bornes=[timezone.localdate()]
    for fin in (accord.fin,accord.accompagnement.fin):
        if fin:bornes.append(fin-timedelta(days=1))
    return min(jour,*bornes)


@never_cache
@require_safe
@login_required
def pdf(request,pk):
    from django.conf import settings
    from .pdf_aides import produire
    s.droit(request.user)
    a=get_object_or_404(m.AccordAide,pk=pk);remises=a.remises.prefetch_related('beneficiaires','usages')
    if request.GET.get('remise'):
        try:r=get_object_or_404(remises,pk=forms.IntegerField().clean(request.GET['remise']))
        except forms.ValidationError:raise Http404
        remises=[r]
    try:contenu=produire(a,remises,navigateur=getattr(settings,'MODE_PWA',False))
    except ValueError:return HttpResponse('Le document ne peut pas être généré avec les caractères présents.',status=422)
    response=HttpResponse(contenu,content_type='application/pdf');response['Content-Disposition']='attachment; filename="prestation-'+str(a.pk)+'.pdf"'
    response['Cache-Control']='private, no-store';response['X-Content-Type-Options']='nosniff'
    return response
