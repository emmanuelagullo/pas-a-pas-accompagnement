from django import forms
from .champs_saisie import FormulaireModeleMetier
from .models import Personne


class PersonneForm(FormulaireModeleMetier):
    class Meta:
        model = Personne
        fields = ["designation", "prenom", "precision_naissance", "date_naissance", "annee_naissance"]
        widgets = {"date_naissance": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})}
        help_texts = {
            "designation": "Une identité incomplète suffit. Utilisez uniquement des données fictives.",
            "prenom": "Facultatif.",
            "precision_naissance": "Facultatif. Pour une année seule, ne saisissez pas de date fictive au 1er janvier.",
            "date_naissance": "À remplir uniquement pour une date exacte ou estimée.",
            "annee_naissance": "À remplir uniquement si seule l’année est connue ou estimée.",
        }


class CorrectionIdentiteForm(PersonneForm):
    motif = forms.CharField(label="Motif de correction", max_length=240, widget=forms.Textarea(attrs={"rows": 2}))
    attendu = forms.CharField(widget=forms.HiddenInput)
