from django import forms
from django.utils import timezone
from .champs_saisie import FormulaireMetier
from .forms_hebergement import date_champ
from . import exploration as e,models as m


class AppelsRechercheForm(FormulaireMetier):
    debut=date_champ('Du (inclus)');fin=date_champ('Au (exclu)')
    q=forms.CharField(label='Recherche dans l’appel ou les noms connus',max_length=160,required=False)
    motif_principal=forms.CharField(label='Demande principale exacte',max_length=160,required=False)
    type_appelant=forms.ChoiceField(label='Qui appelle',choices=[('','Tous'),*m.VersionAppel115.TYPES],required=False)
    lieu_appel=forms.CharField(label='Lieu / origine exact',max_length=160,required=False)
    secondaire=forms.CharField(label='Autre demande exacte',max_length=160,required=False)
    reponse=forms.CharField(label='Réponse exacte',max_length=160,required=False)
    etat_reponse=forms.ChoiceField(label='État de réponse',choices=[('','Tous'),*m.VersionAppel115._meta.get_field('etat_reponse').choices],required=False)
    heure_min=forms.IntegerField(label='Heure à partir de (incluse)',min_value=0,max_value=23,required=False)
    heure_max=forms.IntegerField(label='Heure avant (exclue)',min_value=1,max_value=24,required=False)
    annules=forms.BooleanField(label='Inclure les appels annulés',required=False)
    def clean(self):
        d=super().clean()
        if d.get('debut') and d.get('fin') and d['fin']<=d['debut']:self.add_error('fin','La fin exclue doit suivre le début.')
        if d.get('heure_min') is not None and d.get('heure_max') is not None and d['heure_max']<=d['heure_min']:self.add_error('heure_max','La fin exclue doit suivre le début ; pour traverser minuit, sélectionner les deux plages séparément.')
        return d


class ExplorationForm(FormulaireMetier):
    population=forms.ChoiceField(choices=e.POPULATIONS)
    debut=date_champ('Période — début inclus');fin=date_champ('Période — fin exclue')
    reference=date_champ('Situation personnelle et âge à la date de référence')
    periode=forms.ChoiceField(label='Période relative facultative',choices=[('','Dates fixes'),('mois','Mois en cours'),('mois_precedent','Mois précédent'),('annee','Année en cours'),('annee_precedente','Année précédente'),('douze_mois','Douze derniers mois')],required=False,
        help_text='Recalculée à chaque ouverture du modèle ; la référence devient le dernier jour inclus.')
    mesure=forms.ChoiceField(choices=[('objets','Nombre d’objets de la population'),('personnes','Personnes connues distinctes'),('menages','Ménages explicitement connus distincts'),('quantite','Somme des quantités / montants, par unité'),('minimum','Minimum connu, par unité'),('maximum','Maximum connu, par unité'),('moyenne','Moyenne des valeurs connues, par unité'),('adultes_declares','Adultes déclarés par appel (non dédoublonnés)'),('enfants_declares','Enfants déclarés par appel (non dédoublonnés)'),('grossesses_declarees','Grossesses déclarées par appel (non dédoublonnées)')])
    axe=forms.ChoiceField(label='Classer par')
    croisement=forms.ChoiceField(label='Croiser avec',required=False)
    classes=forms.CharField(label='Classes numériques de l’axe (facultatives)',required=False,widget=forms.Textarea(attrs={'rows':3}),max_length=3000,help_text='Une ligne « nom | minimum inclus | maximum exclu ». Bornes vides possibles. Les inconnus et valeurs hors classes restent visibles.')
    filtre1=forms.ChoiceField(label='Premier filtre',required=False)
    operation1=forms.ChoiceField(label='Condition',choices=[('egal','Égal à'),('un_de','Un des éléments séparés par ;'),('different','Différent, si renseigné'),('contient','Contient'),('inconnu','Non renseigné'),('gte','Au moins (nombre)'),('lt','Moins de (nombre)'),('depuis','Depuis une date (incluse)'),('avant','Avant une date (exclue)')])
    valeur1=forms.CharField(label='Valeur',max_length=160,required=False)
    filtre2=forms.ChoiceField(label='Second filtre (ET)',required=False)
    operation2=forms.ChoiceField(label='Condition',choices=operation1.choices)
    valeur2=forms.CharField(label='Valeur',max_length=160,required=False)
    filtres=forms.IntegerField(min_value=2,max_value=20,required=False,initial=2,widget=forms.HiddenInput)
    classes_croisement=forms.CharField(label='Classes numériques du croisement (facultatives)',required=False,max_length=3000,widget=forms.Textarea(attrs={'rows':3}),help_text='Même convention : minimum inclus, maximum exclu ; inconnus et hors classes conservés.')
    def __init__(self,*args,acteur,**kw):
        super().__init__(*args,**kw);dims=list(e.disponibles(acteur).items())
        self.fields['axe'].choices=dims
        for c in ('croisement','filtre1','filtre2'):self.fields[c].choices=[('','Aucun'),*dims]
        import copy
        try:n=int((args[0] if args and args[0] else kw.get('initial',{})).get('filtres') or 2)
        except (ValueError,TypeError):n=2
        for i in range(3,min(n,20)+1):
            for champ in ('filtre','operation','valeur'):
                self.fields[champ+str(i)]=copy.deepcopy(self.fields[champ+'2'])
                self.fields[champ+str(i)].label='Filtre '+str(i)+' (ET)' if champ=='filtre' else 'Condition' if champ=='operation' else 'Valeur'
        data=args[0] if args and args[0] else {}
        for i in range(1,min(n,20)+1):
            operation=data.get('operation'+str(i))
            if operation in ('gte','lt'):self.fields['valeur'+str(i)].widget.attrs['inputmode']='decimal'
            if operation in ('depuis','avant'):self.fields['valeur'+str(i)].widget=forms.DateInput(attrs={'type':'date'})


    def clean(self):
        d=super().clean()
        if d.get('debut') and d.get('fin') and d['fin']<=d['debut']:self.add_error('fin','La fin exclue doit suivre le début.')
        for i in range(1,(d.get('filtres') or 2)+1):
            if d.get('filtre'+str(i)) and d.get('operation'+str(i))!='inconnu' and not d.get('valeur'+str(i)):
                self.add_error('valeur'+str(i),'Indiquez la valeur du filtre.')
            if d.get('filtre'+str(i)) and d.get('valeur'+str(i)) and d.get('operation'+str(i)) in ('gte','lt'):
                try:d['valeur'+str(i)]=str(forms.DecimalField(localize=True).clean(d['valeur'+str(i)]))
                except forms.ValidationError as exc:self.add_error('valeur'+str(i),exc)

        try:
            e.classes(d.get('classes',''));e.classes(d.get('classes_croisement',''))
        except forms.ValidationError as exc:self.add_error('classes',exc)
        return d
