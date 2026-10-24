from django import forms
from .champs_saisie import FormulaireMetier, FormulaireModeleMetier
from .models import AccordRepas, Personne

DATE = {"type": "date"}


class AccordForm(FormulaireModeleMetier):
    jours_semaine=forms.TypedMultipleChoiceField(label='Jours autorisés (aucun choix : tous les jours)',choices=list(enumerate(['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'])),coerce=int,required=False,widget=forms.CheckboxSelectMultiple)
    saisie_periode = ('debut', 'fin')
    beneficiaires = forms.ModelMultipleChoiceField(Personne.objects.none(), widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = AccordRepas
        fields = ["beneficiaires", "debut", "fin", "service", "prestataire", "jours_semaine"]
        widgets = {nom: forms.DateInput(format="%Y-%m-%d", attrs=DATE) for nom in ("debut", "fin")}

    def __init__(self, *args, accompagnement, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["beneficiaires"].queryset = accompagnement.beneficiaires.all()


class DistributionForm(FormulaireMetier):
    categorie_declaree = forms.CharField(label="Catégorie déclarée (facultative)", max_length=80,required=False,help_text="Par exemple adulte, jeune ou bas âge ; aucune catégorie tarifaire n’est déduite de la naissance.")
    beneficiaire = forms.ModelChoiceField(Personne.objects.none())
    date = forms.DateField(widget=forms.DateInput(format="%Y-%m-%d", attrs=DATE))
    quantite = forms.IntegerField(label="Nombre de repas distribués", min_value=1, max_value=32767, initial=1,
        help_text="Quantité réellement distribuée à cette personne pour ce service. Les statistiques additionnent les quantités, pas les personnes.")

    def __init__(self, *args, accord, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["beneficiaire"].queryset = accord.beneficiaires.all()


class AnnulationForm(FormulaireMetier):
    motif = forms.CharField(label="Motif de l’annulation", max_length=240)


class ServicesForm(FormulaireMetier):
    jours_semaine=forms.TypedMultipleChoiceField(label='Jours autorisés (aucun choix : tous les jours)',choices=list(enumerate(['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'])),coerce=int,required=False,widget=forms.CheckboxSelectMultiple)
    saisie_periode = ('debut', 'fin')
    beneficiaires = forms.ModelMultipleChoiceField(Personne.objects.none(), widget=forms.CheckboxSelectMultiple)
    services = forms.MultipleChoiceField(label='Services à accorder', choices=AccordRepas.SERVICES, widget=forms.CheckboxSelectMultiple)
    debut = forms.DateField(label='Début inclus', widget=forms.DateInput(format='%Y-%m-%d', attrs=DATE))
    fin = forms.DateField(label='Fin exclue — facultative', required=False, widget=forms.DateInput(format='%Y-%m-%d', attrs=DATE))
    prestataire = forms.CharField(label='Prestataire — facultatif', max_length=160, required=False)
    attendu = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, accompagnement, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['beneficiaires'].queryset = accompagnement.beneficiaires.all()
