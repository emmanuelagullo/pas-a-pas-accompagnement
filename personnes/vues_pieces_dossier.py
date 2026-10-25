from urllib.parse import urlencode
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.http import Http404,HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods,require_safe
from . import models as m,pieces_dossier as s,bd6,dossier
from .champs_saisie import FormulaireMetier
from .forms_hebergement import date_champ


class PieceForm(FormulaireMetier):
    attendu=forms.CharField(widget=forms.HiddenInput)
    titre=forms.CharField(label='Titre du document',max_length=160)
    date_document=date_champ('Date portée sur le document (si connue)',required=False)
    source=forms.CharField(label='Provenance du fichier',max_length=160)
    fichier=forms.FileField(label='Fichier à conserver',help_text='Données fictives uniquement. 5 Mio maximum. Le fichier est conservé sans exécution ni aperçu ; les anciennes versions restent accessibles.')
    motif=forms.CharField(label='Motif du remplacement ou de la correction',max_length=240,required=False)


class AnnulationForm(FormulaireMetier):
    attendu=forms.CharField(widget=forms.HiddenInput)
    motif=forms.CharField(label='Motif d’annulation',max_length=240,help_text='Le document et toutes ses versions seront conservés et marqués annulés.')


def contexte(request,cible):
    nature=s.nature(cible)
    nav=dossier.lire(request,cible) if nature=='accompagnement' else dossier.lire_personne(request,cible.pk) if nature=='personne' else {}
    token=request.GET.get('contexte_dossier','')[:6000]
    query=urlencode({'contexte_dossier':token}) if token else ''
    if nature=='accompagnement':retour=reverse('dossiers:prise',args=['menage',cible.menage_id,cible.pk])
    else:
        params=dossier.valeurs_vue(request,nature,cible.pk)
        retour=reverse('dossiers:detail',args=[nature,cible.pk])+('?' + urlencode(params) if params else '')
    return nav.get('retour_dossier') or retour,query


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def pieces(request,nature,pk):
    if nature not in s.CIBLES:raise Http404
    cible=get_object_or_404(s.CIBLES[nature],pk=pk);s.droit(request.user,cible)
    retour,query=contexte(request,cible)
    selection=request.GET.get('piece')
    try:piece=get_object_or_404(m.PieceDossier,pk=selection,**{nature:cible}) if selection else None
    except (ValueError,ValidationError):raise Http404
    action=request.POST.get('action') or request.GET.get('action') or 'ajouter'
    annuler=action=='annuler'
    if action not in ('ajouter','annuler'):raise Http404
    if annuler and not piece:raise Http404
    derniere=piece.versions.defer('contenu').first() if piece else None
    form=(AnnulationForm if annuler else PieceForm)(request.POST or None,request.FILES or None,initial={'attendu':bd6.jeton(cible),**({'titre':derniere.titre,'date_document':derniere.date_document} if derniere and not annuler else {})})
    if piece and not annuler:
        form.fields['fichier'].required=False
        form.fields['fichier'].help_text+=' Sans nouveau fichier, les octets de la version précédente sont conservés.'
    statut=200
    if request.method=='POST' and form.is_valid():
        try:
            if annuler:s.annuler(request.user,piece,**form.cleaned_data)
            else:piece=s.ajouter(request.user,cible,piece=piece,**form.cleaned_data)
        except (ValidationError,OperationalError) as erreur:
            statut=409
            if isinstance(erreur,ValidationError) and hasattr(erreur,'message_dict'):
                for champ,messages in erreur.message_dict.items():form.add_error(champ if champ in form.fields else None,messages)
            else:form.add_error(None,' '.join(erreur.messages) if isinstance(erreur,ValidationError) else 'Écriture non confirmée. Rechargez avant de réessayer.')
        else:
            return redirect(reverse('dossiers:pieces',args=[nature,cible.pk])+'?'+urlencode({'piece':piece.pk})+('&'+query if query else ''))
    racines=m.PieceDossier.objects.filter(**{nature:cible}).order_by('-enregistre_le')
    lignes=[]
    for x in racines:
        v=x.versions.defer('contenu').first()
        if v:lignes.append((x,v))
    return render(request,'pieces_dossier/liste.html',{'cible':cible,'titre_cible':('Prise en charge du '+cible.debut.strftime('%d/%m/%Y')+' — '+str(cible.menage) if nature=='accompagnement' else str(cible)),'nature':nature,'piece':piece,'lignes':lignes,'form':form,'annuler':annuler,'retour':retour,'query':query,'versions':piece.versions.defer('contenu').select_related('auteur') if piece else []},status=statut)


@never_cache
@login_required
@require_safe
def telecharger(request,pk):
    v=get_object_or_404(m.VersionPieceDossier.objects.defer('contenu').select_related('piece__personne','piece__menage','piece__accompagnement'),pk=pk)
    try:contenu=s.octets(request.user,v)
    except ValidationError as erreur:return HttpResponse(' '.join(erreur.messages),status=422,content_type='text/plain; charset=utf-8')
    r=HttpResponse(contenu,content_type='application/octet-stream')
    from django.utils.http import content_disposition_header
    r['Content-Disposition']=content_disposition_header(True,v.nom_fichier)
    r['X-Content-Type-Options']='nosniff';r['Content-Security-Policy']="default-src 'none'; sandbox"
    return r
