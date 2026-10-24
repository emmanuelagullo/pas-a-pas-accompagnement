from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from . import models as m,continuite_hebergement as c,correction_repas as r,hebergement as h,dossier
from .champs_saisie import FormulaireMetier
from .forms_hebergement import date_champ
from .vues_bd6 import traiter


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def individualiser(request,pk):
    h.droit(request.user,'view_continuitesejour')
    s=get_object_or_404(m.Sejour,pk=pk);f=FormulaireMetier(request.POST if request.method=='POST' else None,initial={'date':timezone.localdate()})
    f.fields['date']=date_champ('Continuer individuellement depuis le')
    f.fields['motif']=forms.CharField(label='Motif',max_length=240)
    correction=hasattr(s,'individualisation')
    if correction:
        h.exiger(request.user,'change_continuitesejour','view_revisioncontinuite');f.initial['date']=s.individualisation.date
    else:h.exiger(request.user,'add_continuitesejour')
    f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=c.jeton_coupure(s) if correction else c.jeton(s))
    ctx=dossier.lire(request,s.accord.accompagnement)
    return traiter(request,f,'Corriger la date de continuité' if correction else 'Continuer le séjour collectif par personne',lambda **d:(c.corriger_coupure if correction else c.individualiser)(request.user,s,**d),
        ctx.get('retour_dossier') or reverse('suivi:accord_hebergement',args=[s.accord_id]),s.accord.accompagnement.menage,
        explication='L’histoire commune est conservée jusqu’à cette date. Un segment individuel continue ensuite pour chaque personne, avec son lieu et son absence en cours. Ce ne sont pas de nouvelles admissions. Vous pourrez agir sur une personne ou une sélection.')


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def repas(request,pk):
    from .repas import droit
    droit(request.user,'change_repasdistribue');h.exiger(request.user,'view_revisionrepas')
    x=get_object_or_404(m.RepasDistribue,pk=pk)
    f=FormulaireMetier(request.POST if request.method=='POST' else None,initial={'quantite':x.quantite,'categorie_declaree':x.categorie_declaree})
    f.fields['quantite']=forms.IntegerField(label='Nombre de repas réellement distribués',min_value=1,max_value=32767)
    f.fields['categorie_declaree']=forms.CharField(label='Catégorie déclarée (facultative)',max_length=80,required=False)
    f.fields['motif']=forms.CharField(label='Pourquoi la saisie précédente était-elle erronée ?',max_length=240)
    f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=r.jeton(x))
    ctx=dossier.lire(request,x.accord.accompagnement)
    return traiter(request,f,'Corriger une distribution',lambda **d:r.corriger(request.user,x,**d),ctx.get('retour_dossier') or reverse('suivi:accord_repas',args=[x.accord_id]),x.accord.accompagnement.menage)


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def lieu(request,pk=None):
    from .forms_hebergement import LieuForm
    from . import bd6
    from django.shortcuts import render
    h.droit(request.user,'view_lieuhebergement');h.exiger(request.user,'view_revisionlieu')
    if pk:
        h.exiger(request.user,'change_lieuhebergement')
        x=get_object_or_404(m.LieuHebergement,pk=pk)
        f=LieuForm(request.POST if request.method=='POST' else None,instance=x,acteur=request.user)
        if 'organisme' not in f.fields:
            f.fields['organisme']=forms.ModelChoiceField(m.Partenaire.objects.none(),required=False,disabled=True);f.initial['organisme']=x.organisme_id
        f.fields['motif']=forms.CharField(label='Pourquoi les informations précédentes étaient-elles erronées ?',max_length=240)
        f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=bd6.jeton(x))
        return traiter(request,f,'Corriger un lieu',lambda **d:h.corriger_lieu(request.user,x,**d),reverse('dossiers:lieux_c'),x)
    return render(request,'aides/lieux.html',{'lieux':m.LieuHebergement.objects.select_related('parent').prefetch_related('revisions__auteur')})


@never_cache
@login_required
def rapport_hebergement(request):
    from django.views.decorators.http import require_safe
    from django.core.exceptions import PermissionDenied
    from django.http import HttpResponse
    from django.db.models import Q
    from django.shortcuts import render
    from datetime import timedelta
    import csv
    from .exports import cellule_csv
    h.droit(request.user,'view_continuitesejour');h.exiger(request.user,'view_affectation','view_absence','view_lieuhebergement')
    if request.method not in ('GET','HEAD'):return HttpResponse(status=405)
    class Consultation(FormulaireMetier):
        debut=date_champ('Du (inclus)');fin=date_champ('Au (exclu)')
        personne=forms.ModelChoiceField(m.Personne.objects.all(),required=False)
        def clean(self):
            d=super().clean()
            if d.get('debut') and d.get('fin') and not 0<(d['fin']-d['debut']).days<=732:raise forms.ValidationError('Choisissez une période positive de deux ans au plus pour ce détail.')
            return d
    p=request.GET.copy();p.setdefault('debut',timezone.localdate().replace(day=1).isoformat());p.setdefault('fin',(timezone.localdate()+timedelta(days=1)).isoformat())
    f=Consultation(p);lignes=[]
    if f.is_valid():
        d=f.cleaned_data
        qs=m.Sejour.objects.filter(debut__lt=d['fin']).filter(Q(fin__isnull=True)|Q(fin__gt=d['debut'])).select_related('accord__accompagnement__menage').prefetch_related('beneficiaires','absences','affectations__lieu')
        if d.get('personne'):qs=qs.filter(beneficiaires=d['personne'])
        for s in qs:
            a=max(s.debut,d['debut']);b=min(s.fin or d['fin'],d['fin']);nuits=set();jour=a
            while jour<b:nuits.add(jour);jour+=timedelta(days=1)
            absentes={j for j in nuits if any(x.debut<=j and (x.fin is None or x.fin>j) for x in s.absences.all())}
            for personne in s.beneficiaires.all():
                if d.get('personne') and personne.pk!=d['personne'].pk:continue
                lignes.append({'sejour':s,'personne':personne,'origine':s.origine_collective_id or s.pk,'nuits':len(nuits),'hors_absences':len(nuits-absentes),
                    'lieux':'; '.join(dict.fromkeys(str(x.lieu) for x in s.affectations.all() if x.debut<b and (x.fin is None or x.fin>a)))})
        if request.GET.get('format')=='csv':
            response=HttpResponse(content_type='text/csv; charset=utf-8');response['Content-Disposition']='attachment; filename="hebergement-individuel.csv"'
            w=csv.writer(response,delimiter=';');w.writerow(['episode_initial','fragment','personne_id','personne','debut_fragment','fin_fragment_exclue','nuits_theoriques_selection','hors_absences_declarees','lieux'])
            for x in lignes:w.writerow([x['origine'],x['sejour'].pk,x['personne'].pk,cellule_csv(x['personne']),x['sejour'].debut,x['sejour'].fin or '',x['nuits'],x['hors_absences'],cellule_csv(x['lieux'])])
            return response
    p.pop('format',None)
    return render(request,'aides/hebergement_individuel.html',{'form':f,'lignes':lignes,'query':p.urlencode()})


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def service_repas(request,pk):
    from copy import deepcopy
    from . import accords
    from .forms_repas import ServicesForm
    from .repas import droit
    droit(request.user,'change_accordrepas');h.exiger(request.user,'view_revisionservicerepas')
    x=get_object_or_404(m.AccordRepas,pk=pk)
    f=FormulaireMetier(request.POST if request.method=='POST' else None,initial={'jours_semaine':x.jours_semaine,'prestataire':x.prestataire})
    f.fields['jours_semaine']=deepcopy(ServicesForm.base_fields['jours_semaine'])
    f.fields['prestataire']=forms.CharField(label='Prestataire déclaré',max_length=160,required=False)
    f.fields['motif']=forms.CharField(label='Motif de correction',max_length=240)
    f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=accords.jeton(x))
    ctx=dossier.lire(request,x.accompagnement)
    return traiter(request,f,'Corriger les jours ou le prestataire du service',lambda **d:r.corriger_service(request.user,x,**d),ctx.get('retour_dossier') or reverse('suivi:accord_repas',args=[x.pk]),x.accompagnement.menage)
