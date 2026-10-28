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
    from .presentation_exports import CHOIX as CHOIX_EXPORT
    export_prioritaire=forms.ChoiceField(label='Export à mettre en avant',choices=CHOIX_EXPORT,required=False,help_text='PDF puis CSV restent disponibles dans cet ordre. Ce choix change seulement le bouton principal ; conservez les réglages pour le retrouver.')
    lignes_vides=forms.BooleanField(label='Afficher aussi les mois et services de repas sans distribution',required=False,help_text='Population repas, axes Mois et/ou Service : les cellules vides valent zéro. Les autres populations ne sont pas complétées.')
    sous_totaux=forms.BooleanField(label='Afficher les sous-totaux des niveaux de classement',required=False,help_text='Chaque sous-total utilise les faits de son groupe. Pour les personnes distinctes, une personne compte une fois par groupe et une fois dans le total général, même si elle figure dans plusieurs groupes.')
    cohorte=forms.ChoiceField(label='Faits utilisés pour chaque personne',required=False,choices=[('tous','Tous les objets filtrés'),('premier','Premier objet chronologique dans la sélection filtrée'),('dernier','Dernier objet chronologique dans la sélection filtrée')],help_text='Pour les mesures de personnes distinctes des prises en charge, demandes et prestations. La date du fait/début prime, puis la saisie et l’identifiant départagent les égalités. Ce n’est pas une première admission absolue ; les filtres s’appliquent avant ce choix.')
    mouvement=forms.ChoiceField(label='Lien des faits avec la période',required=False,choices=[('chevauche','Tous les objets chevauchant la période'),('entrees','Seulement les débuts dans la période'),('sorties','Seulement les fins dans la période'),('entrees_sorties','Début et fin dans la période')],help_text='Les fins sont effectives pour les prises en charge et séjours, autorisées pour les accords. Aucune sortie de personne n’est déduite.')
    portion=forms.ChoiceField(label='Nuitées des épisodes retenus',required=False,choices=[('selection','Seulement dans la période'),('integrale','Intégralité des épisodes clos')],help_text='L’intégralité peut dépasser la période. Les absences ne sont pas déduites ; aucun repas réalisé n’est déduit d’un accord.')
    niveaux=forms.IntegerField(min_value=2,max_value=7,required=False,initial=2,widget=forms.HiddenInput)
    affichage=forms.ChoiceField(label='Présentation',required=False,choices=[('synthese','Tableau de synthèse'),('detail','Lignes détaillées des objets retenus')])
    nombre_colonnes=forms.IntegerField(min_value=0,max_value=11,required=False,initial=0,widget=forms.HiddenInput)
    nombre_mesures=forms.IntegerField(min_value=1,max_value=9,required=False,initial=1,widget=forms.HiddenInput)
    population=forms.ChoiceField(label='Sur quoi porte la recherche ?',choices=e.POPULATIONS)
    debut=date_champ('Période — début inclus');fin=date_champ('Période — fin exclue')
    reference_mode=forms.ChoiceField(label='Lire les situations personnelles',required=False,choices=[('commune','À la référence commune'),('fait','À la date du fait ou du début de chaque objet'),('saisie','À la date de saisie initiale de chaque objet')],help_text='La date choisie sert aux filtres et aux regroupements personnels. Les corrections connues aujourd’hui restent prises en compte.')
    reference=date_champ('Situation personnelle et âge à la date de référence')
    from .periodes_rapports import PERIODES
    periode=forms.ChoiceField(label='Période',choices=[('','Dates fixes'),*PERIODES.items()],required=False)
    decalage_debut=forms.IntegerField(label='Début relatif, en jours par rapport à aujourd’hui',min_value=-36600,max_value=36600,required=False,initial=-6)
    decalage_fin=forms.IntegerField(label='Fin exclue relative, en jours par rapport à aujourd’hui',min_value=-36600,max_value=36600,required=False,initial=1)
    mesure=forms.ChoiceField(choices=[('objets','Nombre d’objets de la population'),('personnes','Personnes connues distinctes'),('menages','Ménages explicitement connus distincts'),('quantite','Somme des quantités / montants, par unité'),('minimum','Minimum connu, par unité'),('maximum','Maximum connu, par unité'),('moyenne','Moyenne des valeurs connues, par unité'),('adultes_declares','Adultes déclarés par appel (non dédoublonnés)'),('enfants_declares','Enfants déclarés par appel (non dédoublonnés)'),('grossesses_declarees','Grossesses déclarées par appel (non dédoublonnées)')])
    axe=forms.ChoiceField(label='Classer par')
    croisement=forms.ChoiceField(label='Croiser avec',required=False)
    classes=forms.CharField(label='Classes numériques de l’axe (facultatives)',required=False,widget=forms.Textarea(attrs={'rows':3}),max_length=3000,help_text='Une ligne « nom | minimum inclus | maximum exclu ». Bornes vides possibles. Les inconnus et valeurs hors classes restent visibles.')
    filtre1=forms.ChoiceField(label='Premier filtre',required=False)
    operation1=forms.ChoiceField(label='Condition',choices=[('egal','Égal à'),('egal_sensible','Égalité exacte, casse conservée'),('un_de','Un des éléments séparés par ;'),('different','Différent, si renseigné'),('contient','Contient'),('inconnu','Non renseigné'),('gte','Au moins (nombre)'),('lt','Moins de (nombre)'),('depuis','Depuis une date (incluse)'),('avant','Avant une date (exclue)')])
    valeur1=forms.CharField(label='Valeur',max_length=160,required=False)
    filtre2=forms.ChoiceField(label='Second filtre (ET)',required=False)
    operation2=forms.ChoiceField(label='Condition',choices=operation1.choices)
    valeur2=forms.CharField(label='Valeur',max_length=160,required=False)
    filtres=forms.IntegerField(min_value=2,max_value=20,required=False,initial=2,widget=forms.HiddenInput)
    classes_croisement=forms.CharField(label='Classes numériques du croisement (facultatives)',required=False,max_length=3000,widget=forms.Textarea(attrs={'rows':3}),help_text='Même convention : minimum inclus, maximum exclu ; inconnus et hors classes conservés.')
    def __init__(self,*args,acteur,**kw):
        super().__init__(*args,**kw);dims=list(e.disponibles(acteur).items())
        if str((self.data or {}).get('periode','')) not in ('jours_relatifs','date_relative'):
            self.fields['decalage_debut'].widget=forms.HiddenInput()
            self.fields['decalage_fin'].widget=forms.HiddenInput()
        self.fields['mesure'].choices=[*self.fields['mesure'].choices,*e.mesures.CHOIX]
        self.fields['axe'].choices=dims
        for c in ('croisement','filtre1','filtre2'):self.fields[c].choices=[('','Aucun'),*dims]
        import copy
        data=args[0] if args and args[0] else kw.get('initial',{})
        try:niveaux=int(data.get('niveaux') or 2)
        except (ValueError,TypeError):niveaux=2
        for i in range(3,min(niveaux,7)+1):
            self.fields['axe'+str(i)]=forms.ChoiceField(label='Niveau de classement '+str(i),choices=[('','Aucun'),*dims],required=False)
            self.fields['classes'+str(i)]=copy.deepcopy(self.fields['classes'])
            self.fields['classes'+str(i)].label='Classes du niveau '+str(i)+' (facultatives)'
        try:colonnes=int(data.get('nombre_colonnes') or 0)
        except (ValueError,TypeError):colonnes=0
        for i in range(1,min(colonnes,11)+1):self.fields['colonne'+str(i)]=forms.ChoiceField(label='Colonne du relevé détaillé '+str(i),choices=[('','Aucune'),*dims],required=False)
        try:nombre=int(data.get('nombre_mesures') or 1)
        except (ValueError,TypeError):nombre=1
        for i in range(2,min(nombre,9)+1):
            self.fields['mesure'+str(i)]=forms.ChoiceField(label='Mesure supplémentaire '+str(i),choices=[('','Aucune'),*self.fields['mesure'].choices],required=False)
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
            for c in ('classes','classes_croisement',*('classes'+str(i) for i in range(3,8))):e.classes(d.get(c,''))
        except forms.ValidationError as exc:self.add_error('classes',exc)
        return d
