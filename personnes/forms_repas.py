from django import forms
from .champs_saisie import FormulaireMetier, FormulaireModeleMetier
from .models import AccordRepas, Personne

DATE = {"type": "date"}


def proposer_categories(form, accord):
    """Propositions de lecture autorisées ; aucune catégorie choisie implicitement."""
    from django.db.models import Exists, OuterRef, CharField
    from django.db.models.functions import Cast
    from acteurs.portees import existante
    from acteurs.models import PorteeObjet
    from .models import RepasDistribue
    from .champs_saisie import PropositionInput
    faits = RepasDistribue.objects.filter(annule_le__isnull=True).exclude(categorie_declaree='')
    origine = existante(accord)
    if origine:
        portees = PorteeObjet.objects.filter(modele=RepasDistribue._meta.label_lower,
            identifiant=Cast(OuterRef('pk'), CharField()), service_id=origine.service_id)
        faits = faits.filter(Exists(portees))
    else:
        faits = faits.filter(accord=accord)
    categories = list(faits.order_by('categorie_declaree').values_list('categorie_declaree', flat=True).distinct()[:50])
    champ = form.fields['categorie_declaree']
    champ.label = 'Catégorie de repas (facultative)'
    champ.help_text = 'Choisissez une catégorie proposée ou saisissez-en une autre. Une valeur vide signifie « Non renseignée ». Aucun tarif n’est déduit.'
    champ.widget = PropositionInput(attrs={'placeholder':'Non renseignée', 'autocomplete':'off'}, propositions=categories)


class CorrectionDistributionForm(FormulaireMetier):
    precisions_facultatives = ('motif',)
    quantite = forms.IntegerField(label='Nombre de repas réellement distribués', min_value=1, max_value=32767)
    categorie_declaree = forms.CharField(max_length=80, required=False)
    motif = forms.CharField(label='Précision sur la correction (facultative)', max_length=240, required=False)
    attendu = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, repas, **kwargs):
        from .correction_repas import jeton
        super().__init__(*args, initial={'quantite':repas.quantite,
            'categorie_declaree':repas.categorie_declaree, 'attendu':jeton(repas)}, **kwargs)
        proposer_categories(self, repas.accord)


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
    age_jeune=forms.IntegerField(label='Âge maximal de la catégorie jeune (inclus)',min_value=0,max_value=120,required=False,initial=12)
    age_bas_age=forms.IntegerField(label='Âge maximal de la catégorie bas âge (inclus)',min_value=0,max_value=120,required=False,initial=2)
    aide_categorie=True

    @property
    def champs_sans_aide(self):
        return [f for f in self if f.name not in ('age_jeune','age_bas_age')]

    categorie_declaree = forms.CharField(label="Catégorie déclarée (facultative)", max_length=80,required=False,help_text="Par exemple adulte, jeune ou bas âge ; Une proposition facultative peut être calculée ci-dessous ; elle doit être vérifiée avant d’enregistrer et ne fixe aucun tarif.")
    beneficiaire = forms.ModelChoiceField(Personne.objects.none())
    date = forms.DateField(widget=forms.DateInput(format="%Y-%m-%d", attrs=DATE))
    quantite = forms.IntegerField(label="Nombre de repas distribués", min_value=1, max_value=32767, initial=1,
        help_text="Quantité réellement distribuée à cette personne pour ce service. Les statistiques additionnent les quantités, pas les personnes.")

    def __init__(self, *args, accord, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["beneficiaire"].queryset = accord.beneficiaires.all()
        proposer_categories(self, accord)


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
