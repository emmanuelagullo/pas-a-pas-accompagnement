from django import forms
from .models import Personne


class PersonneForm(forms.ModelForm):
    class Meta:
        model = Personne
        fields = ["designation", "prenom"]
        help_texts = {
            "designation": "Une identité incomplète suffit. Utilisez uniquement des données fictives.",
            "prenom": "Facultatif.",
        }
