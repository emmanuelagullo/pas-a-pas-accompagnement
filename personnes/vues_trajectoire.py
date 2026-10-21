from . import dossier
"""Vue dédiée à la trajectoire, sans exposer les informations non autorisées."""
from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET
from django.utils import timezone
from .models import Accompagnement
from . import social, trajectoire


class Filtres(forms.Form):
    beneficiaire = forms.ChoiceField(label='Bénéficiaire', required=False)
    debut = forms.DateField(label='Depuis (inclus)', required=False,
                            widget=forms.DateInput(attrs={'type': 'date'}))
    fin = forms.DateField(label='Jusqu’au (inclus)', required=False,
                          widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, accompagnement, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['beneficiaire'].choices = [('', 'Tous les bénéficiaires')] + [
            (str(p.pk), str(p)) for p in accompagnement.beneficiaires.all()]

    def clean(self):
        valeurs = super().clean()
        if valeurs.get('debut') and valeurs.get('fin') and valeurs['fin'] < valeurs['debut']:
            self.add_error('fin', 'La fin ne peut pas précéder le début.')
        return valeurs


@require_GET
@login_required
def detail(request, pk):
    social.droit(request.user, 'view_situationsociale')
    accompagnement = get_object_or_404(Accompagnement.objects.select_related('menage'), pk=pk)
    form = Filtres(request.GET, accompagnement=accompagnement)
    lignes = []
    comparaison = []
    if form.is_valid():
        selection = form.cleaned_data['beneficiaire']
        beneficiaire = next((p for p in accompagnement.beneficiaires.all()
                             if str(p.pk) == selection), None) if selection else None
        debut = form.cleaned_data['debut']
        fin = form.cleaned_data['fin']
        lignes = trajectoire.construire(accompagnement, request.user, beneficiaire, debut, fin)
        # Comparaison descriptive, uniquement à partir des situations réellement saisies.
        # La borne finale est incluse, contrairement aux fins de séjour.
        date_initiale = max(debut or accompagnement.debut, accompagnement.debut)
        date_finale = min(fin or timezone.localdate(), timezone.localdate())
        if accompagnement.fin:
            from datetime import timedelta
            date_finale = min(date_finale, accompagnement.fin - timedelta(days=1))
        if date_initiale <= date_finale:
            comparaison = trajectoire.comparer(accompagnement, beneficiaire, date_initiale, date_finale)
    return render(request, 'social/trajectoire.html', {
        **dossier.lire(request, accompagnement), 'accompagnement': accompagnement, 'form': form, 'lignes': lignes,
        'comparaison': comparaison,
    })
