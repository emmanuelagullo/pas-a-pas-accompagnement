"""Vue dédiée à la trajectoire, sans exposer les informations non autorisées."""
from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET
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
    if form.is_valid():
        selection = form.cleaned_data['beneficiaire']
        beneficiaire = next((p for p in accompagnement.beneficiaires.all()
                             if str(p.pk) == selection), None) if selection else None
        lignes = trajectoire.construire(accompagnement, request.user, beneficiaire,
                                       form.cleaned_data['debut'], form.cleaned_data['fin'])
    return render(request, 'social/trajectoire.html', {
        'accompagnement': accompagnement, 'form': form, 'lignes': lignes,
    })
