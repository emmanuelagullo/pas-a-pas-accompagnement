import csv
from datetime import timedelta
from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from . import interventions, bd6, dossier
from .models import Accompagnement, AffectationIntervenant, Intervenant, Partenaire
from .vues_bd6 import traiter
from .vues_famille import ConsultationForm
from .forms_hebergement import date_champ
from .exports import cellule_csv


class AffectationForm(forms.Form):
    role = forms.ChoiceField(label='Rôle', choices=[('', 'Choisir un rôle'), *AffectationIntervenant.ROLES])
    intervenant = forms.ModelChoiceField(Intervenant.objects.all(), required=False, label='Professionnel du répertoire')
    organisme = forms.ModelChoiceField(Partenaire.objects.all(), required=False, label='Organisme seul', help_text='Choisissez un professionnel OU un organisme si l’interlocuteur n’est pas connu. Aucune identité n’est créée ici.')
    debut = date_champ('Début de la mission inclus')
    fin = date_champ('Fin exclue (si la mission est terminée)', False)
    source = forms.CharField(label='Source de l’affectation', max_length=160)
    motif = forms.CharField(label='Motif de correction, de fin de mission ou d’ajout antérieur', max_length=240, required=False)
    attendu = forms.CharField(widget=forms.HiddenInput)


class ConsultationMissionForm(ConsultationForm):
    role = forms.ChoiceField(label='Rôle consulté', choices=[('', 'Tous les rôles'), *AffectationIntervenant.ROLES], required=False)


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(interventions.DROITS_LECTURE, raise_exception=True)
def gerer(request, pk, action=None, affectation_pk=None):
    from .suivi import exiger
    a = get_object_or_404(Accompagnement.objects.select_related('menage'), pk=pk)
    navigation = dossier.lire(request, a)
    token = navigation.get('contexte_dossier', '')
    from urllib.parse import urlencode
    params = {'contexte_dossier': token, 'date': request.GET.get('date', '')[:20], 'role':request.GET.get('role','')[:30]}
    query = urlencode(params)
    base = reverse('dossiers:interventions', args=[pk]) + '?' + query
    attendu = bd6.jeton(a)
    faits = a.interventions.select_related('intervenant', 'organisme', 'auteur')
    if action:
        exiger(request.user, 'add_affectationintervenant')
        x = get_object_or_404(faits, pk=affectation_pk) if affectation_pk else None
        if x:
            exiger(request.user, 'change_affectationintervenant')
        if action=='annuler':
            exiger(request.user,'annuler_affectationintervenant')
            form=forms.Form(request.POST if request.method=='POST' else None)
            form.fields['motif']=forms.CharField(label='Pourquoi cette affectation était-elle une erreur ?',max_length=240)
            form.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=attendu)
            return traiter(request,form,'Annuler une affectation erronée',lambda **d:interventions.annuler(request.user,a,x,**d),
                base,a.menage,explication='L’affectation et son journal restent consultables ; elle sera exclue des missions et exports courants. Terminer une mission réelle utilise une fin de mission.')
        initial = {champ: getattr(x, champ) for champ in ('role','intervenant','organisme','debut','fin','source')} if x else {'debut': timezone.localdate()}
        initial['attendu'] = attendu
        form = AffectationForm(request.POST if request.method == 'POST' else None, initial=initial)
        form.fields['motif'].required = bool(x)
        if action == 'clore':
            for c in ('role','intervenant','organisme','debut','source'):
                form.fields[c].disabled = True
            form.fields['fin'].required = True
        return traiter(request, form, 'Terminer la mission' if action == 'clore' else 'Corriger une affectation' if x else 'Affecter un professionnel ou organisme',
            lambda **d: interventions.affecter(request.user, a, correction=x.pk if x else None, cloture=action == 'clore', **d),
            base, a.menage, explication='Le rôle est limité à cette prise. Plusieurs professionnels peuvent intervenir ; aucune mission précédente n’est terminée automatiquement. Le référent n’est ni l’auteur de saisie, ni le contact du ménage, ni un représentant légal.')
    jour = a.fin - timedelta(days=1) if a.fin else timezone.localdate()
    consultation = ConsultationMissionForm(request.GET if request.GET.get('date') else None, initial={'date': jour})
    if consultation.is_bound and consultation.is_valid():
        jour = consultation.cleaned_data['date']
    actifs = interventions.presentation(request.user, a, jour) if not consultation.errors else []
    if consultation.is_bound and consultation.is_valid() and consultation.cleaned_data.get('role'):
        actifs = [x for x in actifs if x.role == consultation.cleaned_data['role']]
    if request.GET.get('format') == 'csv' and not consultation.errors:
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="interventions-prise.csv"'
        w = csv.writer(response, delimiter=';'); w.writerow(['date_reference','prise_id','role','professionnel_id','professionnel','organisme_id','organisme','debut','fin','fin_effective','source','fonction_a_date','telephone_a_date','courriel_a_date'])
        for x in actifs:
            f = x.fiche_professionnelle
            w.writerow([jour.isoformat(), a.pk, x.get_role_display(), x.intervenant_id or '', cellule_csv(x.nom_affiche), x.organisme_id or (f.organisme_id if f else '') or '', cellule_csv(x.organisme or (f.organisme if f else '') or ''), x.debut.isoformat(), x.fin.isoformat() if x.fin else '', min(d for d in (x.fin, a.fin) if d).isoformat() if x.fin or a.fin else '', cellule_csv(x.source), cellule_csv(f.fonction if f else ''), cellule_csv(f.telephone if f else ''), cellule_csv(f.courriel if f else '')])
        return response
    return render(request, 'dossiers/interventions.html', {'prise': a, 'faits': faits, 'actifs': actifs, 'date_situation': jour,
        'consultation': consultation, 'query_interventions': query, 'contexte_dossier': token,
        'retour': navigation.get('retour_dossier') or reverse('suivi:accompagnement', args=[pk]),
        'revisions': a.revisionaffectationintervenant_set.select_related('auteur')})
