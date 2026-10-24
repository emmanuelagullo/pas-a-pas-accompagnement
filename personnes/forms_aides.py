from decimal import Decimal
from django import forms
from . import models as m, aides
from .champs_saisie import FormulaireMetier,FormulaireModeleMetier
from .forms_hebergement import date_champ


class TypeForm(FormulaireModeleMetier):
    attendu=forms.CharField(widget=forms.HiddenInput)
    motif=forms.CharField(label='Motif',max_length=240)
    class Meta:
        model=m.TypeAide
        fields=list(aides.CATALOGUE)
        help_texts={'unite':'Ce qui sera effectivement compté : carte, titre, bon, colis, kg, passage…',
            'precision':'Par exemple : carte donnant droit à trois voyages. Les cartes remises ne sont pas des voyages effectués.'}


class AccordForm(FormulaireModeleMetier):
    saisie_periode=('debut','fin')
    attendu=forms.CharField(widget=forms.HiddenInput)
    motif=forms.CharField(label='Motif de correction ou prolongation',max_length=240,required=False)
    beneficiaires=forms.ModelMultipleChoiceField(m.Personne.objects.none(),widget=forms.CheckboxSelectMultiple,label='Personnes explicitement concernées')
    class Meta:
        model=m.AccordAide
        fields=['type_aide','beneficiaires',*aides.CHAMPS]
        help_texts={'quantite':'Plafond global pour toute la sélection, pas par personne. Vide : quantité non chiffrée, pas zéro ni une remise.',
            'financeur':'Organisme annoncé, sans engager un paiement ni créer une imputation comptable.',
            'valeur_bon':'Valeur faciale par bon, si connue ; distincte du coût et du financement.',
            'fin':'Fin exclue de l’autorisation. Ne prouve aucune réalisation.'}
    def __init__(self,*args,accompagnement,nature=None,**kw):
        super().__init__(*args,**kw)
        self.fields['beneficiaires'].queryset=accompagnement.beneficiaires.all()
        self.fields['type_aide'].queryset=m.TypeAide.objects.filter(actif=True)
        if nature:self.fields['type_aide'].queryset=self.fields['type_aide'].queryset.filter(nature=nature)
    def clean(self):
        d=super().clean()
        if d.get('type_aide'):self.instance.nature=d['type_aide'].nature
        return d
    def clean_devise(self):return self.cleaned_data['devise'].upper()


class RemiseForm(FormulaireMetier):
    beneficiaires=forms.ModelMultipleChoiceField(m.Personne.objects.none(),widget=forms.CheckboxSelectMultiple,label='Personnes concernées par cette remise')
    date=date_champ('Date réellement effectuée')
    quantite=forms.DecimalField(label='Quantité totale pour toute la sélection',max_digits=14,decimal_places=3,min_value=Decimal('0.001'))
    source=forms.CharField(label='Source de la réalisation',max_length=160)
    motif=forms.CharField(label='Motif de correction',max_length=240,required=False)
    attendu=forms.CharField(widget=forms.HiddenInput)
    def __init__(self,*args,accord,**kw):
        super().__init__(*args,**kw);self.fields['beneficiaires'].queryset=accord.beneficiaires.all()
        self.fields['quantite'].help_text='Unité : '+accord.unite+' ; '+accord.precision


class UsageForm(FormulaireMetier):
    date=date_champ('Date du constat')
    quantite=forms.DecimalField(label='Unités utilisées déclarées',max_digits=14,decimal_places=3,min_value=0,required=False,
        help_text='Vide : inconnu. 0 : explicitement non utilisé. La remise ne prouve jamais l’utilisation ; un titre ne prouve pas un trajet.')
    source=forms.CharField(label='Source du constat',max_length=160)
    motif=forms.CharField(label='Motif du nouveau constat ou de correction',max_length=240,required=False)
    attendu=forms.CharField(widget=forms.HiddenInput)
