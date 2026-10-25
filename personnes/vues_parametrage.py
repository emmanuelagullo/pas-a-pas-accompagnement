"""Une page de répertoire : fichier privé, aperçu, confirmation et reçu."""
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.http import HttpResponse
from django.shortcuts import render,redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from . import parametrage as s,models as m
from .champs_saisie import FormulaireMetier


class ChoixFichier(FormulaireMetier):
    fichier=forms.FileField(label='Paramétrage JSON',help_text='1 Mo maximum ; organismes, professionnels, lieux, types d’aide et tarifs. Aucun dossier ni droit importé.')


class Confirmation(FormulaireMetier):
    attendu=forms.CharField(widget=forms.HiddenInput)
    motif=forms.CharField(max_length=240,label='Origine et raison de cet import')
    accepter_homonymes=forms.BooleanField(required=False,label='Créer aussi les homonymes signalés, sans fusionner ni remplacer les entrées existantes')
    confirmer=forms.BooleanField(label='Je confirme la création des entrées présentées ci-dessus')


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def catalogue(request):
    s.droits(request.user)
    if request.method=='GET' and request.GET.get('format')=='json':
        rep=HttpResponse(s.serialiser(s.exporter(request.user)),content_type='application/json; charset=utf-8')
        rep['Content-Disposition']='attachment; filename="pas-a-pas-parametrage.json"';return rep
    form=ChoixFichier();confirmation=None;apercu=None;conflits=[];statut=200
    if request.method=='POST':
        s.droits(request.user,ecriture=True)
        if request.POST.get('action')=='preparer':
            form=ChoixFichier(request.POST,request.FILES)
            if form.is_valid():
                try:
                    data=s.decoder(form.cleaned_data['fichier'].read(s.MAX_OCTETS+1))
                    token,conflits=s.preparer(request.user,data)
                except ValidationError as erreur:form.add_error('fichier',erreur)
                else:
                    apercu=data;confirmation=Confirmation(initial={'attendu':token})
        elif request.POST.get('action')=='confirmer':
            confirmation=Confirmation(request.POST)
            try:
                p=s.lire_apercu(request.POST.get('attendu'));apercu=p['contenu'];conflits=p['collisions']
            except ValidationError as erreur:confirmation.add_error(None,erreur)
            if confirmation.is_valid():
                try:
                    d=confirmation.cleaned_data.copy();d.pop('confirmer');j=s.confirmer(request.user,**d)
                except (ValidationError,OperationalError) as erreur:
                    confirmation.add_error(None,' '.join(erreur.messages) if isinstance(erreur,ValidationError) else 'Écriture non confirmée ; consultez les reçus avant de réessayer.');statut=409
                else:return redirect(reverse('dossiers:parametrage')+'?recu='+str(j.pk))
        else:
            form=ChoixFichier(request.POST,request.FILES)
            form.add_error(None,'Choisissez le fichier pour préparer un aperçu.')
    return render(request,'dossiers/parametrage.html',{'form':form,'confirmation':confirmation,'apercu':apercu,'conflits':conflits,
        'recus':m.ImportParametrage.objects.select_related('auteur')[:20],'recu_choisi':request.GET.get('recu','')},status=statut)
