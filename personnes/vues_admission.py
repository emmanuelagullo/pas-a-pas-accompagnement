from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.contrib import messages
from .models import Accompagnement, LieuHebergement
from .forms_hebergement import AccordForm, date_champ
from . import admission, hebergement as h


class AdmissionGuideeForm(AccordForm):
    admission = date_champ('Date d’admission effective')
    lieu = forms.ModelChoiceField(LieuHebergement.objects.none(), required=False,
        label='Premier lieu — facultatif', help_text='Une affectation débute à la date d’admission pour chaque personne sélectionnée.')
    attendu = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, acteur, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['debut'].label = 'Début de l’accord inclus'
        self.fields['fin'].label = 'Fin de l’accord exclue — facultative'
        if acteur.has_perms(['personnes.add_affectation', 'personnes.view_affectation', 'personnes.view_lieuhebergement']):
            self.fields['lieu'].queryset = LieuHebergement.objects.all()
        else:
            del self.fields['lieu']


@require_http_methods(['GET', 'POST'])
@login_required
def accueillir(request, pk):
    h.droit(request.user, 'add_accordhebergement')
    h.exiger(request.user, 'add_sejour')
    a = get_object_or_404(Accompagnement.objects.select_related('menage'), pk=pk)
    jour = timezone.localdate()
    form = AdmissionGuideeForm(request.POST if request.method == 'POST' else None,
        acteur=request.user, beneficiaires=a.beneficiaires.all(), initial={'debut': max(a.debut, jour),
            'admission': max(a.debut, jour), 'beneficiaires': list(a.beneficiaires.values_list('pk', flat=True)),
            'attendu': admission.jeton(a)})
    statut = 200
    if request.method == 'POST' and form.is_valid():
        try:
            accord = admission.accueillir(request.user, a, **form.cleaned_data)
        except ValidationError as erreur:
            form.add_error(None, 'Aucun accord, séjour ou lieu d’affectation n’a été enregistré. ' + ' '.join(erreur.messages))
            statut = 409
        except OperationalError:
            form.add_error(None, 'Écriture non confirmée. Rechargez l’accompagnement avant de réessayer.')
            statut = 409
        else:
            messages.success(request, 'Accord et admissions enregistrés ; aucun repas n’a été créé.')
            return redirect('suivi:accord_hebergement', pk=accord.pk)
    return render(request, 'hebergement/admission_guidee.html', {'accompagnement': a, 'form': form}, status=statut)
