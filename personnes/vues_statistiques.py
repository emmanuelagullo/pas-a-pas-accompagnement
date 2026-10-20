"""Consultation des statistiques agrégées CHRS10."""
from datetime import timedelta
import csv
from django import forms
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.http import QueryDict
from django.utils import timezone
from django.views.decorators.http import require_GET
from .statistiques import bilan, evolution_mensuelle, ventilation_repas


RAPPORTS = {
    'synthese': 'Synthèse de l’activité',
    'hebergement': 'Hébergement et nuitées',
    'repas': 'Repas distribués',
    'mensuel': 'Évolution mensuelle',
}


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
    rapport = request.GET.get('rapport', 'synthese')
    if rapport not in RAPPORTS:
        rapport = 'synthese'
    resultats = bilan(**formulaire.cleaned_data) if formulaire.is_valid() else None
    evolution = []
    services = {}
    erreur_evolution = ''
    if resultats is not None:
        services = ventilation_repas(**formulaire.cleaned_data)
        try:
            evolution = evolution_mensuelle(**formulaire.cleaned_data)
        except ValueError as exc:
            erreur_evolution = str(exc)
    if request.GET.get('format') == 'csv' and resultats is not None:
        reponse = HttpResponse(content_type='text/csv; charset=utf-8')
        reponse['Content-Disposition'] = 'attachment; filename="statistiques-chrs.csv"'
        writer = csv.writer(reponse)
        if rapport == 'mensuel':
            if erreur_evolution:
                return HttpResponse(erreur_evolution, status=400, content_type='text/plain; charset=utf-8')
            colonnes = ('mois', 'debut', 'fin', 'admissions', 'sorties',
                        'nuitees_theoriques', 'repas_distribues')
            writer.writerow(colonnes)
            for ligne in evolution:
                writer.writerow([ligne[cle] for cle in colonnes])
        elif rapport == 'repas':
            writer.writerow(['debut_inclus', 'fin_exclue', 'service', 'quantite_distribuee'])
            for service, quantite in services.items():
                writer.writerow([formulaire.cleaned_data['debut'].isoformat(),
                                 formulaire.cleaned_data['fin'].isoformat(), service, quantite])
        else:
            writer.writerow(['debut_inclus', 'fin_exclue', 'indicateur', 'valeur'])
            indicateurs = resultats if rapport == 'synthese' else {
                cle: resultats[cle] for cle in (
                    'personnes_avec_sejour', 'sejours', 'admissions', 'sorties',
                    'nuitees_theoriques', 'nuits_distinctes',
                    'nuits_hors_absences_declarees')}
            for indicateur, valeur in indicateurs.items():
                writer.writerow([formulaire.cleaned_data['debut'].isoformat(),
                                 formulaire.cleaned_data['fin'].isoformat(), indicateur, valeur])
        return reponse
    periode = formulaire.cleaned_data if formulaire.is_valid() else {}
    return render(request, 'suivi/statistiques.html', {
        'formulaire': formulaire, 'resultats': resultats,
        'rapport': rapport, 'rapports': RAPPORTS,
        'evolution': evolution, 'services': services, 'erreur_evolution': erreur_evolution,
        'debut_iso': periode['debut'].isoformat() if periode else '',
        'fin_iso': periode['fin'].isoformat() if periode else '',
    })
