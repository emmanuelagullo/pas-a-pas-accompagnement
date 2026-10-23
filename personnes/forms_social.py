from . import textes_riches as tr
from django import forms
from .models import SituationSociale, Personne
from .forms_hebergement import date_champ


class SituationForm(forms.Form):
    attendu = forms.CharField(widget=forms.HiddenInput)
    motif = forms.CharField(label="Motif de l’insertion rétroactive", max_length=240, required=False,
        help_text="Requis uniquement pour ajouter une situation oubliée avant une situation déjà renseignée.")
    beneficiaire = forms.ModelChoiceField(Personne.objects.none())
    valeur = forms.ChoiceField()
    debut = date_champ("Date d’effet incluse")
    source = forms.CharField(label="Source de l’information", max_length=160)

    def __init__(self,*args,accompagnement,dimension,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["beneficiaire"].queryset=accompagnement.beneficiaires.all()
        self.fields["valeur"].choices=SituationSociale.VALEURS[dimension]


class CorrectionForm(forms.Form):
    attendu = forms.CharField(widget=forms.HiddenInput)
    valeur = forms.ChoiceField()
    motif = forms.CharField(label="Motif de correction",max_length=240)

    def __init__(self,*args,dimension,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["valeur"].choices=SituationSociale.VALEURS[dimension]


class EvenementForm(forms.Form):
    anterieur = forms.BooleanField(label="Ce fait appartient à l’histoire antérieure à cet accompagnement", required=False,
        help_text="Sa date et sa source sont conservées sans avancer le début de l’accompagnement.")
    beneficiaire = forms.ModelChoiceField(Personne.objects.none())
    date_effet = date_champ("Date de l’événement")
    texte = forms.CharField(label="Événement significatif",max_length=500,widget=forms.Textarea)
    source = forms.CharField(label="Source de l’information",max_length=160)

    def __init__(self,*args,accompagnement,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["beneficiaire"].queryset=accompagnement.beneficiaires.all()


class BilanForm(forms.Form):
    date_effet = date_champ("Date du bilan")
    texte = tr.ChampTexte(label="Bilan court", max_length=2000)


class ConsultationForm(forms.Form):
    date = date_champ("Situation à la date du")
