from . import textes_riches as tr, parcours_logement
from django import forms
from .champs_saisie import FormulaireModeleMetier
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .models import Accompagnement, InformationsAccompagnement
from . import informations_suivi as service
from .social import droit
from .vues_hebergement import traiter_hebergement


class SaisieSuggeree(forms.TextInput):
    template_name = 'dossiers/widgets/saisie_suggeree.html'

    def __init__(self, suggestions, champ):
        super().__init__(attrs={'list': 'suggestions-' + champ})
        self.suggestions = suggestions

    def get_context(self, name, value, attrs):
        contexte = super().get_context(name, value, attrs)
        contexte['suggestions'] = self.suggestions
        return contexte


class InformationsForm(FormulaireModeleMetier):
    objectifs_courts = tr.ChampTexte(label='Objectifs à court terme', max_length=1000, required=False)
    objectifs_longs = tr.ChampTexte(label='Objectifs à plus long terme', max_length=1000, required=False)
    motifs_secondaires = forms.MultipleChoiceField(
        label='Motifs secondaires à l’entrée', choices=parcours_logement.MOTIFS_SECONDAIRES,
        required=False, widget=forms.CheckboxSelectMultiple,
    )
    attendu = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = InformationsAccompagnement
        fields = [*service.CHAMPS, *parcours_logement.CHAMPS_CODES, 'motifs_secondaires', 'motif']
        widgets = {champ: forms.Textarea(attrs={'rows': 3}) for champ in ('objectifs_courts', 'objectifs_longs', 'animaux')}
        help_texts = {'referent': 'Nom ou fonction du professionnel, y compris extérieur. Ce n’est pas l’auteur de saisie.',
            'provenance': 'D’où vient la personne ou le ménage à l’entrée ; à distinguer du motif d’admission.',
            'orientation_sortie': 'Relais ou dispositif envisagé ou organisé ; à distinguer de la destination effective.',
            'animaux': 'Facultatif. Une case vide signifie non renseigné, pas absence d’animal.'}


@require_http_methods(['GET', 'POST'])
@login_required
def modifier(request, pk):
    droit(request.user, 'view_informationsaccompagnement')
    droit(request.user, 'add_informationsaccompagnement')
    a = get_object_or_404(Accompagnement, pk=pk)
    precedente = a.informations.first()
    initial = {champ: getattr(precedente, champ) if precedente else '' for champ in service.CHAMPS}
    for champ in ('objectifs_courts', 'objectifs_longs'):
        initial[champ] = tr.lire_objet(precedente, champ) if precedente else ''
    if precedente:
        for champ in (*parcours_logement.CHAMPS_CODES, 'motifs_secondaires'):
            initial[champ] = getattr(precedente, champ)
    initial['attendu'] = service.jeton(a, precedente)
    form = InformationsForm(request.POST if request.method == 'POST' else None, initial=initial)
    from acteurs.listes_saisie import choix
    from acteurs.portees import existante
    origine = existante(a)
    if origine:
        service_actuel = origine.service
        for champ in ('motif_entree', 'motif_sortie', 'destination_sortie', 'qualification_sortie'):
            propositions = choix(champ, etablissement=service_actuel.etablissement, service=service_actuel)
            if propositions:
                form.fields[champ].widget = SaisieSuggeree(propositions, champ)
    return traiter_hebergement(request, form, 'Informations pratiques et projet d’accompagnement',
        lambda **d: service.enregistrer(request.user, a, **d), a.menage, accompagnement=a,
        retour=reverse('suivi:accompagnement', args=[a.pk]))
