from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .models import Accompagnement, InformationsAccompagnement
from . import informations_suivi as service
from .social import droit
from .vues_hebergement import traiter_hebergement


class InformationsForm(forms.ModelForm):
    attendu = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = InformationsAccompagnement
        fields = [*service.CHAMPS, 'motif']
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
    initial['attendu'] = service.jeton(a, precedente)
    form = InformationsForm(request.POST if request.method == 'POST' else None, initial=initial)
    return traiter_hebergement(request, form, 'Informations pratiques et projet d’accompagnement',
        lambda **d: service.enregistrer(request.user, a, **d), a.menage, accompagnement=a,
        retour=reverse('suivi:accompagnement', args=[a.pk]))
