from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404,render,redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from . import models as m, modeles_personnels as s
from .champs_saisie import FormulaireMetier
from django.core.exceptions import ValidationError,PermissionDenied


class GestionForm(FormulaireMetier):
    nom=forms.CharField(label='Nom du rapport personnel',max_length=100)
    attendu=forms.CharField(widget=forms.HiddenInput)


def ouvrir(modele):
    from .catalogue_rapports import ouvrir
    return ouvrir(modele)

@never_cache
@require_http_methods(['GET','POST'])
@login_required
def gerer(request,pk):
    modele=get_object_or_404(m.ModeleRapport,pk=pk,auteur=request.user);s.exiger(request.user,modele)
    f=GestionForm(request.POST if request.method=='POST' else None,initial={'nom':modele.nom,'attendu':s.jeton(request.user,modele)})
    status=200
    if request.method=='POST' and f.is_valid():
        try:
            action=request.POST.get('action')
            if action=='renommer':x=s.changer(request.user,modele,f.cleaned_data['attendu'],f.cleaned_data['nom'])
            elif action=='dupliquer':x=s.dupliquer(request.user,modele,f.cleaned_data['attendu'],f.cleaned_data['nom'])
            elif action=='supprimer':
                s.supprimer(request.user,modele,f.cleaned_data['attendu'])
                return redirect('dossiers:rapports_gerer')
            elif action=='remplacer':
                params={k:v for k,v in request.POST.items() if k not in ('nom','attendu','action','csrfmiddlewaretoken')}
                x=s.changer(request.user,modele,f.cleaned_data['attendu'],f.cleaned_data['nom'],params)
            else:raise ValidationError('Choisissez Renommer, Dupliquer ou Remplacer explicitement.')
        except ValidationError as erreur:
            f.add_error(None,erreur.messages);status=409 if isinstance(erreur,s.ConflitModele) else 400
        else:return redirect(ouvrir(x))
    from urllib.parse import urlencode
    reprise=''
    if request.method=='POST' and request.POST.get('action')=='remplacer':
        params={k:v for k,v in request.POST.items() if k not in ('nom','attendu','action','csrfmiddlewaretoken')}
        params.update(modele_cible=str(modele.pk),attendu_modele=request.POST.get('attendu',''))
        source=modele.parametres.get('_rapport_source')
        route=reverse('dossiers:rapport_composer',args=[source]) if source else reverse('dossiers:explorer' if modele.parametres.get('exploration') else 'statistiques')
        reprise=route+'?'+urlencode(params)
    return render(request,'exploration/gerer_modele.html',{'form':f,'modele':modele,'ouvrir_modele':ouvrir(modele),'reprise_configuration':reprise},status=status)


@never_cache
@require_http_methods(['GET'])
@login_required
def liste(request):
    lignes=[]
    for x in m.ModeleRapport.objects.filter(auteur=request.user):
        try:s.exiger(request.user,x);autorise=True
        except PermissionDenied:autorise=False
        lignes.append(dict(modele=x,url=ouvrir(x),autorise=autorise))
    return render(request,'rapports/gestion.html',{'lignes':lignes})
