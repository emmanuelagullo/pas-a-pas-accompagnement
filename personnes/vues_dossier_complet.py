"""Deux rubriques du dossier et une recherche transversale, sans nouveau menu."""
import csv,json
from urllib.parse import urlencode
from django import forms
from django.contrib.auth.decorators import login_required,permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404,HttpResponse
from django.shortcuts import get_object_or_404,render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods,require_safe
from . import dossier_complet as service,bd6,suivi,models as m
from . import presentation_dossier_complet as presentation
from .forms_dossier_complet import FORMULAIRES,AdministrationForm
from .champs_saisie import FormulaireMetier,valeurs_proposees
from .vues_bd6 import navigation_histoire,traiter
from .vues_famille import ConsultationForm
from .forms_hebergement import date_champ
from .exports import cellule_csv


def rubrique(code):
    if code not in service.RUBRIQUES:raise Http404
    return service.RUBRIQUES[code]


def navigation(request,p,groupe,code=None):
    params,origine,retour,query=navigation_histoire(request,p)
    jour=timezone.localdate()
    if request.GET.get('date'):
        try:jour=forms.DateField().clean(request.GET['date'])
        except forms.ValidationError:pass
    valeurs={**params,**origine,'date':request.GET.get('date',jour.isoformat())[:20]}
    if code:valeurs['rubrique']=code
    query=urlencode(valeurs)
    return jour,retour,query,reverse('dossiers:fiche_a',args=[p.pk,groupe])+'?'+query,valeurs


@never_cache
@require_http_methods(['GET','POST'])
@login_required
@permission_required(service.ADMIN_LECTURE,raise_exception=True)
def administration(request,pk,action=None,fait_pk=None):
    p=get_object_or_404(m.Personne,pk=pk)
    jour,retour,query,base,params=navigation(request,p,'droits','administration')
    attendu=bd6.jeton(p);faits=p.situations_administratives.select_related('auteur')
    if action:
        suivi.exiger(request.user,'add_situationadministrative')
        corrigee=get_object_or_404(faits,pk=fait_pk) if fait_pk else None
        if corrigee:suivi.exiger(request.user,'change_situationadministrative')
        initial,proposition=valeurs_proposees(request,faits,service.ADMIN_CHAMPS,corrigee);initial['attendu']=attendu
        f=AdministrationForm(request.POST if request.method=='POST' else None,initial=initial)
        if corrigee:f.fields['motif'].required=False
        return traiter(request,f,'Corriger une situation administrative' if corrigee else 'Renseigner la situation administrative',
            lambda **d:service.administration(request.user,p,correction=corrigee.pk if corrigee else None,**d),base,p,**proposition,
            explication='Renseignements déclarés sur cette personne. Identifiants textuels, dates exactes ou estimées explicites ; aucune déduction depuis la nationalité, le ménage ou les prestations.')
    raise Http404


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def modifier(request,pk,code,action,fait_pk=None):
    r=rubrique(code);service.exiger_lecture(request.user,code)
    p=get_object_or_404(m.Personne,pk=pk);jour,retour,query,base,params=navigation(request,p,r.groupe,code)
    attendu=bd6.jeton(p);faits=service.faits(code,[p]);x=get_object_or_404(faits,pk=fait_pk) if fait_pk else None
    if action=='annuler':
        suivi.exiger(request.user,'annuler_'+r.modele._meta.model_name)
        f=FormulaireMetier(request.POST if request.method=='POST' else None)
        f.fields['motif']=forms.CharField(label='Pourquoi cette déclaration était-elle une erreur ?',max_length=240)
        f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=attendu)
        return traiter(request,f,'Annuler une saisie erronée — '+r.titre,lambda **d:service.annuler(request.user,code,p,x,**d),base,p,
            explication='Le fait et ses versions restent conservés ; il sera exclu des consultations courantes. Terminer une déclaration réelle utilise une fin effective.')
    if action not in ('nouveau','corriger','changer','clore','absence'):raise Http404
    suivi.exiger(request.user,'add_'+r.modele._meta.model_name)
    if x or action=='absence':suivi.exiger(request.user,'change_'+r.modele._meta.model_name)
    if action in ('corriger','changer','clore') and x is None:raise Http404
    initial={c:getattr(x,c) for c in r.champs} if x else {}
    initial.update(attendu=attendu,debut=x.debut if x and action!='changer' else jour,fin=x.fin if x and action!='changer' else None,source=x.source if x and action!='changer' else '')
    if action=='absence':initial.update(etat='aucun')
    f=FORMULAIRES[code](request.POST if request.method=='POST' else None,initial=initial)
    if x and action in ('corriger','clore'):f.fields['motif'].required=action=='clore'
    if action=='clore':
        for c in (*r.champs,'debut','source'):f.fields[c].disabled=True
        f.fields['fin'].required=True
    if action=='absence':
        f.fields['etat'].choices=[('aucun','Absence déclarée'),('inconnu','Information non connue')]
        for c in r.champs:
            if c!='etat':
                f.initial[c]=r.modele._meta.get_field(c).get_default();f.fields[c].disabled=True;f.fields[c].widget=forms.HiddenInput()
        f.fields['remplacer_ensemble']=forms.BooleanField(label='Je confirme le changement pour toute cette rubrique',
            help_text='Les déclarations applicables à cette date seront terminées, sans les effacer. Les autres rubriques ne changent pas.')
    return traiter(request,f,{'nouveau':'Ajouter une déclaration','absence':'Déclarer une absence ou une information non connue','changer':'La situation a changé','corriger':'Corriger une erreur','clore':'Terminer la déclaration'}[action]+' — '+r.titre,
        lambda **d:service.enregistrer(request.user,code,p,correction=x.pk if action in ('corriger','clore') else None,remplace=x.pk if action=='changer' else None,cloture=action=='clore',**d),base,p,
        explication='Montants et situations déclarés, distincts des prestations et des décisions. Une fin effective ne doit pas être future ; une échéance annoncée reste une prévision. Aucun droit ou paiement n’est créé automatiquement.')


def bloc(acteur,code,p,jour,query):
    r=rubrique(code);qs=service.faits(code,[p]);actifs=list(service.applicables(qs,jour))
    revisions=r.journal.objects.filter(fait__personne=p).select_related('auteur')
    journaux=[{'revision':j,'avant':[presentation.snapshot(code,x) for x in j.avant],
        'apres':[presentation.snapshot(code,x) for x in j.apres]} for j in revisions]
    return {'code':code,'titre':r.titre,'modele':r.modele._meta.model_name,'query':query,
        'peut_ajouter':acteur.has_perm('personnes.add_'+r.modele._meta.model_name),
        'peut_modifier':acteur.has_perm('personnes.change_'+r.modele._meta.model_name),
        'peut_annuler':acteur.has_perm('personnes.annuler_'+r.modele._meta.model_name),
        'actifs':presentation.preparer(code,actifs,jour,acteur),'faits':presentation.preparer(code,qs,jour,acteur),
        'totaux':service.totaux(code,actifs) if code in ('ressources','dettes') else [],'journaux':journaux}


@never_cache
@require_safe
@login_required
@permission_required('personnes.view_personne',raise_exception=True)
def fiche(request,pk,groupe):
    if groupe not in ('economique','droits','histoire'):raise Http404
    p=get_object_or_404(m.Personne,pk=pk);jour,retour,query,base,params=navigation(request,p,groupe)
    consultation=ConsultationForm(request.GET if 'date' in request.GET else None,initial={'date':jour})
    if consultation.is_bound and consultation.is_valid():jour=consultation.cleaned_data['date']
    autorises=[c for c,r in service.RUBRIQUES.items() if r.groupe==groupe and request.user.has_perms(service.droits_lecture(c))]
    lecture_admin=groupe=='droits' and request.user.has_perms(service.ADMIN_LECTURE)
    if not autorises and not lecture_admin:raise PermissionDenied
    selection=request.GET.get('rubrique','administration' if lecture_admin else autorises[0] if autorises else '')
    if selection not in [*autorises,'administration','toutes']:raise Http404
    if selection=='administration' and not lecture_admin:raise PermissionDenied
    if groupe=='economique':selection='toutes'
    params['rubrique']=selection;query=urlencode(params)
    blocs=[];liens=[]
    if not consultation.errors:
        for code in autorises:
            q=params.copy();q['rubrique']=code;q=urlencode(q)
            n=service.a_date(code,[p],jour).count()
            liens.append((service.RUBRIQUES[code].titre,n,'?'+q))
            if selection in (code,'toutes'):blocs.append(bloc(request.user,code,p,jour,q))
    admin=service.administration_a_date([p],jour).first() if lecture_admin and not consultation.errors else None
    admin_faits=[{'fait':x,'lignes':presentation.lignes(m.SituationAdministrative,x,service.ADMIN_CHAMPS)} for x in p.situations_administratives.select_related('auteur')] if lecture_admin and selection in ('administration','toutes') else []
    admin_revisions=[]
    if lecture_admin and selection in ('administration','toutes'):
        for j in p.revisionsituationadministrative_set.select_related('auteur'):
            def etats(vals):return [{'debut':x['debut'],'fin':x['fin'],'source':x['source'],'lignes':[(m.SituationAdministrative._meta.get_field(c).verbose_name,presentation.valeur(m.SituationAdministrative._meta.get_field(c),x.get(c))) for c in service.ADMIN_CHAMPS]} for x in vals]
            admin_revisions.append({'revision':j,'avant':etats(j.avant),'apres':etats(j.apres)})
    return render(request,'dossiers/fiche_a.html',{'objet':p,'groupe':groupe,'retour':retour,'consultation':consultation,'date_situation':jour,
        'query_fiche':query,'parametres_fiche':{k:v for k,v in params.items() if k!='date'},'blocs':blocs,'liens_rubriques':liens,
        'lecture_admin':lecture_admin,'admin_affiche':lecture_admin and selection in ('administration','toutes'),
        'admin':admin,'admin_lignes':presentation.lignes(m.SituationAdministrative,admin,service.ADMIN_CHAMPS) if admin else [],'admin_faits':admin_faits,'admin_revisions':admin_revisions})


class RapportForm(FormulaireMetier):
    date=date_champ('Déclarations applicables au')
    rubrique=forms.ChoiceField(label='Rubrique')
    q=forms.CharField(label='Nom ou prénom',max_length=160,required=False)
    texte=forms.CharField(label='Libellé ou référence contenant',max_length=160,required=False)
    etat=forms.ChoiceField(label='État',choices=[('','Tous les états'),*m.FaitPersonnelDate._meta.get_field('etat').choices],required=False)
    devise=forms.CharField(label='Devise',max_length=3,required=False)
    montant_min=forms.DecimalField(label='Montant minimal',min_value=0,max_digits=14,decimal_places=2,required=False)
    montant_max=forms.DecimalField(label='Montant maximal',min_value=0,max_digits=14,decimal_places=2,required=False)
    echeance_avant=date_champ('Échéance prévue au plus tard le',False)
    organisme=forms.ModelChoiceField(m.Partenaire.objects.all(),label='Organisme déclaré',required=False)
    periodicite=forms.ChoiceField(label='Périodicité',choices=[('','Toutes les périodicités'),*[(k,v) for k,v in m.RessourcePersonnelle._meta.get_field('periodicite').choices if k]],required=False)
    nature=forms.ChoiceField(label='Détails ou total déclaré',choices=[('','Les deux'),*m.DettePersonnelle._meta.get_field('nature').choices],required=False)
    domaine=forms.ChoiceField(label='Portée de la mesure',choices=[('','Toutes'),*[(k,v) for k,v in m.ProtectionJuridique._meta.get_field('domaine').choices if k]],required=False)
    representant=forms.ModelChoiceField(m.Personne.objects.all(),label='Représentant personne déclaré',required=False)
    representant_professionnel=forms.ModelChoiceField(m.Intervenant.objects.all(),label='Professionnel représentant déclaré',required=False)
    identifiants=forms.BooleanField(label='Afficher et exporter les identifiants administratifs',required=False,
        help_text='Désactivé par défaut. La recherche textuelle ne les utilise que si cette case est cochée.')

    def clean(self):
        d=super().clean()
        if d.get('montant_min') is not None and d.get('montant_max') is not None and d['montant_min']>d['montant_max']:raise forms.ValidationError('Le montant minimal dépasse le maximal.')
        return d


@never_cache
@require_safe
@login_required
@permission_required('personnes.view_personne',raise_exception=True)
def rapport(request):
    choix=[(c,r.titre) for c,r in service.RUBRIQUES.items() if request.user.has_perms(service.droits_lecture(c))]
    if request.user.has_perms(service.ADMIN_LECTURE):choix.append(('administration','Situation administrative'))
    if not choix:raise PermissionDenied
    selection=request.GET.copy();selection.setdefault('date',timezone.localdate().isoformat());selection.setdefault('rubrique',choix[0][0])
    code=selection.get('rubrique')
    if code not in dict(choix):raise PermissionDenied
    admin=code=='administration';r=service.RUBRIQUES.get(code)
    f=RapportForm(selection);f.fields['rubrique'].choices=choix
    inutiles=set()
    if admin:inutiles|={'etat','devise','montant_min','montant_max','organisme','periodicite','nature','domaine','representant','representant_professionnel'}
    else:inutiles.add('identifiants')
    if code not in ('ressources','dettes'):inutiles|={'devise','montant_min','montant_max'}
    if code!='ressources':inutiles.add('periodicite')
    if code!='dettes':inutiles.add('nature')
    if code!='protections':inutiles|={'domaine','representant','representant_professionnel'}
    if r and 'echeance_prevue' not in r.champs:inutiles.add('echeance_avant')
    if r and 'organisme' not in r.champs:inutiles.add('organisme')
    for c in inutiles:f.fields.pop(c,None)
    objets=[];lignes=[];totaux=[];journaux=[];champs=[]
    if f.is_valid():
        d=f.cleaned_data;jour=d['date'];ps=m.Personne.objects.all()
        for mot in d['q'].split():ps=ps.filter(Q(designation__icontains=mot)|Q(prenom__icontains=mot))
        model=m.SituationAdministrative if admin else r.modele
        champs=list(service.ADMIN_CHAMPS if admin else r.champs)
        if admin and not d.get('identifiants'):champs=[c for c in champs if c not in ('numero_ss','numero_caf')]
        qs=service.administration_a_date(ps,jour) if admin else service.a_date(code,ps,jour)
        qs=qs.select_related('personne')
        if d.get('etat'):qs=qs.filter(etat=d['etat'])
        if d.get('devise'):qs=qs.filter(devise=d['devise'].upper())
        for c,lookup in [('montant_min','montant__gte'),('montant_max','montant__lte')]:
            if d.get(c) is not None:qs=qs.filter(**{lookup:d[c]})
        if d.get('echeance_avant'):qs=qs.filter(**{('echeance_sejour' if admin else 'echeance_prevue')+'__lte':d['echeance_avant']})
        for c in ('organisme','periodicite','nature','domaine'):
            if d.get(c):qs=qs.filter(**{c:d[c]})
        if d.get('representant'):qs=qs.filter(representant_personne=d['representant'])
        if d.get('representant_professionnel'):qs=qs.filter(representant_intervenant=d['representant_professionnel'])
        if d['texte']:
            filtre=Q()
            for c in champs:
                if model._meta.get_field(c).get_internal_type() in ('CharField','TextField'):filtre|=Q(**{c+'__icontains':d['texte']})
            qs=qs.filter(filtre)
        objets=list(qs.order_by('personne__designation','personne_id','-debut','pk'))
        if not admin and code in ('ressources','dettes'):totaux=service.totaux(code,objets)
        if request.GET.get('format')=='csv':
            response=HttpResponse(content_type='text/csv; charset=utf-8');response['Content-Disposition']='attachment; filename="dossier-complet.csv"'
            w=csv.writer(response,delimiter=';');w.writerow(['date_reference','rubrique','personne_id','personne','declaration_id','debut','fin',*champs,'source'])
            for x in objets:
                vals=[service.series_personnelles.valeur_journal(getattr(x,c)) for c in champs]
                w.writerow([jour.isoformat(),code,x.personne_id,cellule_csv(x.personne),x.pk,x.debut.isoformat(),x.fin.isoformat() if x.fin else '',*[cellule_csv(json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v) for v in vals],cellule_csv(x.source)])
            return response
        lignes=[{'fait':x,'lignes':presentation.lignes(model,x,champs)} for x in objets]
    selection.pop('format',None);selection.pop('page',None)
    return render(request,'dossiers/rapport_dossier_complet.html',{'form':f,'code':code,'nombre':len(objets),'personnes_distinctes':len({x.personne_id for x in objets}),
        'page_obj':Paginator(lignes,50).get_page(request.GET.get('page')),'totaux':totaux,'query_rapport':selection.urlencode()})
