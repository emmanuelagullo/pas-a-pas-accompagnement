from django import forms
from .models import AccordRepas, Personne

DATE = {"type": "date"}


class AccordForm(forms.ModelForm):
    beneficiaires = forms.ModelMultipleChoiceField(Personne.objects.none(), widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = AccordRepas
        fields = ["beneficiaires", "debut", "fin", "service", "prestataire"]
        widgets = {nom: forms.DateInput(format="%Y-%m-%d", attrs=DATE) for nom in ("debut", "fin")}

    def __init__(self, *args, accompagnement, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["beneficiaires"].queryset = accompagnement.beneficiaires.all()


class DistributionForm(forms.Form):
    beneficiaire = forms.ModelChoiceField(Personne.objects.none())
    date = forms.DateField(widget=forms.DateInput(format="%Y-%m-%d", attrs=DATE))
    quantite = forms.IntegerField(label="Nombre de repas distribués", min_value=1, max_value=32767, initial=1,
        help_text="Quantité réellement distribuée à cette personne pour ce service. Les statistiques additionnent les quantités, pas les personnes.")

    def __init__(self, *args, accord, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["beneficiaire"].queryset = accord.beneficiaires.all()


class AnnulationForm(forms.Form):
    motif = forms.CharField(label="Motif de l’annulation", max_length=240)


class ServicesForm(forms.Form):
    beneficiaires = forms.ModelMultipleChoiceField(Personne.objects.none(), widget=forms.CheckboxSelectMultiple)
    services = forms.MultipleChoiceField(label='Services à accorder', choices=AccordRepas.SERVICES, widget=forms.CheckboxSelectMultiple)
    debut = forms.DateField(label='Début inclus', widget=forms.DateInput(format='%Y-%m-%d', attrs=DATE))
    fin = forms.DateField(label='Fin exclue — facultative', required=False, widget=forms.DateInput(format='%Y-%m-%d', attrs=DATE))
    prestataire = forms.CharField(label='Prestataire — facultatif', max_length=160, required=False)
    attendu = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, accompagnement, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['beneficiaires'].queryset = accompagnement.beneficiaires.all()
