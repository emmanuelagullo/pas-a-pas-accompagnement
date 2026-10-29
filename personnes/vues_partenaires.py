"""Répertoire transverse ; fiches datées, recherche et retours BD contrôlés."""
import csv
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
from . import partenaires, bd6, dossier, suivi
from .models import Partenaire, FichePartenaire, Accompagnement
from .vues_bd6 import traiter
from .vues_famille import ConsultationForm
from .vues_suivi import _uuid_valide
from .forms_hebergement import date_champ
from .exports import cellule_csv
from .interventions import DROITS_LECTURE as DROITS_MISSIONS


class FicheForm(FormulaireModeleMetier):
    debut = date_champ('Depuis quelle date ces renseignements sont-ils vrais ?')
    motif = forms.CharField(label='Motif de correction ou d’ajout dans le passé', max_length=240, required=False)
    attendu = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = FichePartenaire
        fields = ['debut', *partenaires.CHAMPS, 'source']
        help_texts = {'nom': 'Organisme ou service, distinct d’une personne accompagnée et d’un compte professionnel.',
            'informations': 'Consignes pratiques du partenaire. Pas de données de dossier personnel, de tarif ou de mot de passe.',
            'source': 'Par exemple : coordonnées confirmées par le service lors d’un échange fictif.'}


class RechercheForm(ConsultationForm):
    q = forms.CharField(label='Nom ou ville du partenaire', max_length=160, required=False)


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
@permission_required(partenaires.DROITS_LECTURE, raise_exception=True)
def liste(request):
    params, nav = contexte(request)
    form = RechercheForm(params)
    fiches = FichePartenaire.objects.none()
    if form.is_valid():
        fiches = partenaires.a_date(Partenaire.objects.all(), form.cleaned_data['date'])
        for mot in form.cleaned_data['q'].split():
            fiches = fiches.filter(Q(nom__icontains=mot) | Q(ville__icontains=mot))
        fiches = fiches.order_by('nom', 'partenaire_id')
        if request.GET.get('format') == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="partenaires.csv"'
            w = csv.writer(response, delimiter=';')
            w.writerow(['date_reference', 'partenaire_id', 'depuis', *partenaires.CHAMPS, 'source'])
            for f in fiches:
                w.writerow([form.cleaned_data['date'].isoformat(), f.partenaire_id, f.debut.isoformat(),
                    *[cellule_csv(getattr(f, c)) for c in partenaires.CHAMPS], cellule_csv(f.source)])
            return response
    page = Paginator(fiches, 25).get_page(request.GET.get('page_annuaire'))
    query = urlencode(params)
    for f in page:
        f.url = reverse('dossiers:partenaire', args=[f.partenaire_id]) + '?' + query
    return render(request, 'dossiers/partenaires.html', {'form': form, 'page_obj': page, 'query_annuaire': query, 'peut_rechercher_missions':request.user.has_perms(DROITS_MISSIONS),
        'params_annuaire': {k:v for k,v in params.items() if k not in ('q','date')}, **nav})


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(partenaires.DROITS_LECTURE, raise_exception=True)
def fiche(request, pk=None, action=None, fait_pk=None):
    params, nav = contexte(request)
    query = urlencode(params)
    objet = get_object_or_404(Partenaire, pk=pk) if pk else None
    attendu = bd6.jeton(objet) if objet else partenaires.jeton_creation()
    faits = objet.fiches.select_related('auteur') if objet else FichePartenaire.objects.none()
    if action:
        partenaires.droits(request.user)
        if objet is None:
            suivi.exiger(request.user, 'add_partenaire')
        corrigee = get_object_or_404(faits, pk=fait_pk) if fait_pk else None
        if corrigee:
            suivi.exiger(request.user, 'change_fichepartenaire')
        from .champs_saisie import valeurs_proposees
        initial, proposition = valeurs_proposees(request, faits, partenaires.CHAMPS, corrigee)
        initial["attendu"] = attendu
        form = FicheForm(request.POST if request.method == 'POST' else None, initial=initial)
        form.fields['motif'].required = False
        base = reverse('dossiers:partenaire', args=[pk]) + '?' + query if objet else reverse('dossiers:partenaires') + '?' + query
        return traiter(request, form, 'Corriger la fiche partenaire' if corrigee else 'Mettre à jour le partenaire' if objet else 'Créer un organisme partenaire',
            lambda **d: partenaires.renseigner(request.user, objet, correction=corrigee.pk if corrigee else None, **d) if objet else partenaires.creer(request.user, **d),
            base if objet else lambda p: reverse('dossiers:partenaire', args=[p.pk]) + '?' + query,
            objet or 'Répertoire des organismes', annuler=base, **proposition,
            explication='Vérifiez les renseignements proposés. Un changement crée une période ; une correction conserve l’avant/après. Les anciens textes des dossiers ne sont pas rapprochés automatiquement.')
    consultation = RechercheForm(params)
    courante = partenaires.a_date([objet], consultation.cleaned_data['date']).first() if consultation.is_valid() else None
    return render(request, 'dossiers/partenaire.html', {'objet': objet, 'fiche': courante, 'faits': faits,
        'consultation': consultation, 'query_annuaire': query, 'peut_rechercher_missions':request.user.has_perms(DROITS_MISSIONS),
        'params_annuaire': {k:v for k,v in params.items() if k not in ('q','date')},
        'retour': reverse('dossiers:partenaires') + '?' + query, 'revisions': objet.revisionfichepartenaire_set.select_related('auteur'), **nav})
