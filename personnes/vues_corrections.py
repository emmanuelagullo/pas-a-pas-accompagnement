from . import textes_riches as tr
from . import dossier
from django import forms
from .champs_saisie import FormulaireMetier
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_safe
from . import corrections as c
from .forms_hebergement import date_champ
from .vues_hebergement import traiter_hebergement
from .models import Accompagnement, CorrectionPeriode, RevisionTexteSocial
from .suivi import exiger


class PeriodeForm(FormulaireMetier):
    debut = date_champ('Début inclus')
    fin = date_champ('Fin non comprise',False)
    source = forms.CharField(max_length=160,required=False,label='Source de l’information')
    motif = forms.CharField(max_length=240,label='Précision sur la correction (facultative)',required=False)
    attendu = forms.CharField(widget=forms.HiddenInput)


class TexteForm(FormulaireMetier):
    date_effet = date_champ('Date d’effet')
    texte = forms.CharField(max_length=2000,widget=forms.Textarea)
    source = forms.CharField(max_length=160,required=False,label='Source de l’information')
    motif = forms.CharField(max_length=240,label='Précision sur la correction (facultative)',required=False)
    attendu = forms.CharField(widget=forms.HiddenInput)


@require_http_methods(['GET','POST'])
@login_required
def corriger(request,nature,pk):
    registre={**{nom:val[0] for nom,val in c.PERIODES.items()},**c.TEXTES}
    if nature not in registre:raise Http404
    c.droits(request.user,nature)
    objet=get_object_or_404(registre[nature],pk=pk)
    if getattr(objet, 'annule_le', None) is not None:
        from django.http import HttpResponse
        return HttpResponse('Cet accord est annulé ; ses dates restent conservées dans l’historique.', status=409)
    a=c.suivi_de(objet)
    retour=reverse('suivi:accompagnement',args=[a.pk]) if a else reverse('suivi:detail',args=[objet.menage_id])
    if nature in c.TEXTES:
        initial={'date_effet':objet.date_effet,'texte':objet.texte,'source':getattr(objet,'source',''),'attendu':c.jeton(objet)}
        form=TexteForm(request.POST if request.method=='POST' else None,initial=initial)
        if nature=='evenementsocial':
            form.fields['texte'].max_length=500
            form.fields['source'].required=True
            form.fields['date_effet'].help_text='Un fait de l’histoire antérieure peut précéder le début du suivi ; sa source et le motif restent requis.'
        else:
            del form.fields['source']
            form.fields['texte'] = tr.ChampTexte(label='Bilan court', max_length=2000)
            form.initial['texte'] = tr.lire_objet(objet, 'texte')
        action=lambda **d:c.texte(request.user,objet,**d)
    else:
        initial={'debut':objet.debut,'fin':objet.fin,'source':getattr(objet,'source',''),'attendu':c.jeton(objet)}
        form=PeriodeForm(request.POST if request.method=='POST' else None,initial=initial)
        if nature=='situationsociale':
            form.fields['fin'].disabled=True;form.fields['source'].required=True
        else:
            del form.fields['source']
        action=lambda **d:c.periode(request.user,objet,**d)
    return traiter_hebergement(request,form,'Corriger une saisie — '+objet._meta.verbose_name,action,c.menage_de(objet),accompagnement=a,retour=retour)


@require_safe
@login_required
def historique(request,pk):
    exiger(request.user,'view_personne','view_menage','view_accompagnement')
    a=get_object_or_404(Accompagnement.objects.select_related('menage'),pk=pk)
    periodes=[];textes=[]
    if request.user.has_perm('personnes.view_correctionperiode'):
        natures=[nom for nom in c.PERIODES if request.user.has_perm('personnes.view_'+nom)]
        periodes=a.corrections_periodes.filter(nature__in=natures).select_related('auteur')
    if request.user.has_perm('personnes.view_revisiontextesocial'):
        q=RevisionTexteSocial.objects.none()
        if request.user.has_perm('personnes.view_evenementsocial'):q=a.revisions_textes.filter(evenement__isnull=False)
        if request.user.has_perm('personnes.view_bilansocial'):q=q|a.revisions_textes.filter(bilan__isnull=False)
        textes=q.select_related('auteur').order_by('enregistre_le','pk')
    if not (request.user.has_perm('personnes.view_correctionperiode') or request.user.has_perm('personnes.view_revisiontextesocial')):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return render(request,'suivi/corrections.html',{**dossier.lire(request, a),'accompagnement':a,'periodes':periodes,'textes':textes})
