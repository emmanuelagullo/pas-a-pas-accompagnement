from urllib.parse import urlencode
from django import forms
from django.forms.utils import ErrorDict
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404,render,redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.db import OperationalError
from django.db.models import Q
from .retour_service import contexte_jour
from .vues_hebergement import retour_hebergement
from django.core.exceptions import ValidationError
from . import models as m,annulations_arrivees as s,dossier
from .champs_saisie import FormulaireMetier


class RetraitForm(FormulaireMetier):
    recherche=forms.CharField(label='Rechercher le ménage ou un bénéficiaire du bon accord',max_length=160,required=False)
    attendu=forms.CharField(widget=forms.HiddenInput)
    motif=forms.CharField(label='Pourquoi cette arrivée était-elle une erreur ?',max_length=240,widget=forms.Textarea(attrs={'rows':3}))
    accord_correct=forms.ModelChoiceField(m.AccordHebergement.objects.none(),required=False,label='Accord de remplacement (facultatif)',help_text='Pour corriger une cible : choisir explicitement le bon accord. Les dates du séjour sont conservées.')
    beneficiaires=forms.ModelMultipleChoiceField(m.Personne.objects.none(),required=False,label='Bénéficiaires du remplacement',widget=forms.CheckboxSelectMultiple)
    reprendre_mouvements=forms.BooleanField(required=False,label='Reprendre les lieux et absences dans les arrivées corrigées',help_text='Vérifier ces mouvements avant de confirmer. Les notes et financements ne changent pas de cible.')
    confirmer=forms.BooleanField(label='Je confirme que l’arrivée décrite ci-dessus était erronée, et non une sortie réelle')

    def __init__(self,*args,menage,**kw):
        super().__init__(*args,**kw)
        base=m.AccordHebergement.objects.filter(annule_le__isnull=True)
        recherche=self.data.get('recherche','').strip()[:160]
        if recherche:
            for mot in recherche.split():base=base.filter(Q(accompagnement__menage__libelle__icontains=mot)|Q(beneficiaires__designation__icontains=mot)|Q(beneficiaires__prenom__icontains=mot))
        else:base=base.filter(accompagnement__menage=menage)
        ids=list(base.distinct().order_by('-debut','pk').values_list('pk',flat=True)[:50])
        self.fields['accord_correct'].queryset=m.AccordHebergement.objects.filter(pk__in=ids).select_related('accompagnement__menage').order_by('-debut','pk')
        self.fields['accord_correct'].help_text+=' Au plus 50 accords affichés ; préciser la recherche si nécessaire.'
        self.fields['accord_correct'].label_from_instance=lambda a:f'{a.accompagnement.menage} · prise en charge du {a.accompagnement.debut} · accord du {a.debut} ({a.pk})'
        data=self.data
        try:identifiant=forms.UUIDField(required=False).clean(data.get('accord_correct'))
        except forms.ValidationError:identifiant=None
        a=self.fields['accord_correct'].queryset.filter(pk=identifiant).first() if identifiant else None
        self.fields['beneficiaires'].queryset=a.beneficiaires.all() if a else m.Personne.objects.none()
        if not a:self.fields['beneficiaires'].widget=forms.SelectMultiple()


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def retirer(request,pk):
    s.droits(request.user)
    origine=s.racine(get_object_or_404(m.Sejour.objects.select_related('origine_collective__accord__accompagnement','accord__accompagnement'),pk=pk))
    nav=dossier.lire(request,origine.accord.accompagnement)
    retour=nav.get('retour_dossier') or retour_hebergement(request,origine.accord_id)
    form=RetraitForm(request.POST or None,menage=origine.accord.accompagnement.menage,initial={'attendu':s.jeton(origine)})
    statut=200
    if request.method=='POST' and request.POST.get('action')=='actualiser':
        form._errors=ErrorDict();form.cleaned_data={}
    if request.method=='POST' and request.POST.get('action')!='actualiser' and form.is_valid():
        d=form.cleaned_data;d.pop('confirmer');d.pop('recherche')
        try:journal=s.annuler(request.user,origine,**d)
        except (ValidationError,OperationalError) as erreur:
            form.add_error(None,' '.join(erreur.messages) if isinstance(erreur,ValidationError) else 'Écriture non confirmée ; rechargez avant de réessayer.');statut=409
        else:
            if d['accord_correct']:
                a=d['accord_correct'];navigation=dossier.creer(request,a.accompagnement,None,None)
                parametres={'contexte_dossier':navigation['contexte_dossier']}
                if contexte_jour(request)['retour_jour']:parametres.update(retour='jour',date_service=contexte_jour(request)['date_service'])
                return redirect(reverse('suivi:accord_hebergement',args=[a.pk])+'?'+urlencode(parametres))
            return redirect(retour)
    fs=s.fragments(origine)
    return render(request,'hebergement/annulation_arrivee.html',{**contexte_jour(request),**nav,'origine':origine,'fragments':fs,'form':form,'retour':retour,'journal':m.AnnulationArrivee.objects.filter(origine=origine).first(),'documents_actifs':s.documents_actifs(origine).exists()},status=statut)
