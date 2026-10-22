from django import forms
from .models import Personne


class MenageForm(forms.Form):
    libelle = forms.CharField(label="Libellé du ménage", max_length=160)
    personnes = forms.ModelMultipleChoiceField(Personne.objects.all(), label="Personnes", widget=forms.CheckboxSelectMultiple)
    debut = forms.DateField(label="Début inclus", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}))


class AppartenanceForm(forms.Form):
    personne = forms.ModelChoiceField(Personne.objects.all())
    debut = forms.DateField(label="Début inclus", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}))
    fin = forms.DateField(label="Fin exclue", required=False, widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}))


class AccompagnementForm(forms.Form):
    fin_prevue = forms.DateField(label="Fin prévue exclue", required=False, widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}), help_text="Prévision uniquement : ne clôture ni la prise en charge ni ses prestations.")
    beneficiaires = forms.ModelMultipleChoiceField(Personne.objects.all(), label="Bénéficiaires explicites", widget=forms.CheckboxSelectMultiple)
    debut = forms.DateField(label="Début inclus", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}))


class ClotureForm(forms.Form):
    fin = forms.DateField(label="Fin exclue — premier jour hors période", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}))
