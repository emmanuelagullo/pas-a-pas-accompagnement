"""Répertoire transverse ; fiches datées, recherche et retours BD contrôlés."""
import csv
from urllib.parse import urlencode
from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe
from . import intervenants, bd6, dossier, suivi
from .models import Intervenant, FicheIntervenant, Accompagnement
from .vues_bd6 import traiter
from .vues_famille import ConsultationForm
from .vues_suivi import _uuid_valide
from .forms_hebergement import date_champ
from .exports import cellule_csv


class FicheForm(forms.ModelForm):
    debut = date_champ('Depuis quelle date ces renseignements sont-ils vrais ?')
    motif = forms.CharField(label='Motif de correction ou d’ajout dans le passé', max_length=240, required=False)
    attendu = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = FicheIntervenant
        fields = ['debut', *intervenants.CHAMPS, 'source']
        help_texts = {'nom': 'Professionnel identifié, distinct d’un compte utilisateur et d’une personne accompagnée.',
            'organisme': 'Organisation du répertoire, facultative. Ce lien ne donne aucun droit et ne crée aucune affectation à une prise.', 'source': 'Indiquez comment ces renseignements ont été confirmés.'}


class RechercheForm(ConsultationForm):
    q = forms.CharField(label='Nom ou fonction du professionnel', max_length=160, required=False)


def contexte(request):
    nav = {}
    prise = request.GET.get('prise', '')
    if _uuid_valide(prise) and request.user.has_perms(dossier.DROITS):
        a = Accompagnement.objects.filter(pk=prise).first()
        nav = dossier.lire(request, a)
    params = {'q': request.GET.get('q', '')[:160], 'date': request.GET.get('date') or timezone.localdate().isoformat()}
    if nav:
        params.update(prise=prise, contexte_dossier=nav['contexte_dossier'])
    return params, nav


@never_cache
@require_safe
@login_required
@permission_required(intervenants.DROITS_LECTURE, raise_exception=True)
def liste(request):
    params, nav = contexte(request)
    form = RechercheForm(params)
    fiches = FicheIntervenant.objects.none()
    if form.is_valid():
        fiches = intervenants.a_date(Intervenant.objects.all(), form.cleaned_data['date'])
        for mot in form.cleaned_data['q'].split():
            fiches = fiches.filter(Q(nom__icontains=mot) | Q(fonction__icontains=mot))
        fiches = fiches.select_related('organisme').order_by('nom', 'intervenant_id')
        if request.GET.get('format') == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="intervenants.csv"'
            w = csv.writer(response, delimiter=';')
            w.writerow(['date_reference', 'intervenant_id', 'depuis', *intervenants.CHAMPS, 'source'])
            for f in fiches:
                w.writerow([form.cleaned_data['date'].isoformat(), f.intervenant_id, f.debut.isoformat(),
                    *[cellule_csv(getattr(f, c)) for c in intervenants.CHAMPS], cellule_csv(f.source)])
            return response
    page = Paginator(fiches, 25).get_page(request.GET.get('page_annuaire'))
    query = urlencode(params)
    for f in page:
        f.url = reverse('dossiers:intervenant', args=[f.intervenant_id]) + '?' + query
    return render(request, 'dossiers/intervenants.html', {'form': form, 'page_obj': page, 'query_annuaire': query,
        'params_annuaire': {k:v for k,v in params.items() if k not in ('q','date')}, **nav})


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(intervenants.DROITS_LECTURE, raise_exception=True)
def fiche(request, pk=None, action=None, fait_pk=None):
    params, nav = contexte(request)
    query = urlencode(params)
    objet = get_object_or_404(Intervenant, pk=pk) if pk else None
    attendu = bd6.jeton(objet) if objet else intervenants.jeton_creation()
    faits = objet.fiches.select_related('auteur') if objet else FicheIntervenant.objects.none()
    if action:
        intervenants.droits(request.user)
        if objet is None:
            suivi.exiger(request.user, 'add_intervenant')
        corrigee = get_object_or_404(faits, pk=fait_pk) if fait_pk else None
        if corrigee:
            suivi.exiger(request.user, 'change_ficheintervenant')
        precedente = corrigee or faits.first()
        initial = {c: getattr(precedente, c) for c in intervenants.CHAMPS} if precedente else {}
        initial.update(attendu=attendu, debut=corrigee.debut if corrigee else timezone.localdate(), source=corrigee.source if corrigee else '')
        form = FicheForm(request.POST if request.method == 'POST' else None, initial=initial)
        form.fields['motif'].required = bool(corrigee)
        if not request.user.has_perm('personnes.view_partenaire'):
            form.fields['organisme'].queryset = form.fields['organisme'].queryset.none()
        base = reverse('dossiers:intervenant', args=[pk]) + '?' + query if objet else reverse('dossiers:intervenants') + '?' + query
        return traiter(request, form, 'Corriger la fiche intervenant' if corrigee else 'Mettre à jour le professionnel' if objet else 'Créer un professionnel',
            lambda **d: intervenants.renseigner(request.user, objet, correction=corrigee.pk if corrigee else None, **d) if objet else intervenants.creer(request.user, **d),
            base if objet else lambda p: reverse('dossiers:intervenant', args=[p.pk]) + '?' + query,
            objet or 'Répertoire des professionnels', annuler=base,
            explication='Vérifiez les renseignements proposés. Un changement crée une période ; une correction conserve l’avant/après. Les anciens textes des dossiers ne sont pas rapprochés automatiquement.')
    consultation = RechercheForm(params)
    courante = intervenants.a_date([objet], consultation.cleaned_data['date']).first() if consultation.is_valid() else None
    return render(request, 'dossiers/intervenant.html', {'objet': objet, 'fiche': courante, 'faits': faits,
        'consultation': consultation, 'query_annuaire': query,
        'params_annuaire': {k:v for k,v in params.items() if k not in ('q','date')},
        'retour': reverse('dossiers:intervenants') + '?' + query, 'revisions': objet.revisionficheintervenant_set.select_related('auteur'), **nav})
