"""Même lecture et même saisie pour le cahier complet et son panneau intégré."""
from django.contrib.auth.decorators import login_required
from django import forms
from django.core.exceptions import ObjectDoesNotExist,ValidationError,PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction,OperationalError
from django.http import Http404
from django.shortcuts import render,redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from acteurs.contexte import perimetre
from . import liaisons as s
from .vues_transmissions import TexteForm


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def cahier(request):
    with perimetre(request.user,statistiques='accessibles',reperage=False):
        try:point=s.Point(request.user,request.GET.get('lia_cible','service'),request.GET.get('lia_id'))
        except (ObjectDoesNotExist,ValidationError,ValueError,TypeError):raise Http404
        with perimetre(request.user,service=point.service_id):
            f=s.filtres(request.GET,point);params=s.parametres(request.GET)
            from .retour_service import contexte_jour
            form=TexteForm(request.POST if request.method=='POST' else None,initial={'date_fait':contexte_jour(request)['date_service']})
            envoi_requis='lia_cible' in request.GET
            form.fields['lia_envoi']=forms.CharField(required=envoi_requis,widget=forms.HiddenInput,initial=s.jeton_envoi(point))
            statut=200
            if request.method=='POST':
                if not point.ecriture():raise PermissionDenied
                if form.is_valid():
                    try:
                        with transaction.atomic():
                            cle=s.verifier_envoi(point,form.cleaned_data['lia_envoi']) if form.cleaned_data.get('lia_envoi') else None
                            message=point.publier(form.cleaned_data['contenu'],form.cleaned_data['date_fait'],cle_envoi=cle)
                    except (ValidationError,OperationalError) as e:
                        form.add_error(None,e if isinstance(e,ValidationError) else 'Écriture non confirmée ; votre message est conservé.');statut=409
                    else:
                        if request.POST.get('retour')=='jour':
                            from .retour_service import url_jour
                            return redirect(url_jour(request.POST.get('date_service')))
                        if not request.GET:return redirect('suivi:cahier')
                        jour=message.date_fait or s.timezone.localdate(message.cree_le)
                        voir=point.page({'lia_debut':jour.isoformat(),'lia_fin':(jour+s.timedelta(days=1)).isoformat(),'lia_types':['messages'],'lia_focus':'message-'+message._meta.model_name+'-'+str(message.pk)})
                        params['lia_voir']=s.retour_signe(request.user,voir)
                        params['lia_publie']='1'
                        if request.GET.get('lia_fragment')=='1':params['lia_fragment']='1'
                        return redirect(point.url(params)+'#liaisons')
                else:statut=400
            lignes=s.selection(point,f.cleaned_data) if f.is_valid() else []
            paginator=Paginator(lignes,25);page=request.GET.get('lia_page')
            focus=request.GET.get('lia_focus','')[:100]
            if focus:
                place=next((i for i,x in enumerate(lignes) if x['cle']==focus),None)
                if place is not None:page=place//25+1
            page=paginator.get_page(page)
            # Corrections réutilisées ; aucun message ni événement n'est effacé par un filtre.
            token=s.retour_signe(request.user,point.page(params) if params.get('lia_enplace')=='1' else point.url(params))
            for x in page:
                c=x['contribution']
                if c:
                    from acteurs import politique as politique
                    try:politique.exiger_objet(request.user,c,True);modifiable=True
                    except PermissionDenied:modifiable=False
                    nature='note' if c._meta.model_name=='notepartagee' else 'transmission'
                    x['corriger_url']=s.reverse('suivi:corriger_contribution',args=[nature,c.pk])+'?'+s.urlencode({'lia_retour':token}) if modifiable and request.user.has_perm('personnes.change_'+c._meta.model_name) else ''
                    x['annuler_url']=s.reverse('dossiers:contribution_annuler',args=[nature,c.pk])+'?'+s.urlencode({'lia_retour':token}) if modifiable and request.user.has_perm('personnes.add_annulationcontribution') else ''
            services=[]
            if point.nature in ('service','ensemble'):
                from acteurs.models import Service
                services=[{'label':str(x),'url':s.Point(request.user,'service',x.pk).url(params)} for x in Service.objects.filter(pk__in=s.services(request.user))]
                if len(services)>1:services.append({'label':'Tous mes services accessibles','url':s.Point(request.user,'ensemble').url(params)})
            query={**point.params(),**params,'lia_filtres':'1'}
            donnees={**contexte_jour(request),'point':point,'filtres':f,'form':form if point.ecriture() else None,'page_obj':page,
                'services_cahier':services,'parents':point.parents(params),'retour_origine':s.lire_retour(request.user,params.get('lia_origine','')),
                'url_cahier':point.url({k:v for k,v in params.items() if k!='lia_enplace'}),'url_formulaire':point.url({**params,**({'lia_fragment':'1'} if request.GET.get('lia_fragment')=='1' else {})}),
                'url_precedente':point.url({**query,'lia_page':page.previous_page_number()}) if page.has_previous() else '',
                'url_suivante':point.url({**query,'lia_page':page.next_page_number()}) if page.has_next() else '',
                'voir_message':s.lire_retour(request.user,request.GET.get('lia_voir','')),'focus':focus,'publie':request.GET.get('lia_publie')=='1'}
            return render(request,'liaisons/panneau.html' if request.GET.get('lia_fragment')=='1' else 'liaisons/page.html',donnees,status=statut)
