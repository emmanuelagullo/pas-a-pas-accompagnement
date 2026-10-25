from datetime import timedelta
from urllib.parse import urlencode
from django import forms
from django.core.exceptions import PermissionDenied,ValidationError
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render,get_object_or_404
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe,require_http_methods
from django.http import HttpResponse
from django.utils import timezone
from . import models as m,appels115 as s,textes_riches as tr,dossier
from .forms_appels115 import AppelForm,LienForm
from .champs_saisie import FormulaireMetier
from .vues_bd6 import traiter


def date_proposee(request):
    try:date=forms.DateField().clean(request.GET.get('date_service'))
    except forms.ValidationError:date=timezone.localdate()
    return min(date,timezone.localdate())


def reference(modele,valeur):
    from django.http import Http404
    try:pk=forms.UUIDField().clean(valeur)
    except forms.ValidationError:raise Http404
    return get_object_or_404(modele,pk=pk)


def navigation(request):
    return {k:request.GET[k][:6000] for k in ('contexte_dossier','date_service','retour','personne','menage','debut','fin','q','motif_principal','type_appelant','lieu_appel','secondaire','reponse','etat_reponse','heure_min','heure_max','annules','page','retour_exploration') if k in request.GET}


def url(appel,query=''):return reverse('dossiers:appel115',args=[appel.pk])+('?' + query if query else '')


def contexte(request,v=None):
    q=urlencode(navigation(request));retour=reverse('dossiers:appels115')+('?' + q if q else '')
    ctx={}
    if request.GET.get('contexte_dossier'):
        from django.core import signing
        try:valeurs=signing.loads(request.GET['contexte_dossier'],salt=dossier.SEL,max_age=86400)
        except (signing.BadSignature,TypeError,ValueError):valeurs={}
        if isinstance(valeurs,dict):
            if valeurs.get('accompagnement') and request.user.has_perms(dossier.DROITS):
                try:a=m.Accompagnement.objects.filter(pk=valeurs['accompagnement']).first()
                except (ValueError,ValidationError):a=None
                if a:ctx=dossier.lire(request,a)
            if not ctx:
                vue=valeurs.get('vue',{})
                if isinstance(vue,dict) and vue.get('nature')=='personne':ctx=dossier.lire_personne(request,vue.get('pk'))
    if request.GET.get('retour')=='jour':
        from .retour_service import url_jour
        retour=url_jour(request.GET.get('date_service'))
    from .exploration_releve import retour_verifie
    retour_rapport=retour_verifie(request.user,request.GET.get('retour_exploration'))
    return ctx,q,retour_rapport or ctx.get('retour_dossier') or retour


def visibles(acteur):
    s.droit(acteur)
    qs=m.Appel115.objects.select_related('auteur').prefetch_related('versions__beneficiaires','versions__auteur','versions__menage','versions__appelant_personne','versions__appelant_intervenant','versions__appelant_organisme','versions__orientation')
    for a in qs:
        v=a.versions.first()
        if not v:continue
        try:s.cibles(acteur,v)
        except PermissionDenied:continue
        yield a,v


@never_cache
@require_safe
@login_required
def journal(request):
    s.droit(request.user)
    from .exploration import selection_appels
    donnees=request.GET.copy();jour=date_proposee(request)
    donnees.setdefault('debut',(jour-timedelta(days=30)).isoformat());donnees.setdefault('fin',(jour+timedelta(days=1)).isoformat())
    from .forms_exploration import AppelsRechercheForm
    f=AppelsRechercheForm(donnees);lignes=[]
    if f.is_valid():lignes=selection_appels(request.user,f.cleaned_data,personne=request.GET.get('personne'),menage=request.GET.get('menage'))
    page=Paginator(lignes,25).get_page(request.GET.get('page'));p=navigation(request);ctx,q,retour=contexte(request)
    return render(request,'appels115/journal.html',{'form':f,'page_obj':page,'query':q,'query_rapport':request.GET.urlencode(),'retour':retour,'nav_params':{k:v for k,v in p.items() if k not in f.fields and k!='page'},**ctx})


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def saisir(request,pk=None):
    s.droit(request.user,'add_versionappel115')
    a=get_object_or_404(m.Appel115,pk=pk) if pk else None
    if not a:s.droit(request.user,'add_appel115')
    v=s.lire(request.user,a) if a else None
    initial={c:getattr(v,c) for c in s.CHAMPS} if v else {'date':date_proposee(request),'type_appelant':'inconnu','etat_reponse':'inconnue'}
    if v:initial.update(details=tr.lire_objet(v,'details'),beneficiaires=list(v.beneficiaires.values_list('pk',flat=True)))
    elif request.GET.get('personne'):
        from .suivi import exiger
        exiger(request.user,'view_personne');p=reference(m.Personne,request.GET['personne']);initial['beneficiaires']=[p.pk]
    elif request.GET.get('menage'):
        from .suivi import exiger
        exiger(request.user,'view_personne','view_menage');initial['menage']=reference(m.Menage,request.GET['menage'])
    initial.update(attendu=s.jeton(a) if a else s.creation(),action='suite' if a else 'saisie')
    form=AppelForm(request.POST if request.method=='POST' else None,acteur=request.user,initial=initial)
    form.fields['action'].choices=[x for x in form.fields['action'].choices if (x[0]!='saisie')==bool(a)]
    ctx,q,retour=contexte(request,v)
    principaux=('date','heure','motif_principal','details','demandes_secondaires','secondaires_proposes','etat_reponse','reponses','reponses_proposees','source','action','motif','attendu')
    secondaires=[form[nom] for nom in form.fields if nom not in principaux]
    selection=list(form.fields['beneficiaires'].queryset.filter(pk__in=initial.get('beneficiaires',[])))
    return traiter(request,form,'Appel 115 — '+('suite ou correction' if a else 'nouvel appel'),lambda **d:s.ecrire(request.user,appel=a,**d),lambda x:url(x,q),a or 'Appel sans dossier obligatoire',annuler=url(a,q) if a else retour,gabarit='appels115/form.html',principaux=[form[nom] for nom in principaux if nom in form.fields],secondaires=secondaires,personnes_initiales=selection,
        explication='Un appel n’ouvre ni ménage, ni demande d’accueil, ni prise en charge, ni hébergement. Plusieurs appels restent des événements distincts.',**ctx)


@never_cache
@require_safe
@login_required
def fiche(request,pk):
    a=get_object_or_404(m.Appel115,pk=pk);v=s.lire(request.user,a)
    if request.GET.get('version'):
        try:n=forms.IntegerField(min_value=1).clean(request.GET['version'])
        except forms.ValidationError:from django.http import Http404;raise Http404
        v=get_object_or_404(a.versions,version=n);s.cibles(request.user,v)
    ctx,q,retour=contexte(request,v)
    versions=[]
    for ancienne in a.versions.all():
        try:s.cibles(request.user,ancienne)
        except PermissionDenied:continue
        versions.append(ancienne)
    from .parcours import droits
    liens=[l for l in a.liens.select_related('demande','accompagnement','auteur') if request.user.has_perms(droits('demandes') if l.demande_id else dossier.DROITS)]
    return render(request,'appels115/fiche.html',{'appel':a,'version':v,'est_courante':v.version==a.versions.first().version,'versions':versions,'query':q,'retour':retour,'liens':liens,**ctx})


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def action(request,pk,action,lien_pk=None):
    a=get_object_or_404(m.Appel115,pk=pk);v=s.lire(request.user,a);ctx,q,retour=contexte(request,v)
    if action=='lier':
        s.droit(request.user,'add_lienappelparcours');f=LienForm(request.POST if request.method=='POST' else None,acteur=request.user,version=v,initial={'attendu':s.jeton(a)})
        fn=lambda **d:s.lier(request.user,a,**d)
    else:
        s.droit(request.user,'annuler_appel115' if action=='annuler' else 'annuler_lienappelparcours')
        f=FormulaireMetier(request.POST if request.method=='POST' else None)
        f.fields['motif']=forms.CharField(max_length=240,label='Motif de l’annulation')
        f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=s.jeton(a))
        if action=='annuler':fn=lambda **d:s.annuler(request.user,a,**d)
        else:
            lien=get_object_or_404(a.liens,pk=lien_pk);fn=lambda **d:s.delier(request.user,a,lien,**d)
    return traiter(request,f,'Lier au parcours' if action=='lier' else 'Annuler une saisie erronée',fn,url(a,q),a.pk,**ctx)


@never_cache
@require_safe
@login_required
def pdf(request,pk):
    a=get_object_or_404(m.Appel115,pk=pk);v=s.lire(request.user,a)
    if request.GET.get('version'):
        from django.http import Http404
        try:n=forms.IntegerField(min_value=1).clean(request.GET['version'])
        except forms.ValidationError:raise Http404
        v=get_object_or_404(a.versions,version=n);s.cibles(request.user,v)

    lignes=['Données fictives uniquement','Appel : '+str(a.pk)+' · version '+str(v.version),
        'Date : '+str(v.date)+' · heure : '+(str(v.heure) if v.heure else 'inconnue'),
        'Appelant : '+v.get_type_appelant_display()+' · '+str(v.appelant_personne or v.appelant_intervenant or v.appelant_organisme or v.appelant_libre),
        'Lieu : '+v.lieu_appel,'Téléphone déclaré : '+v.telephone,'Personnes concernées : '+' ; '.join(str(p) for p in v.beneficiaires.all()),
        'Demande principale : '+v.motif_principal,v.details,'Autres demandes : '+' ; '.join(v.demandes_secondaires),
        'État de réponse : '+v.get_etat_reponse_display(),'Réponses : '+' ; '.join(v.reponses),
        'Orientation : '+str(v.orientation or v.orientation_declaree),'Complément : '+v.information_complementaire,'Effectifs déclarés par appel : adultes '+str(v.adultes_declares)+' ; enfants '+str(v.enfants_declares)+' ; grossesses '+str(v.grossesses_declarees),'Source : '+v.source,
        'Auteur initial de saisie : '+str(a.auteur),'Version saisie par : '+str(v.auteur)+' · '+str(v.enregistre_le),'Une orientation déclarée ne prouve ni admission ni réalisation.']
    if a.annule_le:lignes.insert(1,'APPEL ANNULÉ : '+a.motif_annulation)
    from .pdf_restitution import produire
    return produire(request,'Appel 115',lignes,'appel115-'+str(a.pk)+'.pdf')
