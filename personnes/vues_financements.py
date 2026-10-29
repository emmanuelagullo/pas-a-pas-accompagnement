from . import precisions_correction as precision
from django.template.response import TemplateResponse
import csv
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import OperationalError
from django.db.models import Q,Max
from django.http import Http404,HttpResponse
from django.shortcuts import get_object_or_404,render,redirect
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods,require_safe
from . import models as m,financements as s,bd6,dossier
from .forms_financements import TarifForm,CalculForm,LignesFormSet,ImputationsFormSet,EmissionForm
from .forms_hebergement import date_champ
from .champs_saisie import FormulaireMetier
from .vues_bd6 import traiter
from .exports import cellule_csv


def cible(request,nature,pk):
    if nature not in s.CIBLES:raise Http404
    a=get_object_or_404(s.CIBLES[nature],pk=pk);s.droit(request.user,a)
    ctx=dossier.lire(request,a.accompagnement) or dossier.creer(request,a.accompagnement,None,None)
    params={k:request.GET[k][:6000] for k in ('contexte_dossier','date_service','retour','retour_exploration') if k in request.GET}
    return a,ctx,urlencode(params)


def url(a,q=''):return reverse('dossiers:financement',args=[s.nature(a),a.pk])+('?' + q if q else '')


def retour_accord(a,q):
    nom='dossiers:aide' if s.nature(a)=='aide' else 'suivi:accord_'+s.nature(a)
    return reverse(nom,args=[a.pk])+('?' + q if q else '')


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def tarifs(request,pk=None):
    from .suivi import exiger
    exiger(request.user,'view_tarifprestation','view_versiontarif','view_partenaire')
    t=get_object_or_404(m.TarifPrestation,pk=pk) if pk else None
    # Retour construit uniquement depuis une cible existante, jamais depuis une URL libre.
    retour=reverse('dossiers:tarifs')
    if t or request.GET.get('nouveau'):
        exiger(request.user,'add_versiontarif','change_tarifprestation' if t else 'add_tarifprestation')
        v=t.versions.first() if t else None
        initial={c:getattr(v,c) for c in s.TARIF} if v else {'debut':timezone.localdate(),'devise':'EUR','actif':True}
        initial.update(attendu=bd6.jeton(t) if t else s.creation_tarif(),action='changement' if t else 'definition')
        f=TarifForm(request.POST if request.method=='POST' else None,initial=initial)
        precision.operation(f)
        f.fields['action'].choices=[x for x in f.fields['action'].choices if (x[0]!='definition')==bool(t)]
        return traiter(request,f,'Définir un tarif daté',lambda **d:s.definir_tarif(request.user,tarif=t,**d),retour,t or 'Catalogue des tarifs',
            explication='Chaque prix est conservé dans une version. Un nouveau prix ne recalcule aucun ancien financement.')
    return render(request,'financements/tarifs.html',{'tarifs':m.TarifPrestation.objects.prefetch_related('versions__auteur')})


@never_cache
@require_safe
@login_required
def fiche(request,nature,pk):
    a,ctx,q=cible(request,nature,pk);f=s.financement(a)
    v=f.versions.first() if f else None
    if f and request.GET.get('version'):
        try:n=int(request.GET['version'])
        except ValueError:raise Http404
        v=get_object_or_404(f.versions,version=n)
    return render(request,'financements/fiche.html',{'accord':a,'nature':nature,'financement':f,'version':v,'arrivees_annulees':isinstance(a,m.AccordHebergement) and a.sejours.filter(annule_le__isnull=False).exists(),
        'totaux':s.detail_totaux(v) if v else [],'query':q,'retour':retour_accord(a,q),
        'versions':f.versions.all() if f else [],'documents':m.DocumentFinancement.objects.filter(version__financement=f).select_related('annulation','auteur','version') if f else [],**ctx})


def lignes_initiales(v,champs,lien):return [{c:getattr(x,c) for c in champs} for x in getattr(v,lien).all()] if v else []


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def calcul(request,nature,pk):
    a,ctx,q=cible(request,nature,pk);s.droit(request.user,a,'add_versionfinancement')
    f=s.financement(a);v=f.versions.first() if f else None
    if not f:s.droit(request.user,a,'add_financementprestation')
    initial={c:getattr(v,c) for c in s.ENTETE} if v else {'debut':a.debut,'fin':a.fin,'devise':'EUR','prestataire':getattr(a,'prestataire',None) if nature=='aide' else None}
    initial.update(attendu=s.jeton(a),action='changement' if v else 'definition')
    data=request.POST.copy() if request.method=='POST' else None
    if data is not None and data.get('commande')=='tarifs':
        try:n=min(int(data.get('lignes-TOTAL_FORMS','0') or 0),101)
        except ValueError:n=0
        for i in range(n):
            try:t=m.VersionTarif.objects.filter(pk=data.get(f'lignes-{i}-tarif') or None).first()
            except ValueError:t=None
            if t:
                from .suivi import exiger
                exiger(request.user,'view_tarifprestation','view_versiontarif')
                for c,tc in [('libelle','libelle'),('unite','unite'),('categorie','categorie'),('prix','montant')]:data[f'lignes-{i}-{c}']=str(getattr(t,tc))
    proposition=''
    if data is not None and data.get('commande')=='faits':
        try:
            debut=forms.DateField().clean(data.get('debut'))
            fin=forms.DateField(required=False).clean(data.get('fin'))
            if debut<a.debut or fin and fin<=debut:raise ValidationError('Vérifiez la période avant de proposer les quantités.')
            suggestions=s.quantites_documentees(request.user,a,debut,fin)
            try:n=int(data.get('lignes-TOTAL_FORMS','0'))
            except ValueError:n=0
            for d in suggestions[:max(0,100-n)]:
                for c,valeur in d.items():data[f'lignes-{n}-{c}']=str(valeur) if valeur is not None else ''
                n+=1
            data['lignes-TOTAL_FORMS']=str(n)
            proposition='Quantités ajoutées depuis les faits actuellement enregistrés. Vérifiez la période, les unités, les quantités et complétez les prix avant d’enregistrer.' if suggestions else 'Aucun fait enregistré dans cette période ; aucune quantité proposée.'
        except ValidationError as e:proposition=' '.join(e.messages)
    if data is not None and data.get('commande') in ('ligne','imputation'):
        pref='lignes' if data['commande']=='ligne' else 'imputations'
        try:n=int(data.get(pref+'-TOTAL_FORMS','0'))
        except ValueError:n=0
        data[pref+'-TOTAL_FORMS']=str(min(n+1,101))
    form=CalculForm(data,initial=initial)
    precision.operation(form)
    form.fields['action'].choices=[x for x in form.fields['action'].choices if (x[0]!='definition')==bool(v)]
    lignes=LignesFormSet(data,prefix='lignes',initial=lignes_initiales(v,s.LIGNE,'lignes'))
    imputations=ImputationsFormSet(data,prefix='imputations',initial=lignes_initiales(v,s.IMPUTATION,'imputations'))
    statut=200
    if data is not None and data.get('commande','enregistrer')=='enregistrer':
        valid=[form.is_valid(),lignes.is_valid(),imputations.is_valid()]
        if all(valid):
            ls=[{k:d[k] for k in s.LIGNE} for d in lignes.cleaned_data if d and not d.get('DELETE')]
            imps=[{k:d[k] for k in s.IMPUTATION} for d in imputations.cleaned_data if d and not d.get('DELETE')]
            try:s.enregistrer(request.user,a,lignes=ls,imputations=imps,**form.cleaned_data)
            except (ValidationError,OperationalError) as e:
                if isinstance(e,ValidationError) and hasattr(e,'error_dict'):
                    for champ,messages in e.message_dict.items():form.add_error(champ if champ in form.fields else None,messages)
                else:form.add_error(None,' '.join(e.messages) if isinstance(e,ValidationError) else 'Écriture non confirmée ; rechargez avant de réessayer.')
                statut=409
            else:return redirect(url(a,q))
    return render(request,'financements/calcul.html',{'form':form,'lignes':lignes,'imputations':imputations,'proposition':proposition,'accord':a,'retour':url(a,q),**ctx},status=statut)


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def emission(request,nature,pk):
    a,ctx,q=cible(request,nature,pk);s.droit(request.user,a,'add_documentfinancement')
    f=EmissionForm(request.POST if request.method=='POST' else None,accord=a,initial={'attendu':s.jeton(a),'date':timezone.localdate(),'phase':'autorise'})
    return traiter(request,f,'Émettre un document numéroté',lambda **d:s.emettre(request.user,a,**d),
        lambda x:reverse('dossiers:document_financement',args=[x.pk])+('?' + q if q else ''),a.accompagnement.menage,annuler=url(a,q),
        explication='Le contenu, les coordonnées et les calculs seront figés. Une correction ultérieure nécessite une annulation motivée puis une nouvelle émission.')


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def document(request,pk):
    doc=get_object_or_404(m.DocumentFinancement.objects.select_related('version__financement'),pk=pk)
    a=doc.version.financement.accord;s.droit(request.user,a);ctx=dossier.lire(request,a.accompagnement) or dossier.creer(request,a.accompagnement,None,None)
    params={k:request.GET[k][:6000] for k in ('contexte_dossier','date_service','retour','retour_exploration') if k in request.GET};q=urlencode(params)
    if request.GET.get('annuler')=='1':
        s.droit(request.user,a,'add_annulationdocument')
        f=FormulaireMetier(request.POST if request.method=='POST' else None)
        f.fields['motif']=forms.CharField(label='Motif de l’annulation',max_length=240)
        f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=s.jeton(a))
        return traiter(request,f,'Annuler '+doc.numero,lambda **d:s.annuler_document(request.user,a,doc,**d),url(a,q),doc.numero,
            explication='Le contenu et le numéro restent conservés. Le statut d’annulation apparaît à chaque consultation et téléchargement.')
    if request.method=='POST':raise Http404
    if s.empreinte(doc.contenu)!=doc.empreinte:return HttpResponse('Le contenu conservé ne correspond plus à son empreinte ; réédition refusée.',status=409)
    if request.GET.get('format')=='pdf':
        from .pdf_financements import produire
        try:contenu=produire(doc,navigateur=getattr(settings,'MODE_PWA',False))
        except ValueError:return HttpResponse('Le document ne peut pas être généré avec les caractères présents.',status=422)
        response=HttpResponse(contenu,content_type='application/pdf')
        response['Cache-Control']='private, no-store';response['X-Content-Type-Options']='nosniff'
        response['Content-Disposition']='attachment; filename="'+doc.numero+'.pdf"';return response
    return render(request,'financements/document.html',{'document':doc,'retour':url(a,q),'query':q,**ctx})


class RapportForm(FormulaireMetier):
    debut=date_champ('Du (inclus)');fin=date_champ('Au (exclu)')
    phase=forms.ChoiceField(choices=m.LigneCout.PHASES,label='Phase')
    nature=forms.ChoiceField(choices=[('','Toutes'),('hebergement','Hébergement'),('repas','Repas'),('aide','Autres prestations')],required=False)
    q=forms.CharField(label='Personne ou ménage',max_length=160,required=False)
    reference=forms.CharField(label='Référence exacte du calcul',max_length=100,required=False)
    devise=forms.CharField(label='Devise exacte',max_length=3,required=False)
    unite=forms.CharField(label='Unité exacte',max_length=60,required=False)
    categorie=forms.CharField(label='Catégorie exacte',max_length=80,required=False)
    financeur=forms.ModelChoiceField(m.Partenaire.objects.all(),required=False)
    budget=forms.CharField(label='Budget exact',max_length=160,required=False)
    prescripteur=forms.ModelChoiceField(m.Partenaire.objects.all(),required=False)
    signataire=forms.ModelChoiceField(m.Intervenant.objects.all(),required=False)
    mode=forms.ChoiceField(choices=[('couts','Composantes de coût'),('imputations','Imputations de financement')],label='Afficher')
    def clean(self):
        d=super().clean()
        if d.get('debut') and d.get('fin') and d['fin']<=d['debut']:raise ValidationError('La fin exclue doit suivre le début.')
        if d.get('mode')=='couts' and (d.get('financeur') or d.get('budget')):raise ValidationError('Choisissez les imputations pour filtrer un financeur ou un budget ; un coût ne doit pas être multiplié par ses financeurs.')
        if d.get('mode')=='imputations' and (d.get('unite') or d.get('categorie')):raise ValidationError('Les imputations portent sur le total de la phase ; unité et catégorie filtrent les composantes de coût.')
        return d


@never_cache
@require_safe
@login_required
def rapport(request):
    s.droit(request.user)
    data=request.GET.copy();jour=timezone.localdate()
    for k,v in dict(debut=jour.replace(day=1).isoformat(),fin=(jour+timedelta(days=1)).isoformat(),phase='realise',mode='couts').items():data.setdefault(k,v)
    form=RapportForm(data);rows=[];totaux={}
    if form.is_valid():
        d=form.cleaned_data
        derniers=m.VersionFinancement.objects.values('financement_id').annotate(n=Max('version'))
        for dernier in derniers:
            v=m.VersionFinancement.objects.select_related('financement','prescripteur','signataire').get(financement_id=dernier['financement_id'],version=dernier['n'])
            a=v.financement.accord;s.droit(request.user,a)
            if a.annule_le or d.get('nature') and v.financement.nature!=d['nature'] or d.get('devise') and v.devise!=d['devise'].upper():continue
            if d.get('reference') and v.reference!=d['reference']:continue
            if d.get('q'):
                personnes=list(a.beneficiaires.all())
                texte=' '.join([str(a.accompagnement.menage),*(str(p) for p in personnes)]).casefold()
                if not all(mot.casefold() in texte for mot in d['q'].split()):continue
            if any(d.get(c) and getattr(v,c)!=d[c] for c in ('prescripteur','signataire')):continue
            if d['mode']=='imputations':
                if v.debut>=d['fin'] or v.fin and v.fin<=d['debut']:continue
                for i in v.imputations.filter(phase=d['phase']).select_related('financeur'):
                    if d.get('financeur') and i.financeur!=d['financeur'] or d.get('budget') and i.budget!=d['budget']:continue
                    rows.append({'lien':url(a)+'?version='+str(v.version)+'#imputation-'+str(i.pk),'menage':str(a.accompagnement.menage),'prestation':v.financement.nature,'version':v.version,'date':v.debut,'libelle':str(i.financeur),'unite':'','categorie':'','quantite':'','prix':'','montant':i.montant,'devise':v.devise,'budget':i.budget,'reference':i.reference,'source':v.source})
            else:
                for x in v.lignes.filter(phase=d['phase'],date__gte=d['debut'],date__lt=d['fin']):
                    if d.get('unite') and x.unite!=d['unite'] or d.get('categorie') and x.categorie!=d['categorie']:continue
                    rows.append({'lien':url(a)+'?version='+str(v.version)+'#cout-'+str(x.pk),'menage':str(a.accompagnement.menage),'prestation':v.financement.nature,'version':v.version,'date':x.date,'libelle':x.libelle,'unite':x.unite,'categorie':x.categorie,'quantite':x.quantite,'prix':x.prix,'montant':x.montant,'devise':v.devise,'budget':'','reference':v.reference,'source':x.justification})
        for r in rows:totaux[r['devise']]=totaux.get(r['devise'],Decimal('0'))+r['montant']
        if request.GET.get('format')=='csv':
            response=HttpResponse(content_type='text/csv; charset=utf-8');response['Content-Disposition']='attachment; filename="financements-fictifs.csv"'
            w=csv.writer(response,delimiter=';');champs=[c for c in (rows[0].keys() if rows else ['menage','prestation','version','date','libelle','unite','categorie','quantite','prix','montant','devise','budget','reference','source']) if c!='lien'];w.writerow(champs)
            for r in rows:w.writerow([cellule_csv(r[c]) for c in champs])
            return response
    data.pop('page',None);data.pop('format',None)
    page=Paginator(rows,50).get_page(request.GET.get('page'))
    return TemplateResponse(request,'financements/rapport.html',{'form':form,'lignes':page,'page_obj':page,'totaux':totaux,'query':data.urlencode(),'query_rapport':data.urlencode()})
