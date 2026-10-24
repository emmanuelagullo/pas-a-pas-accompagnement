from django import forms
from .models import AccordHebergement, LieuHebergement, Personne
from .forms_suivi import ClotureForm


def date_champ(label, required=True):
    return forms.DateField(label=label, required=required, widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}))


class AccordForm(forms.Form):
    beneficiaires = forms.ModelMultipleChoiceField(Personne.objects.none(), widget=forms.CheckboxSelectMultiple)
    debut = date_champ("Début inclus")
    fin = date_champ("Fin exclue", False)

    def __init__(self, *args, beneficiaires, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["beneficiaires"].queryset = beneficiaires


class AdmissionForm(AccordForm):
    fin = None


class PeriodeForm(forms.Form):
    debut = date_champ("Début inclus")
    fin = date_champ("Fin exclue", False)


class AffectationForm(PeriodeForm):
    lieu = forms.ModelChoiceField(LieuHebergement.objects.all())


class LieuForm(forms.ModelForm):
    class Meta:
        model = LieuHebergement
        fields = ["libelle", "organisme", "partenaire"]
        help_texts = {'organisme': 'Réutiliser une fiche du répertoire sans recopier ses coordonnées.',
            'partenaire': 'Seulement si aucun organisme du répertoire n’est choisi. Les anciens libellés restent conservés.'}

    def __init__(self, *args, acteur=None, **kwargs):
        super().__init__(*args, **kwargs)
        if acteur is None or not acteur.has_perm('personnes.view_partenaire'):
            del self.fields['organisme']


class ChangementLieuForm(forms.Form):
    debut = date_champ("Date du changement de lieu")
    lieu = forms.ModelChoiceField(LieuHebergement.objects.all(), label="Nouveau lieu")
    attendu = forms.CharField(widget=forms.HiddenInput)
