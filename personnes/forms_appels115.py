from django import forms
from . import models as m,appels115 as s,textes_riches as tr
from .champs_saisie import FormulaireMetier,FormulaireModeleMetier


class ListeMots(forms.CharField):
    def __init__(self,*args,**kw):
        kw.update(required=False,widget=forms.Textarea(attrs={'rows':3}),help_text='Un élément par ligne, au plus 30 éléments distincts. Une ligne est une donnée recherchable, pas un commentaire.')
        super().__init__(*args,**kw)
    def prepare_value(self,value):return '\n'.join(value) if isinstance(value,list) else value
    def to_python(self,value):
        if isinstance(value,list):return value
        return [s.strip() for s in super().to_python(value).splitlines() if s.strip()]
    def validate(self,value):
        if len(value)>30 or any(len(s)>160 for s in value) or len({s.casefold() for s in value})!=len(value):raise forms.ValidationError('Au plus 30 éléments distincts de 160 caractères chacun.')


class AppelForm(FormulaireModeleMetier):
    attendu=forms.CharField(widget=forms.HiddenInput)
    beneficiaires=forms.ModelMultipleChoiceField(m.Personne.objects.none(),required=False,label='Personnes explicitement concernées',widget=forms.SelectMultiple(attrs={'size':5}),
        help_text='Vide si elles ne sont pas identifiées. Sélectionnez explicitement plusieurs noms si nécessaire (Contrôle/Commande au clavier). Ne crée aucune personne ni appartenance ; le tiers appelant n’est pas automatiquement bénéficiaire.')
    action=forms.ChoiceField(choices=m.VersionAppel115._meta.get_field('action').choices,label='Nature de la saisie')
    motif=forms.CharField(max_length=240,required=False,label='Motif de suite ou de correction')
    details=tr.ChampTexte(label='Détails de la demande',required=False,max_length=4000)
    demandes_secondaires=ListeMots(label='Autres demandes')
    reponses=ListeMots(label='Réponses apportées')
    class Meta:
        model=m.VersionAppel115
        fields=[*s.CHAMPS,'beneficiaires','action','motif']
        widgets={'heure':forms.TimeInput(format='%H:%M:%S',attrs={'type':'time','step':'1'})}
        help_texts={'heure':'Heure déclarée locale ; laissez vide si inconnue. Ce n’est pas une fin de séjour ni une durée.',
            'telephone':'Numéro déclaré de rappel ; ne déclenche aucun appel.',
            'menage':'Rattachement facultatif et explicite. Ne désigne ni chef de famille ni appelant.',
            'information_complementaire':'Précisez le sens de cette information. L’ancien champ paramétrable 115 n’est pas un prescripteur financier.'}
    def __init__(self,*args,acteur,**kw):
        super().__init__(*args,**kw)
        for nom,modele,droits in [('beneficiaires',m.Personne,['view_personne']),('appelant_personne',m.Personne,['view_personne']),('menage',m.Menage,['view_personne','view_menage']),('appelant_intervenant',m.Intervenant,['view_intervenant','view_ficheintervenant']),('appelant_organisme',m.Partenaire,['view_partenaire','view_fichepartenaire']),('orientation',m.Partenaire,['view_partenaire','view_fichepartenaire'])]:
            self.fields[nom].queryset=modele.objects.all() if acteur.has_perms(['personnes.'+d for d in droits]) else modele.objects.none()
        if acteur.has_perm('personnes.view_propositionsaisie'):
            for nom,champ,label in [('secondaires_proposes','demande_secondaire115','Ajouter des demandes proposées'),('reponses_proposees','reponse115','Ajouter des réponses proposées')]:
                choix=list(m.PropositionSaisie.objects.filter(champ=champ,active=True).values_list('valeur',flat=True))
                if choix:self.fields[nom]=forms.MultipleChoiceField(choices=[(v,v) for v in choix],required=False,widget=forms.CheckboxSelectMultiple,label=label)

    def clean(self):
        d=super().clean()
        for propose,champ in [('secondaires_proposes','demandes_secondaires'),('reponses_proposees','reponses')]:
            if propose in d:
                d[champ]=list(dict.fromkeys([*d.get(champ,[]),*d.pop(propose)]))
                self.instance.__dict__[champ]=d[champ]
        if d.get('action')!='saisie' and not d.get('motif'):self.add_error('motif','Expliquez la suite ou la correction.')
        return d


class ChoixPrise(forms.ModelChoiceField):
    def label_from_instance(self,obj):return 'Prise en charge du '+obj.debut.strftime('%d/%m/%Y')+' — '+str(obj.menage)


class LienForm(FormulaireMetier):
    attendu=forms.CharField(widget=forms.HiddenInput)
    demande=forms.ModelChoiceField(m.DemandeAccueil.objects.none(),required=False,label='Demande d’accueil existante')
    accompagnement=ChoixPrise(m.Accompagnement.objects.none(),required=False,label='Prise en charge existante')
    motif=forms.CharField(max_length=240,label='Motif du lien explicite')
    def __init__(self,*args,acteur,version,**kw):
        super().__init__(*args,**kw)
        from .parcours import droits
        ids=list(version.beneficiaires.values_list('pk',flat=True))
        if acteur.has_perms(droits('demandes')):self.fields['demande'].queryset=m.DemandeAccueil.objects.filter(annule_le__isnull=True,beneficiaires__in=ids).distinct()
        if acteur.has_perms(['personnes.view_personne','personnes.view_menage','personnes.view_accompagnement']):self.fields['accompagnement'].queryset=m.Accompagnement.objects.filter(beneficiaires__in=ids).select_related('menage').distinct()
    def clean(self):
        d=super().clean()
        if bool(d.get('demande'))==bool(d.get('accompagnement')):raise forms.ValidationError('Choisissez une demande ou une prise en charge, pas les deux.')
        return d
