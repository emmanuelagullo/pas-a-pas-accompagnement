from datetime import datetime
from django import forms
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, OperationalError
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST
from personnes.champs_saisie import FormulaireMetier
from personnes import models as m
from .models import *
from . import politique as p, services as s
from .forms import *


def formulaire(request,form,titre,faire,retour,**contexte):
    statut=200
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():faire(**form.cleaned_data)
        except (ValidationError,OperationalError) as e:
            form.add_error(None,' '.join(e.messages) if isinstance(e,ValidationError) else 'Écriture non confirmée ; rechargez avant de réessayer.');statut=409
        else:return redirect(retour() if callable(retour) else retour)
    return render(request,'acteurs/form.html',{'form':form,'titre':titre,'retour':retour,**contexte},status=statut)


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def organisation(request,service_pk=None,action=None):
    s.exiger_gestion(request.user)
    service=get_object_or_404(Service,pk=service_pk) if service_pk else None
    retour=reverse('acteurs:organisation')
    if service:retour=reverse('acteurs:service',args=[service.pk])
    if action=='creer_service':
        f=ServiceForm(request.POST if request.method=='POST' else None)
        def creer(**d):
            x=Service(**d);x.full_clean();x.save();s.journal(request.user,x,'service',{}, {'libelle':x.libelle,'politique':x.politique})
        return formulaire(request,f,'Créer un service',creer,reverse('acteurs:organisation'))
    if action=='membre':
        f=AppartenanceForm(request.POST if request.method=='POST' else None,initial={'debut':timezone.localdate()})
        # Répertoire explicite, uniquement après le contrôle gerer_organisation.
        # Configurer les membres ne nécessite aucune habilitation aux dossiers.
        f.fields['professionnel'].queryset=m.Intervenant._base_manager.all()
        return formulaire(request,f,'Inscrire un professionnel dans ce service',lambda compte=None,**d:s.inscrire(request.user,service,cible_compte=compte,**d),retour)
    if action=='habilitation':
        f=HabilitationForm(request.POST if request.method=='POST' else None,initial={'debut':timezone.localdate()})
        return formulaire(request,f,'Accorder des tâches dans ce service',lambda compte,**d:s.habiliter(request.user,compte,service,**d),retour)
    if action=='politique':
        f=FormulaireMetier(request.POST if request.method=='POST' else None)
        f.fields['politique']=forms.ChoiceField(choices=Service.POLITIQUES,initial=service.politique)
        f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=s.jeton(service))
        return formulaire(request,f,'Changer la politique du service',lambda **d:s.changer_politique(request.user,service,**d),retour)
    if request.method=='POST':return HttpResponseNotAllowed(['GET'])
    return render(request,'acteurs/organisation.html',{'services':Service.objects.select_related('etablissement__organisme'),
        'service':service,'membres':AppartenanceProfessionnelle.objects.filter(service=service).select_related('professionnel'),
        'habilitations':Habilitation.objects.filter(service=service).select_related('compte'),
        'journaux':JournalAcces.objects.filter(service=service).select_related('auteur').order_by('-pk')[:50] if service else [],
        'controle_actif':p.active()})


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def revocation(request,pk):
    s.exiger_gestion(request.user);h=get_object_or_404(Habilitation,pk=pk)
    f=FormulaireMetier(request.POST if request.method=='POST' else None)
    f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=s.jeton(h))
    return formulaire(request,f,'Révoquer cet accès maintenant',lambda **d:s.revoquer(request.user,h,**d),reverse('acteurs:service',args=[h.service_id]))


@login_required
@require_POST
def choisir_service(request):
    x=get_object_or_404(Service,pk=request.POST.get('service'),pk__in=p.habilitations(request.user).values('service_id'))
    request.session['service_acteurs']=x.pk
    return redirect('accueil')


def dossier_autorise(request,pk):
    ds=get_object_or_404(DossierService.objects.select_related('service','personne','menage'),pk=pk,
        service_id__in=p.habilitations(request.user).values('service_id'))
    cible=ds.personne or ds.menage
    p.exiger_objet(request.user,cible)
    return ds


def retour_dossier(ds,request=None):
    if request:
        try:
            p.exiger_objet(request.user,ds.personne or ds.menage)
        except PermissionDenied:return reverse('accueil')
        token=request.GET.get('retour_acteurs','')
        if token and len(token)<=35000:
            try:
                v=signing.loads(token,salt='retour-acteurs-v1',max_age=86400)
                from django.utils.http import url_has_allowed_host_and_scheme
                url=v.get('url','')
                if v.get('compte')==str(request.user.pk) and v.get('dossier')==str(ds.pk) and url.startswith('/') and not url.startswith('//') and url_has_allowed_host_and_scheme(url,allowed_hosts=set()):return url
            except (signing.BadSignature,TypeError,AttributeError):pass
    return reverse('dossiers:detail',args=['personne' if ds.personne_id else 'menage',ds.personne_id or ds.menage_id])


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def reprendre(request,pk):
    ds=dossier_autorise(request,pk)
    f=FormulaireMetier(request.POST if request.method=='POST' else None)
    f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=s.jeton(ds))
    return formulaire(request,f,'Commencer le suivi de '+str(ds),lambda **d:s.commencer(request.user,ds,**d),retour_dossier(ds,request))


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def relais(request,pk,niveau='dossier',objet_pk=None):
    ds=dossier_autorise(request,pk)
    model={'prise':m.Accompagnement,'hebergement':m.AccordHebergement,'repas':m.AccordRepas,'aide':m.AccordAide}.get(niveau)
    objet=get_object_or_404(model,pk=objet_pk) if model else ds
    if model is None and niveau!='dossier':raise Http404
    s.selection_cible(ds,objet)
    qs=m.Intervenant.objects.filter(pk__in=AppartenanceProfessionnelle.objects.filter(p.periode(),service=ds.service).values('professionnel_id'))
    prof=p.professionnel(request.user)
    init={'entrant':prof if request.GET.get('prendre') else None,'sortant':prof,'date':timezone.localdate(),'descendants':True,'attendu':s.jeton(ds)}
    f=RelaisForm(request.POST if request.method=='POST' else None,initial=init)
    f.fields['entrant'].queryset=qs
    f.fields['sortant'].queryset=qs if p.habilitations(request.user).filter(service=ds.service,corriger_autrui=True).exists() else qs.filter(pk=prof)
    lignes,prop=s.proposition_relais(request.user,ds,objet)
    if request.method=='POST' and f.is_valid():
        d=f.cleaned_data
        lignes,proposition_attendue=s.proposition_relais(request.user,ds,objet,d['descendants'],d['sortant'].pk,d['date'])
        try:ancienne=signing.loads(d['proposition'],salt='acteurs-relais-v1',max_age=3600)
        except (signing.BadSignature,TypeError):ancienne={}
        nouvelle=signing.loads(proposition_attendue,salt='acteurs-relais-v1')
        # L'heure du clic reste celle photographiée à la proposition pour aujourd'hui.
        try:
            instant=datetime.fromisoformat(ancienne.get('date',''))
            jour=timezone.localtime(instant).date() if timezone.is_aware(instant) else None
        except (ValueError,TypeError):jour=None
        concorde=all(ancienne.get(k)==nouvelle.get(k) for k in ('dossier','revision','ids','sortant')) and jour==d['date']
        prop=proposition_attendue
        if concorde:
            try:s.relayer(request.user,ds,d['entrant'],d['attendu'],d['proposition'])
            except (ValidationError,OperationalError) as e:f.add_error(None,' '.join(e.messages) if isinstance(e,ValidationError) else 'Relais non confirmé ; rechargez avant de réessayer.')
            else:return redirect(retour_dossier(ds,request))
        else:f.add_error(None,'Vérifiez la portée actualisée puis confirmez le relais.')
    f.initial['proposition']=prop
    if f.is_bound:
        data=f.data.copy();data['proposition']=prop;f.data=data
    return render(request,'acteurs/form.html',{'form':f,'titre':'Passer ou prendre le relais','retour':retour_dossier(ds,request),'lignes_relais':lignes,'niveau':niveau,'proposition_relais':True})


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def attribuer(request,pk,niveau='dossier',objet_pk=None):
    ds=dossier_autorise(request,pk)
    model={'prise':m.Accompagnement,'hebergement':m.AccordHebergement,'repas':m.AccordRepas,'aide':m.AccordAide}.get(niveau)
    objet=get_object_or_404(model,pk=objet_pk) if model else ds
    if model is None and niveau!='dossier':raise Http404
    if not s.peut_attribuer(request.user,ds,objet):raise PermissionDenied
    f=FormulaireMetier(request.POST if request.method=='POST' else None)
    qs=m.Intervenant.objects.filter(pk__in=AppartenanceProfessionnelle.objects.filter(p.periode(),service=ds.service).values('professionnel_id'))
    f.fields['professionnel']=forms.ModelChoiceField(qs,label='Professionnel du service')
    f.fields['role']=forms.ChoiceField(choices=Responsabilite._meta.get_field('role').choices,label='Participation')
    f.fields['debut']=forms.DateField(label='Début de l’intervention',initial=timezone.localdate(),widget=forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'}))
    f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=s.jeton(ds))
    return formulaire(request,f,'Ajouter un intervenant à ce suivi',lambda **d:s.ajouter_responsabilite(request.user,ds,objet,**d),retour_dossier(ds,request))


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def exploitation(request,service_pk):
    s.exiger_gestion(request.user)
    service=get_object_or_404(Service,pk=service_pk)
    f=FormulaireMetier(request.POST if request.method=='POST' else None)
    f.fields['lieu']=forms.ModelChoiceField(m.LieuHebergement._base_manager.all(),label='Lieu physique')
    f.fields['etablissement']=forms.ModelChoiceField(Etablissement.objects.all(),required=False,label='Établissement exploitant')
    f.fields['organisme_exterieur']=forms.ModelChoiceField(m.Partenaire._base_manager.all(),required=False,label='Ou organisme exploitant, si l’établissement n’est pas identifié')
    f.fields['interlocuteur']=forms.ModelChoiceField(m.Intervenant._base_manager.all(),required=False,label='Interlocuteur (facultatif)')
    f.fields['debut']=forms.DateField(label='Depuis le',initial=timezone.localdate(),widget=forms.DateInput(attrs={'type':'date'}))
    f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=s.jeton(service))
    return formulaire(request,f,'Déclarer un changement d’exploitant',lambda **d:s.changer_exploitation(request.user,service,**d),reverse('acteurs:service',args=[service.pk]))


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def terminer(request,pk):
    x=get_object_or_404(Responsabilite.objects.select_related('dossier'),pk=pk)
    ds=dossier_autorise(request,x.dossier_id)
    if x.professionnel_id!=p.professionnel(request.user) and not p.habilitations(request.user).filter(service=ds.service,corriger_autrui=True).exists():raise PermissionDenied
    f=FormulaireMetier(request.POST if request.method=='POST' else None)
    f.fields['date']=forms.DateField(label='Fin de l’intervention',initial=timezone.localdate(),widget=forms.DateInput(attrs={'type':'date'}))
    f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=s.jeton(ds))
    return formulaire(request,f,'Terminer cette intervention',lambda **d:s.terminer_responsabilite(request.user,x,**d),lambda:retour_dossier(ds,request))


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def reperage_politique(request,service_pk):
    s.exiger_gestion(request.user)
    service=get_object_or_404(Service.objects.select_related('etablissement'),pk=service_pk)
    f=FormulaireMetier(request.POST if request.method=='POST' else None)
    f.fields['activer']=forms.BooleanField(required=False,initial=service.etablissement.reperage_identites,label='Permettre de repérer les identités dans cet établissement',help_text='Les professionnels habilités voient les noms et les équipes des dossiers de cet établissement. Le contenu social, les documents et les statistiques gardent leurs propres accès. Les prestations restent limitées aux services autorisés.')
    f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=s.jeton(service.etablissement))
    def faire(activer,attendu):
        s.exiger_gestion(request.user);e=service.etablissement;s.reserver(e,attendu)
        avant=e.reperage_identites;e.reperage_identites=activer;e.save(update_fields=['reperage_identites'])
        s.journal(request.user,service,'reperage_identites',{'actif':avant},{'etablissement':e.pk,'actif':activer})
    return formulaire(request,f,'Repérage des identités · '+str(service.etablissement),faire,reverse('acteurs:service',args=[service.pk]))


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def demander_rattachement(request,pk):
    from . import reperage
    ds=get_object_or_404(reperage.dossiers(request.user),pk=pk)
    if not reperage.disponibles(request.user,ds):raise PermissionDenied
    f=FormulaireMetier(request.POST if request.method=='POST' else None)
    return formulaire(request,f,'Demander à rejoindre le suivi de '+str(ds),lambda:reperage.demander(request.user,ds),retour_dossier(ds,request))


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def decider_rattachement(request,pk):
    from . import reperage
    demande=get_object_or_404(DemandeRattachement.objects.select_related('dossier','professionnel','demandeur'),pk=pk)
    ds=dossier_autorise(request,demande.dossier_id)
    if not s.peut_attribuer(request.user,ds,ds):raise PermissionDenied
    f=FormulaireMetier(request.POST if request.method=='POST' else None)
    f.fields['accepter']=forms.TypedChoiceField(choices=[('oui','Ajouter au suivi'),('non','Refuser la demande')],coerce=lambda x:x=='oui',label='Réponse')
    f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=s.jeton(demande))
    f.fields['attendu_dossier']=forms.CharField(widget=forms.HiddenInput,initial=s.jeton(ds))
    return formulaire(request,f,'Demande de '+str(demande.professionnel),lambda **d:reperage.decider(request.user,demande,**d),retour_dossier(ds,request))
