"""Consultation des statistiques agrégées CHRS10."""
from datetime import timedelta
import csv
from django import forms
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET
from .statistiques import bilan


class PeriodeStatistiquesForm(forms.Form):
    debut = forms.DateField(label='Début inclus', widget=forms.DateInput(attrs={'type': 'date'}))
    fin = forms.DateField(label='Fin exclue', widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        valeurs = super().clean()
        if valeurs.get('debut') and valeurs.get('fin') and valeurs['fin'] <= valeurs['debut']:
            self.add_error('fin', 'La fin doit être postérieure au début.')
        return valeurs


@require_GET
@login_required
@permission_required(('personnes.view_accompagnement', 'personnes.view_sejour',
                      'personnes.view_repasdistribue'), raise_exception=True)
def statistiques(request):
    aujourd_hui = timezone.localdate()
    initial = {'debut': aujourd_hui.replace(day=1), 'fin': aujourd_hui + timedelta(days=1)}
    formulaire = PeriodeStatistiquesForm(request.GET or None, initial=initial)
    resultats = bilan(**formulaire.cleaned_data) if formulaire.is_valid() else None
    if request.GET.get('format') == 'csv' and resultats is not None:
        reponse = HttpResponse(content_type='text/csv; charset=utf-8')
        reponse['Content-Disposition'] = 'attachment; filename="statistiques-chrs.csv"'
        writer = csv.writer(reponse)
        writer.writerow(['debut_inclus', 'fin_exclue', 'indicateur', 'valeur'])
        for indicateur, valeur in resultats.items():
            writer.writerow([formulaire.cleaned_data['debut'].isoformat(),
                             formulaire.cleaned_data['fin'].isoformat(), indicateur, valeur])
        return reponse
    periode = formulaire.cleaned_data if formulaire.is_valid() else {}
    return render(request, 'suivi/statistiques.html', {
        'formulaire': formulaire, 'resultats': resultats,
        'debut_iso': periode['debut'].isoformat() if periode else '',
        'fin_iso': periode['fin'].isoformat() if periode else '',
    })
