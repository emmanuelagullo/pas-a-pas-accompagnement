from django.template.response import TemplateResponse
import csv
from urllib.parse import urlencode
from django import forms
from django.contrib.auth.decorators import login_required,permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods,require_safe
from django.core.paginator import Paginator
from django.db.models import Q
from . import relations_personnelles as service,bd6,suivi
from .models import Personne,RevisionRelationPersonnelle
from .champs_saisie import FormulaireMetier
from .forms_hebergement import date_champ
from .vues_famille import ConsultationForm
from .vues_bd6 import navigation_histoire,traiter
from .exports import cellule_csv


class RelationForm(FormulaireMetier):
    autre=forms.ModelChoiceField(Personne.objects.none(),label='Autre personne connue',help_text='Aucune identité, appartenance ni prestation ne sera créée. Les homonymes restent distincts.')
    role=forms.ChoiceField(label='Lien depuis la personne de ce dossier',choices=[('','Choisir un lien'),*service.ROLES])
    debut=date_champ('Déclaration applicable depuis le (inclus)')
    fin=date_champ('Fin du lien exclue (si déjà terminée)',False)
    precision=forms.CharField(label='Précision du lien',max_length=240,required=False,widget=forms.Textarea(attrs={'rows':2}))
    source=forms.CharField(label='Comment cette relation est-elle connue ? (facultatif)',max_length=160,required=False)
    motif=forms.CharField(label='Motif de correction, de fin ou d’ajout antérieur',max_length=240,required=False)
    attendu=forms.CharField(widget=forms.HiddenInput)

    def __init__(self,*args,personne,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['autre'].queryset=Personne.objects.exclude(pk=personne.pk)
        self.fields['autre'].label_from_instance=lambda p:f'{p} · {p.naissance_affichee} · {str(p.pk)[:8]}'


def lignes(faits,personne):
    resultat=[]
    for x in faits:
        resultat.append({'fait':x,'autre':x.autre(personne),'libelle':x.libelle_depuis(personne)})
    return resultat


@never_cache
@require_http_methods(['GET','POST'])
@login_required
@permission_required(service.DROITS_LECTURE,raise_exception=True)
def histoire(request,pk,action=None,fait_pk=None):
    p=get_object_or_404(Personne,pk=pk)
    params,origine,retour,query=navigation_histoire(request,p)
    if request.GET.get('date'):query+=('&' if query else '')+urlencode({'date':request.GET['date'][:20]})
    base=reverse('dossiers:relations_personnelles',args=[p.pk])+('?'+query if query else '')
    attendu=bd6.jeton(p)
    faits=service.faits(p)
    x=get_object_or_404(faits,pk=fait_pk) if fait_pk else None
    if action:
        if action=='annuler':
            suivi.exiger(request.user,'annuler_relationpersonnelle')
            f=FormulaireMetier(request.POST if request.method=='POST' else None)
            f.fields['motif']=forms.CharField(label='Pourquoi ce lien était-il une erreur ?',max_length=240)
            f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=attendu)
            return traiter(request,f,'Annuler une relation erronée',lambda **d:service.annuler(request.user,p,x,**d),base,p,
                explication='Le fait et son journal restent conservés. Pour la fin d’un lien réel, utilisez Terminer le lien.')
        suivi.exiger(request.user,'add_relationpersonnelle')
        if x:suivi.exiger(request.user,'change_relationpersonnelle')
        initial={'attendu':attendu,'debut':timezone.localdate()}
        if x:
            initial.update(autre=x.autre(p),role=x.role_depuis(p),debut=x.debut if action!='changer' else timezone.localdate(),fin=x.fin if action!='changer' else None,
                precision=x.precision,source=x.source if action!='changer' else '')
        f=RelationForm(request.POST if request.method=='POST' else None,initial=initial,personne=p)
        if x:
            f.fields['autre'].disabled=True
            f.fields['autre'].help_text='Les deux personnes restent celles du lien. Si une personne était erronée, annulez la saisie puis déclarez le bon lien.'
        if action in ('corriger','clore'):f.fields['motif'].required=action=='clore'
        if action=='clore':
            for c in ('autre','role','debut','precision','source'):f.fields[c].disabled=True
            f.fields['fin'].required=True
        return traiter(request,f,{'corriger':'Corriger une relation','clore':'Terminer le lien','changer':'Le lien a changé'}.get(action,'Déclarer une relation'),
            lambda **d:service.enregistrer(request.user,p,correction=x.pk if action in ('corriger','clore') else None,remplace=x.pk if action=='changer' else None,cloture=action=='clore',**d),base,p,
            explication='Lien déclaré, sans reconnaissance juridique implicite. Il reste indépendant des ménages, des bénéficiaires, du contact du ménage et des professionnels. Les actions sont lisibles depuis les deux personnes ; un changement termine l’ancien lien et ouvre le nouveau à sa date.')
    f=ConsultationForm(request.GET if 'date' in request.GET else None,initial={'date':timezone.localdate()})
    jour=f.cleaned_data['date'] if f.is_bound and f.is_valid() else timezone.localdate()
    actifs=service.a_date(p,jour) if not f.errors else faits.none()
    if request.GET.get('format')=='csv' and not f.errors:
        response=HttpResponse(content_type='text/csv; charset=utf-8');response['Content-Disposition']='attachment; filename="relations-personnelles.csv"'
        w=csv.writer(response,delimiter=';');w.writerow(['date_reference','personne_id','personne','lien_id','role_depuis_personne','autre_id','autre','debut','fin','precision','source'])
        for r in lignes(actifs,p):
            x=r['fait'];autre=r['autre'];w.writerow([jour.isoformat(),p.pk,cellule_csv(p),x.pk,x.role_depuis(p),autre.pk,cellule_csv(autre),x.debut.isoformat(),x.fin.isoformat() if x.fin else '',cellule_csv(x.precision),cellule_csv(x.source)])
        return response
    return render(request,'dossiers/relations_personnelles.html',{'objet':p,'retour':retour,'consultation':f,'date_situation':jour,
        'actifs':lignes(actifs,p),'faits':lignes(faits,p),'query_relations':query,'parametres_relations':{**params,**origine},
        'revisions':RevisionRelationPersonnelle.objects.filter(relation__in=faits).select_related('auteur')})


class RapportForm(ConsultationForm):
    q=forms.CharField(label='Nom ou prénom de l’une des personnes',max_length=160,required=False)
    nature=forms.ChoiceField(label='Type de lien',choices=[('','Tous les liens'),('parent','Parent / enfant'),('couple','Couple'),('fratrie','Fratrie'),('proche','Proche'),('contact','Personne à contacter')],required=False)


@never_cache
@require_safe
@login_required
@permission_required(service.DROITS_LECTURE,raise_exception=True)
def rapport(request):
    from .models import RelationPersonnelle
    selection=request.GET.copy()
    if 'date' not in selection:selection['date']=timezone.localdate().isoformat()
    f=RapportForm(selection);faits=RelationPersonnelle.objects.none()
    if f.is_valid():
        d=f.cleaned_data;faits=RelationPersonnelle.objects.filter(debut__lte=d['date'],annule_le__isnull=True).filter(Q(fin__isnull=True)|Q(fin__gt=d['date']))
        if d['nature']:
            n={'parent':['parent_a','parent_b'],'contact':['contact_a','contact_b']}.get(d['nature'],[d['nature']]);faits=faits.filter(nature__in=n)
        for mot in d['q'].split():faits=faits.filter(Q(personne_a__designation__icontains=mot)|Q(personne_a__prenom__icontains=mot)|Q(personne_b__designation__icontains=mot)|Q(personne_b__prenom__icontains=mot))
        faits=faits.select_related('personne_a','personne_b').order_by('personne_a_id','personne_b_id','nature','pk')
        if request.GET.get('format')=='csv':
            response=HttpResponse(content_type='text/csv; charset=utf-8');response['Content-Disposition']='attachment; filename="liens-declares.csv"'
            w=csv.writer(response,delimiter=';');w.writerow(['date_reference','lien_id','personne_a_id','personne_a','role_depuis_a','personne_b_id','personne_b','debut','fin','precision','source'])
            for x in faits:w.writerow([d['date'].isoformat(),x.pk,x.personne_a_id,cellule_csv(x.personne_a),x.role_depuis(x.personne_a),x.personne_b_id,cellule_csv(x.personne_b),x.debut.isoformat(),x.fin.isoformat() if x.fin else '',cellule_csv(x.precision),cellule_csv(x.source)])
            return response
    selection.pop('format',None);selection.pop('page',None)
    return TemplateResponse(request,'dossiers/rapport_relations.html',{'form':f,'page_obj':Paginator(faits,50).get_page(request.GET.get('page')),'nombre':faits.count(),'query_rapport':selection.urlencode()})
