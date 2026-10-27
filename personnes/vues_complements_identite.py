from django.template.response import TemplateResponse
"""Compléments d’identité déclarés, consultation à date et exploitation."""
import csv
from collections import Counter
from urllib.parse import urlencode

from django import forms
from .champs_saisie import FormulaireModeleMetier
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe

from . import bd6, complements_identite, suivi
from .models import Personne, ComplementIdentite
from .vues_bd6 import navigation_histoire, traiter
from .vues_famille import ConsultationForm
from .forms_hebergement import date_champ
from .exports import cellule_csv


class NationalitesField(forms.CharField):
    def prepare_value(self,value):
        return '\n'.join(value) if isinstance(value,list) else value
    def to_python(self,value):
        texte=super().to_python(value)
        if len(texte)>8000:raise forms.ValidationError('Limitez la déclaration à 8000 caractères.')
        return [v.strip() for v in texte.splitlines() if v.strip()]


class ComplementForm(FormulaireModeleMetier):
    nationalites=NationalitesField(label="Nationalités déclarées",required=False,max_length=8000,widget=forms.Textarea(attrs={"rows":2}),help_text="Une nationalité par ligne. Vide signifie non renseigné ; aucune déduction depuis la naissance ou le ménage.")
    attendu = forms.CharField(widget=forms.HiddenInput)
    debut = date_champ('Depuis quelle date cette situation est-elle vraie ?')
    motif = forms.CharField(label='Motif de correction ou d’ajout dans le passé', max_length=240, required=False)

    class Meta:
        model = ComplementIdentite
        fields = ['debut', *complements_identite.CHAMPS, 'source']
        help_texts = {
            'sexe_declare': 'Libellé déclaré, facultatif. Aucun titre, droit, grossesse ou catégorie de ménage n’en est déduit.',
            'naissance_lieu': 'Précision distincte de la ville et du pays ; ne renseignez pas une adresse actuelle ici.',
            'naissance_pays': 'Pays de naissance déclaré, sans déduction de nationalité.',
            'apatridie_declaree': 'Déclaration distincte d’une absence de renseignement. Ne constitue pas une qualification juridique vérifiée.',
            'source': 'Entretien ou document consulté ; date du fait et date de saisie sont distinctes.',
        }


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(complements_identite.DROITS_LECTURE, raise_exception=True)
def histoire(request, pk, action=None, fait_pk=None):
    personne = get_object_or_404(Personne, pk=pk)
    params, origine, retour, query = navigation_histoire(request, personne)
    if request.GET.get('date'):
        query += ('&' if query else '') + urlencode({'date': request.GET['date'][:20]})
    base = reverse('dossiers:complements_identite', args=[pk]) + ('?' + query if query else '')
    # Réserver la révision lue avant de charger les valeurs du formulaire.
    attendu = bd6.jeton(personne)
    faits = personne.complements_identite.select_related('auteur')
    if action is not None:
        suivi.exiger(request.user, 'add_complementidentite')
        correction = get_object_or_404(faits, pk=fait_pk) if fait_pk else None
        if correction:
            suivi.exiger(request.user, 'change_complementidentite')
        from .champs_saisie import valeurs_proposees
        initial, proposition = valeurs_proposees(request, faits, complements_identite.CHAMPS, correction)
        initial["attendu"] = attendu
        # Ne pas donner l'instance persistée à ModelForm : les modifications
        # validées ne doivent être écrites que par le service et son journal.
        form = ComplementForm(request.POST if request.method == 'POST' else None, initial=initial)
        if correction:
            form.fields['motif'].required = False
            form.fields['debut'].help_text = 'La correction peut rectifier la date, sans traverser une autre déclaration. Les périodes voisines et leur avant/après sont conservés.'
        return traiter(request, form, 'Corriger un complément d’identité' if correction else 'Renseigner les compléments d’identité',
            lambda **d: complements_identite.renseigner(request.user, personne, correction=correction.pk if correction else None, **d),
            base, personne, **proposition, explication='Renseignements déclarés sur cette personne. Une nouvelle information ouvre une période ; corriger une erreur conserve l’avant/après. Le ménage, les bénéficiaires et les droits restent inchangés.')
    form = ConsultationForm(request.GET if 'date' in request.GET else None, initial={'date': timezone.localdate()})
    jour = form.cleaned_data['date'] if form.is_bound and form.is_valid() else timezone.localdate()
    declaration = complements_identite.a_date([personne], jour).first() if not form.is_bound or form.is_valid() else None
    return render(request, 'dossiers/complements_identite.html', {'objet': personne, 'faits': faits,
        'complement': declaration, 'date_situation': jour, 'consultation': form, 'retour': retour,
        'query_identite': query, 'parametres_identite': {**params, **origine},
        'revisions': personne.revisioncomplementidentite_set.select_related('auteur', 'complement')})


class RapportForm(ConsultationForm):
    q=forms.CharField(label='Nom ou prénom',max_length=160,required=False)
    sexe=forms.CharField(label='Sexe déclaré exact',max_length=80,required=False)
    nationalite=forms.CharField(label='Nationalité déclarée exacte',max_length=160,required=False)
    lieu=forms.CharField(label='Lieu de naissance exact',max_length=160,required=False)
    ville=forms.CharField(label='Ville de naissance exacte',max_length=160,required=False)
    apatridie=forms.ChoiceField(label='Apatridie déclarée',choices=[('','Toutes les valeurs'),('oui','Oui déclaré'),('non','Non déclaré'),('inconnue','Non renseignée')],required=False)
    pays=forms.CharField(label='Pays de naissance exact',max_length=160,required=False)
    renseignement=forms.ChoiceField(label='Déclaration',choices=[('','Toutes les fiches'),('connue','Avec une déclaration applicable'),('inconnue','Sans déclaration applicable')],required=False)


@never_cache
@require_safe
@login_required
@permission_required(complements_identite.DROITS_LECTURE,raise_exception=True)
def rapport(request):
    import json
    selection=request.GET.copy()
    if 'date' not in selection:selection['date']=timezone.localdate().isoformat()
    form=RapportForm(selection);lignes=[];bilan=[]
    if form.is_valid():
        d=form.cleaned_data;ps=Personne.objects.all()
        for mot in d['q'].split():ps=ps.filter(Q(designation__icontains=mot)|Q(prenom__icontains=mot))
        applicables={x.personne_id:x for x in complements_identite.a_date(ps,d['date'])}
        comptes=Counter()
        for p in ps.order_by('designation','prenom','pk'):
            f=applicables.get(p.pk)
            if d['renseignement']=='connue' and not f or d['renseignement']=='inconnue' and f:continue
            if d['sexe'] and (not f or f.sexe_declare.casefold()!=d['sexe'].casefold()):continue
            if d['pays'] and (not f or f.naissance_pays.casefold()!=d['pays'].casefold()):continue
            if d['lieu'] and (not f or f.naissance_lieu.casefold()!=d['lieu'].casefold()):continue
            if d['ville'] and (not f or f.naissance_ville.casefold()!=d['ville'].casefold()):continue
            etat=f.apatridie_declaree if f else None
            if d['apatridie'] and etat is not {'oui':True,'non':False,'inconnue':None}[d['apatridie']]:continue
            if d['nationalite'] and (not f or d['nationalite'].casefold() not in {v.casefold() for v in f.nationalites}):continue
            lignes.append({'personne':p,'complement':f})
            comptes[f.sexe_declare or 'Non renseigné' if f else 'Aucune déclaration applicable']+=1
        bilan=sorted(comptes.items())
        if request.GET.get('format')=='csv':
            response=HttpResponse(content_type='text/csv; charset=utf-8');response['Content-Disposition']='attachment; filename="complements-identite.csv"'
            w=csv.writer(response,delimiter=';');w.writerow(['date_reference','personne_id','personne','debut',*complements_identite.CHAMPS,'source'])
            for x in lignes:
                p,f=x['personne'],x['complement']
                vals=[json.dumps(f.nationalites,ensure_ascii=False) if c=='nationalites' and f else
                    ('Oui' if f.apatridie_declaree else 'Non') if c=='apatridie_declaree' and f and f.apatridie_declaree is not None else getattr(f,c) if f else '' for c in complements_identite.CHAMPS]
                w.writerow([d['date'].isoformat(),p.pk,cellule_csv(p),f.debut.isoformat() if f else '',*[cellule_csv(v) for v in vals],cellule_csv(f.source if f else '')])
            return response
    selection.pop('format',None);selection.pop('page',None)
    return TemplateResponse(request,'dossiers/rapport_complements_identite.html',{'form':form,'page_obj':Paginator(lignes,50).get_page(request.GET.get('page')),'nombre':len(lignes),'bilan':bilan,'query_rapport':selection.urlencode()})
