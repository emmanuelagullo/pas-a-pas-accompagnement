from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from . import bd6, models as m, retraits_chronologiques as service
from .champs_saisie import FormulaireMetier
from .presentation_dossier_complet import lignes
from .vues_bd6 import navigation_histoire, traiter


class RetraitForm(FormulaireMetier):
    attendu = forms.CharField(widget=forms.HiddenInput)
    preuve_portee = forms.CharField(widget=forms.HiddenInput)
    motif = forms.CharField(label='Contexte du retrait (facultatif)', max_length=240, required=False)
    confirmer = forms.BooleanField(label='Je confirme le retrait de ce changement et le rétablissement indiqué ci-dessus')


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
def retirer(request, pk, code, fait_pk):
    personne = get_object_or_404(m.Personne, pk=pk)
    # Le jeton est capturé avant les lectures qui servent à la confirmation.
    attendu = bd6.jeton(personne)
    try:
        serie, fait, precedent = service.apercu(request.user, personne, code, fait_pk)
    except ValidationError:
        raise Http404
    _, _, retour, query = navigation_histoire(request, personne)
    form = RetraitForm(request.POST if request.method == 'POST' else None, initial={
        'attendu': attendu, 'preuve_portee': service.preuve(code, personne, fait, precedent)})
    if not request.headers.get('X-Condition-Form'):
        retour = reverse('dossiers:social', args=[pk]) + '?' + query if serie.dimension else retour
    return traiter(request, form, 'Retirer ce changement — ' + serie.titre,
        lambda **d: service.retirer(request.user, personne, code, fait_pk, **d), retour, personne,
        explication='Ce changement restera dans le journal. Le retrait ne signifie pas que la situation a réellement changé de nouveau.',
        condition_portee={'debut': fait.debut, 'fin': fait.fin, 'retrait': True,
            'retablissement': ([('Situation', precedent.libelle_valeur)] if serie.dimension else lignes(serie.modele, precedent, serie.champs)) if precedent else [],
            'entrees': service.prises_concernees(request.user, personne, fait.debut, fait.fin),
            'groupe': not bool(serie.dimension)})
