from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import AccordHebergement, LieuHebergement
from . import hebergement as h, hebergement_collectif as service
from .vues_hebergement import traiter_hebergement
from .forms_hebergement import date_champ


class SelectionSejours(forms.ModelMultipleChoiceField):
    def label_from_instance(self, sejour):
        return f"{', '.join(str(p) for p in sejour.beneficiaires.all())} — séjour du {sejour.debut:%d/%m/%Y}"


class ActionForm(forms.Form):
    sejours = SelectionSejours(queryset=None, widget=forms.CheckboxSelectMultiple,
        help_text='Seuls les séjours cochés seront modifiés. Pour un ancien séjour collectif, tous ses bénéficiaires sont concernés.')
    action = forms.ChoiceField(label='Action')
    date = date_champ('Date d’effet commune')
    lieu = forms.ModelChoiceField(LieuHebergement.objects.none(), label='Lieu commun', required=False,
        help_text='Uniquement pour affecter ou changer de lieu.')
    attendu = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, accord, acteur, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sejours'].queryset = service.sejours_ouverts(accord)
        self.fields['action'].choices = [(code, libelle) for code, (libelle, droits) in service.ACTIONS.items()
            if acteur.has_perms(['personnes.' + droit for droit in droits])]
        if acteur.has_perm('personnes.view_lieuhebergement'):
            self.fields['lieu'].queryset = LieuHebergement.objects.all()


@require_http_methods(['GET', 'POST'])
@login_required
def selection(request, pk):
    h.droit(request.user, 'view_sejour')
    accord = get_object_or_404(AccordHebergement.objects.select_related('accompagnement__menage'), pk=pk)
    sejours = list(service.sejours_ouverts(accord))
    form = ActionForm(request.POST if request.method == 'POST' else None, accord=accord, acteur=request.user,
        initial={'date': timezone.localdate(), 'attendu': service.jeton(accord, sejours)})
    if not form.fields["action"].choices:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return traiter_hebergement(request, form, 'Agir sur les séjours sélectionnés',
        lambda **d: service.appliquer(request.user, accord, **d), accord.accompagnement.menage,
        retour=reverse('suivi:accord_hebergement', args=[accord.pk]))
