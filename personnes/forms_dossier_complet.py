from django import forms
from . import models as m,dossier_complet as service
from .champs_saisie import FormulaireModeleMetier
from .forms_hebergement import date_champ


class FaitForm(FormulaireModeleMetier):
    def clean_devise(self):return self.cleaned_data["devise"].upper()
    debut=date_champ('Déclaration applicable depuis le (inclus)')
    fin=date_champ('Fin effective exclue (si déjà terminée)',False)
    motif=forms.CharField(label='Motif de correction, de fin ou d’ajout antérieur',max_length=240,required=False)
    attendu=forms.CharField(widget=forms.HiddenInput)

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['source'].help_text='Entretien ou document consulté, sans pièce à téléverser. Date de saisie et date du renseignement restent distinctes.'
        self.fields['etat'].help_text='Une absence déclarée ou une information non connue porte sur toute cette rubrique, pas sur un seul poste. Les détails ne s’y appliquent pas.'
        etat=self.data.get(self.add_prefix('etat')) if self.is_bound else self.initial.get('etat','detail')
        if etat in ('aucun','inconnu'):
            for c in self.Meta.fields:
                if c not in ('debut','fin','etat','source'):
                    self.initial[c]=self._meta.model._meta.get_field(c).get_default()
                    # Nullable fields have None; blank text has ''. Choice and
                    # currency defaults remain explicit, never hidden amounts.
                    self.fields[c].disabled=True
                    self.fields[c].widget=forms.HiddenInput()
        if 'organisme' in self.fields:self.fields['organisme'].help_text='Organisation connue du répertoire, sans copie de coordonnées.'
        if 'interlocuteur' in self.fields:self.fields['interlocuteur'].help_text='Contact professionnel du répertoire, distinct du représentant et de l’auteur de saisie.'
        if 'representant_personne' in self.fields:self.fields['representant_personne'].help_text='Personne connue exerçant le rôle déclaré. Aucun lien familial ou rôle du ménage n’est déduit.'
        if 'devise' in self.fields:self.fields['devise'].help_text='Trois lettres majuscules ; aucune conversion n’est effectuée.'
        if 'montant' in self.fields:self.fields['montant'].help_text='Montant déclaré, avec virgule ou point. Vide : inconnu ; 0 : zéro explicitement déclaré.'
        if 'echeance_prevue' in self.fields:self.fields['echeance_prevue'].help_text='Date annoncée, éventuellement future ; ne termine pas la déclaration et ne crée pas de tâche.'


class RessourceForm(FaitForm):
    class Meta:
        model=m.RessourcePersonnelle
        fields=['debut','fin',*service.RUBRIQUES['ressources'].champs,'source']


class DetteForm(FaitForm):
    class Meta:
        model=m.DettePersonnelle
        fields=['debut','fin',*service.RUBRIQUES['dettes'].champs,'source']
        help_texts={'nature':'Un total de dette déclaré est distinct des créanciers détaillés ; les deux ne sont jamais additionnés.',
            'mensualite':'Remboursement périodique déclaré, distinct du solde de dette.'}


class PieceForm(FaitForm):
    class Meta:
        model=m.PieceAdministrative
        fields=['debut','fin',*service.RUBRIQUES['pieces'].champs,'source']


class CouvertureForm(FaitForm):
    class Meta:
        model=m.CouvertureSociale
        fields=['debut','fin',*service.RUBRIQUES['couvertures'].champs,'source']


class ProtectionForm(FaitForm):
    class Meta:
        model=m.ProtectionJuridique
        fields=['debut','fin',*service.RUBRIQUES['protections'].champs,'source']
        labels={'organisme':'Organisme représentant déclaré'}
        help_texts={'mesure':'Libellé connu de la mesure, sans attribution automatique de pouvoirs.',
            'domaine':'Portée déclarée ; le libellé de la mesure seul ne détermine pas les responsabilités.',
            'precision_portee':'Précisions connues sur les actes ou limites de la mesure, sans données inventées.'}


class BesoinAccueilForm(FaitForm):
    class Meta:
        model=m.BesoinAccueil
        fields=['debut','fin',*service.RUBRIQUES['besoins'].champs,'source']
        help_texts={'libelle':'Renseignement déclaré utile à l’accueil. Aucun diagnostic ou besoin n’est déduit d’une couverture sociale, de la grossesse ou de l’âge.', 'adaptation':'Demande pratique déclarée, distincte d’une prestation accordée ou réalisée.'}


class AntecedentForm(FaitForm):
    class Meta:
        model=m.AntecedentInstitutionnel
        fields=['debut','fin',*service.RUBRIQUES['antecedents'].champs,'source']
        help_texts={'debut':'Date à laquelle ce renseignement est déclaré applicable, distincte de la date d’entrée dans l’institution.', 'periode_declaree':'Conservez une durée ou époque déclarée sans inventer de date au 1er janvier.'}


class TerritoireForm(FaitForm):
    class Meta:
        model=m.AncrageTerritorial
        fields=['debut','fin',*service.RUBRIQUES['territoires'].champs,'source']
        help_texts={'debut':'Date à laquelle ces renseignements sont déclarés applicables, distincte de l’arrivée déclarée sur le territoire.', 'anciennete_declaree':'Conservez la durée ou catégorie déclarée sans calculer une date d’arrivée fictive.', 'territoire':'Territoire explicitement nommé, sans déduction depuis une adresse ou un lieu d’hébergement.'}


class EvolutionDeclareeForm(FaitForm):
    class Meta:
        model=m.EvolutionPersonnelleDeclaree
        fields=['debut','fin',*service.RUBRIQUES['evolutions'].champs,'source']
        help_texts={'libelle':'Qualification déclarée à rechercher ou classer ; ne change ni les situations logement/emploi/ressources ni un objectif automatiquement.'}


FORMULAIRES={'evolutions':EvolutionDeclareeForm,'territoires':TerritoireForm,'antecedents':AntecedentForm,'besoins':BesoinAccueilForm,'ressources':RessourceForm,'dettes':DetteForm,'pieces':PieceForm,'couvertures':CouvertureForm,'protections':ProtectionForm}


class AdministrationForm(FormulaireModeleMetier):
    debut=date_champ('Depuis quelle date ces renseignements sont-ils vrais ?')
    motif=forms.CharField(label='Motif de correction ou d’ajout antérieur',max_length=240,required=False)
    attendu=forms.CharField(widget=forms.HiddenInput)
    class Meta:
        model=m.SituationAdministrative
        fields=['debut',*service.ADMIN_CHAMPS,'source']
        help_texts={'numero_ss':'Identifiant textuel déclaré : conservez les zéros et lettres ; aucune vérification ou déduction automatique.',
            'numero_caf':'Identifiant textuel déclaré, distinct du numéro de sécurité sociale.',
            'qualification':'Niveau ou qualification déclaré, sans déduction de la situation d’emploi.',
            'droit_sejour':'Situation déclarée ; la nationalité ne la détermine pas automatiquement.',
            'sans_emploi_duree_declaree':'Par exemple six mois déclarés à cette date. Conservez ce renseignement sans inventer de date de début.',
            'sans_domicile_duree_declaree':'Durée ou catégorie déclarée, distincte d’une date de début exacte ou estimée.',
            'sans_emploi_depuis':'Date connue ou estimée explicitement ; vide si inconnue, sans date fictive au 1er janvier.',
            'sans_domicile_depuis':'Déclaration de perte de domicile, distincte du séjour effectif.'}
