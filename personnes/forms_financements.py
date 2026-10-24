from decimal import Decimal
from django import forms
from . import models as m,financements as s
from .champs_saisie import FormulaireMetier,FormulaireModeleMetier
from .forms_hebergement import date_champ


class TarifForm(FormulaireModeleMetier):
    saisie_periode=('debut','fin')
    attendu=forms.CharField(widget=forms.HiddenInput)
    action=forms.ChoiceField(label='Nature de la modification',choices=m.VersionTarif._meta.get_field('action').choices)
    class Meta:
        model=m.VersionTarif
        fields=[*s.TARIF,'motif']
        help_texts={'debut':'Date du nouveau prix ou de la correction. Les calculs déjà enregistrés gardent leur prix.',
            'unite':'Exemples : chambre-nuit, personne-nuit, petit déjeuner, repas, carte. Aucun multiplicateur implicite.',
            'categorie':'Déclarée explicitement, sans déduction à partir de l’âge.', 'devise':'Trois lettres, sans conversion automatique (EUR, CHF, FRF pour une reprise historique…).'}
    def clean_devise(self):return self.cleaned_data['devise'].upper()


class CalculForm(FormulaireModeleMetier):
    saisie_periode=('debut','fin')
    attendu=forms.CharField(widget=forms.HiddenInput)
    action=forms.ChoiceField(label='Nature de cette version',choices=m.VersionFinancement._meta.get_field('action').choices)
    class Meta:
        model=m.VersionFinancement
        fields=[*s.ENTETE,'motif']
        help_texts={'emetteur':'Organisme au nom duquel ce document est préparé, sans déduction depuis votre compte.',
            'mentions':'Conditions particulières à faire apparaître sur le bon (ex. repas chaud, modalités de présentation). Les données financières restent dans les lignes structurées.',
            'facturation':'Destinataire du document ; distinct du prestataire et des financeurs indiqués ci-dessous.',
            'signataire':'Professionnel désigné, distinct de votre compte de saisie. Aucune signature automatique.',
            'fin':'Période du calcul uniquement. Ne prolonge ni autorisation ni séjour.'}
    def clean_devise(self):return self.cleaned_data['devise'].upper()


class LigneForm(FormulaireMetier):
    phase=forms.ChoiceField(choices=[('','Choisir la phase'),*m.LigneCout.PHASES],label='Phase')
    date=date_champ('Date du tarif applicable')
    tarif=forms.ModelChoiceField(m.VersionTarif.objects.select_related('tarif').all(),required=False,label='Tarif conservé (facultatif)',
        help_text='Choisir puis « Reprendre les tarifs choisis » remplit libellé, unité, catégorie et prix. La quantité reste à vérifier.')
    libelle=forms.CharField(label='Composante',max_length=160)
    unite=forms.CharField(label='Unité facturée',max_length=60)
    categorie=forms.CharField(label='Catégorie déclarée',max_length=80,required=False)
    quantite=forms.DecimalField(label='Quantité totale',max_digits=14,decimal_places=3,min_value=0,
        help_text='Globale à cette ligne, jamais multipliée automatiquement par le nombre de personnes ou de jours.')
    prix=forms.DecimalField(label='Prix par unité',max_digits=14,decimal_places=4,min_value=0)
    justification=forms.CharField(label='Origine de la quantité / référence de pièce',max_length=240,
        help_text='Pour le réalisé : indiquer les distributions, remises, nuitées ou la pièce vérifiée. Aucun fait n’est créé par ce calcul.')


class ImputationForm(FormulaireMetier):
    phase=forms.ChoiceField(choices=[('','Choisir la phase'),*m.LigneCout.PHASES],label='Phase financée')
    financeur=forms.ModelChoiceField(m.Partenaire.objects.all(),label='Financeur explicite')
    budget=forms.CharField(label='Budget / dispositif',max_length=160)
    montant=forms.DecimalField(label='Montant affecté',max_digits=20,decimal_places=2,min_value=Decimal('0'))
    reference=forms.CharField(label='Référence de décision',max_length=100,required=False)


LignesFormSet=forms.formset_factory(LigneForm,extra=1,can_delete=True,max_num=100,validate_max=True,absolute_max=101)
ImputationsFormSet=forms.formset_factory(ImputationForm,extra=1,can_delete=True,max_num=100,validate_max=True,absolute_max=101)


class EmissionForm(FormulaireMetier):
    modele=forms.ChoiceField(label='Document',choices=m.DocumentFinancement.MODELES)
    phase=forms.ChoiceField(label='Phase chiffrée',choices=m.LigneCout.PHASES)
    date=date_champ('Date d’émission')
    remplace=forms.ModelChoiceField(m.DocumentFinancement.objects.none(),label='Remplace un document annulé (facultatif)',required=False)
    attendu=forms.CharField(widget=forms.HiddenInput)
    def __init__(self,*args,accord,**kw):
        super().__init__(*args,**kw)
        f=s.financement(accord)
        self.fields['remplace'].queryset=m.DocumentFinancement.objects.filter(version__financement=f,annulation__isnull=False,remplacement__isnull=True) if f else m.DocumentFinancement.objects.none()
