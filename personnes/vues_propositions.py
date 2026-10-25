from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .champs_saisie import FormulaireModeleMetier
from .models import PropositionSaisie
from . import propositions
from .vues_bd6 import traiter


class PropositionForm(FormulaireModeleMetier):
    attendu=forms.CharField(widget=forms.HiddenInput, required=False)
    motif=forms.CharField(label='Pourquoi modifier les propositions ?',max_length=240,widget=forms.Textarea(attrs={'rows':2}))
    class Meta:
        model=PropositionSaisie
        fields=['champ','valeur','active']
        labels={'champ':'Champ concerné','valeur':'Valeur proposée','active':'Proposer cette valeur à la saisie'}


@never_cache
@require_http_methods(['GET','POST'])
@login_required
@permission_required(('personnes.view_propositionsaisie','personnes.view_revisionpropositionsaisie'),raise_exception=True)
def liste(request,pk=None,action=None):
    objet=get_object_or_404(PropositionSaisie,pk=pk) if pk else None
    if action:
        from .suivi import exiger
        exiger(request.user,'change_propositionsaisie' if objet else 'add_propositionsaisie')
        initial=propositions.photo(objet) if objet else {'active':True}
        if objet:initial['attendu']=propositions.jeton(objet)
        form=PropositionForm(request.POST if request.method=='POST' else None,initial=initial)
        return traiter(request,form,'Modifier une proposition' if objet else 'Ajouter une proposition',
            lambda attendu=None,**d:propositions.enregistrer(request.user,objet=objet,attendu=attendu,**d),
            reverse('dossiers:propositions'), 'Listes de propositions',
            explication='Ces valeurs sont proposées, jamais imposées. Une modification ne réécrit aucun dossier. Ne pas inscrire de donnée personnelle dans une liste partagée ; la source, les dates, téléphones et identités ne sont jamais collectés depuis les dossiers.')
    return render(request,'dossiers/propositions.html',{'objets':PropositionSaisie.objects.prefetch_related('revisions__auteur')})


@never_cache
@require_http_methods(['GET','POST'])
@login_required
@permission_required(('personnes.view_propositionsaisie','personnes.view_revisionpropositionsaisie'),raise_exception=True)
def echanger(request):
    from django.http import HttpResponse
    from django.core.exceptions import ValidationError
    from .champs_saisie import FormulaireMetier
    from .suivi import exiger
    if request.method=='GET' and request.GET.get('format')=='json':
        r=HttpResponse(propositions.exporter(request.user),content_type='application/json');r['Content-Disposition']='attachment; filename="propositions-saisie.json"';return r
    exiger(request.user,'add_propositionsaisie')
    class ImportForm(FormulaireMetier):
        fichier=forms.FileField(label='Fichier JSON de propositions',help_text='1 Mio et 1 000 propositions au plus. Ajouts uniquement : les valeurs déjà présentes restent inchangées, y compris leur activation. Aucun dossier ni droit n’est importé.')
        motif=forms.CharField(label='Pourquoi ajouter ces propositions ?',max_length=240)
    form=ImportForm(request.POST or None,request.FILES or None);resultat=None
    if request.method=='POST' and form.is_valid():
        try:resultat=propositions.importer(request.user,form.cleaned_data['fichier'].read(1048577),form.cleaned_data['motif'])
        except ValidationError as erreur:form.add_error(None,' '.join(erreur.messages))
        else:form=ImportForm()
    return render(request,'dossiers/propositions_echange.html',{'form':form,'resultat':resultat})
