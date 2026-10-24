from django import forms
from . import models as m, parcours, textes_riches as tr
from .champs_saisie import FormulaireModeleMetier, FormulaireMetier
from .forms_hebergement import date_champ


class VersionForm(FormulaireModeleMetier):
    debut = date_champ('Date d’effet réelle')
    motif = forms.CharField(label='Motif de correction ou d’insertion antérieure',max_length=240,required=False)
    attendu = forms.CharField(widget=forms.HiddenInput)

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for nom,champ in self.fields.items():
            if isinstance(champ,forms.ModelChoiceField):
                champ.empty_label='Non renseigné'
                champ.label_from_instance=lambda x:str(x)
        self.fields['source'].help_text='Entretien, courrier ou échange ayant établi cette information. La date de saisie reste distincte.'
        self.fields['debut'].help_text='Une décision ou un résultat déjà intervenu. Les dates annoncées peuvent être futures.'


class DemandeForm(VersionForm):
    class Meta:
        model=m.VersionDemande
        fields=['debut',*parcours.RUBRIQUES['demandes'].champs,'source']
        help_texts={'groupe_demande':'Déclaration personne seule, couple, famille, amis… Distincte du nombre de bénéficiaires et de la composition du ménage ; aucune parenté déduite.',
            'dernier_hebergement_duree':'Durée ou catégorie connue ; aucune date de début précise n’est inventée.',
            'dernier_hebergement_lieu':'Lieu de la nuit précédant l’accueil déclaré ; à confirmer à l’admission, distinct du service orienteur.',
            'demandeur':'Qui exprime la demande ; ni l’auteur de saisie ni automatiquement le prescripteur.',
            'prescripteur':'Professionnel prescripteur, distinct de la personne ayant saisi la demande.',
            'accueil_prevu':'Prévision seulement : ne crée ni prise en charge, ni séjour, ni arrivée.'}


class OrientationForm(VersionForm):
    class Meta:
        model=m.VersionOrientation
        fields=['debut',*parcours.RUBRIQUES['orientations'].champs,'source']
        widgets={'resultat':forms.Textarea(attrs={'rows':2})}
        help_texts={'etat':'Une orientation réalisée ne clôture pas automatiquement une prise en charge.',
            'destination':'Libellé connu ; l’organisme du répertoire complète cette destination sans déduction automatique.'}


class ObjectifForm(VersionForm):
    texte=tr.ChampTexte(label='Démarche et bilan de progression',max_length=4000,required=False)
    class Meta:
        model=m.VersionObjectif
        fields=['debut',*parcours.RUBRIQUES['objectifs'].champs,'source']
        help_texts={'echeance':'Date visée ; son dépassement ne marque pas l’objectif comme atteint.',
            'horizon':'Les récits court/long terme déjà présents restent conservés ; aucun découpage automatique.'}


class SuiviForm(VersionForm):
    class Meta:
        model=m.VersionRepereDossier
        fields=['debut',*parcours.RUBRIQUES['suivi'].champs,'source']
        help_texts={'etat':'Repère de suivi uniquement : aucune clôture, aucun blocage du dossier ou de ses prestations.'}


FORMULAIRES={'demandes':DemandeForm,'orientations':OrientationForm,'objectifs':ObjectifForm,'suivi':SuiviForm}


class LiaisonForm(FormulaireMetier):
    accompagnement=forms.ModelChoiceField(m.Accompagnement.objects.none(),label='Prise en charge à associer')
    attendu=forms.CharField(widget=forms.HiddenInput)
    motif=forms.CharField(label='Source et motif de l’association ou de sa correction',max_length=240)
