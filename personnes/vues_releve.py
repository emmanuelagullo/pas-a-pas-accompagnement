from datetime import timedelta
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render,get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe,require_http_methods
from . import models as m,releve as s,transmissions,bd6
from .champs_saisie import FormulaireMetier
from .forms_hebergement import date_champ
from .vues_bd6 import traiter


class RechercheForm(FormulaireMetier):
    debut=date_champ('Du (inclus)');fin=date_champ('Au (exclu)')
    q=forms.CharField(label='Chercher dans le texte',max_length=160,required=False)
    auteur=forms.ModelChoiceField(get_user_model().objects.all(),required=False,label='Auteur de saisie')
    notes=forms.BooleanField(label='Chercher les notes de dossiers plutôt que les transmissions',required=False)
    annules=forms.BooleanField(label='Inclure les contributions annulées',required=False)
    def clean(self):
        d=super().clean()
        if d.get('debut') and d.get('fin') and d['fin']<=d['debut']:self.add_error('fin','La fin exclue doit suivre le début.')
        return d


@never_cache
@require_safe
@login_required
def recherche(request):
    from .suivi import exiger
    exiger(request.user,'view_notepartagee' if request.GET.get('notes') in ('1','true','True','on') else 'view_transmission')
    data=request.GET.copy();jour=timezone.localdate();data.setdefault('debut',(jour-timedelta(days=30)).isoformat());data.setdefault('fin',(jour+timedelta(days=1)).isoformat())
    f=RechercheForm(data);xs=[]
    if f.is_valid():xs=s.contributions(request.user,**f.cleaned_data)
    if f.is_valid() and request.GET.get('format')=='pdf':
        from .pdf_restitution import produire
        lignes=['Données fictives uniquement','Dates déclarées, ou date de saisie explicitement utilisée quand inconnues.',str(f.cleaned_data['debut'])+' → '+str(f.cleaned_data['fin'])+' (fin exclue)']
        for x in xs:
            lignes.extend([str(s.date_de(x))+(' (date déclarée)' if x.date_fait else ' (date de saisie, date du fait inconnue)')+' · auteur initial : '+str(x.auteur),x.contenu])
            correction=x.revisions.last()
            if correction:lignes.append('Dernière correction : '+str(correction.auteur)+' · '+str(correction.date)+' · '+correction.motif)
            if hasattr(x,'annulation'):lignes.append('ANNULÉ : '+x.annulation.motif+' · '+str(x.annulation.auteur)+' · '+str(x.annulation.enregistre_le))
        return produire(request,'Relève — sélection de contributions',lignes,'releve-fictive.pdf')
    data.pop('page',None);data.pop('format',None)
    return render(request,'releve/recherche.html',{'form':f,'page_obj':Paginator(xs,25).get_page(request.GET.get('page')),'query_rapport':data.urlencode()})


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def annuler(request,nature,pk):
    from .suivi import exiger
    exiger(request.user,'add_annulationcontribution','view_annulationcontribution')
    if nature not in ('transmission','note'):
        from django.http import Http404
        raise Http404
    x=get_object_or_404(m.Transmission if nature=='transmission' else m.NotePartagee,pk=pk);s.lecture(request.user,x)
    f=FormulaireMetier(request.POST if request.method=='POST' else None)
    f.fields['motif']=forms.CharField(max_length=240,label='Motif de l’annulation')
    f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=transmissions.jeton(x))
    from .liaisons import lire_retour
    retour=lire_retour(request.user,request.GET.get('lia_retour','')) or reverse('dossiers:releve_recherche')
    return traiter(request,f,'Annuler une contribution erronée',lambda **d:transmissions.annuler(request.user,x,**d),retour,str(x.pk),explication='Le contenu et ses corrections restent conservés ; l’annulation est un statut séparé.')


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def action(request,pk):
    from .suivi import exiger
    exiger(request.user,'view_actionrelais','change_actionrelais','view_revisionactionrelais')
    x=get_object_or_404(m.ActionRelais,pk=pk)
    f=FormulaireMetier(request.POST if request.method=='POST' else None)
    f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=bd6.jeton(x))
    f.fields['operation']=forms.ChoiceField(choices=[('correction','Corriger libellé ou échéance'),('reouvrir','Rouvrir une action clôturée ou annulée par erreur'),('annuler','Annuler une action erronée sans la déclarer réalisée')])
    if not request.user.has_perm('personnes.annuler_actionrelais'):f.fields['operation'].choices=[c for c in f.fields['operation'].choices if c[0]!='annuler']
    f.fields['libelle']=forms.CharField(max_length=240,label='Action',initial=x.libelle)
    f.fields['echeance']=date_champ('Échéance prévue',False);f.initial['echeance']=x.echeance
    f.fields['motif']=forms.CharField(max_length=240,label='Motif')
    def faire(operation,**d):return s.changer_action(request.user,x,reouvrir=operation=='reouvrir',annuler=operation=='annuler',**d)
    return traiter(request,f,'Corriger ou rouvrir l’action',faire,reverse('suivi:actions_relais'),x.pk)
