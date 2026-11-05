from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from personnes.champs_saisie import FormulaireMetier
from . import services as s
from .listes_saisie import LISTES, choix
from .models import Etablissement, Service
from .views import formulaire


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def modifier(request, service_pk=None, etablissement_pk=None):
    s.exiger_gestion(request.user)
    service = get_object_or_404(Service.objects.select_related('etablissement'), pk=service_pk) if service_pk else None
    etablissement = service.etablissement if service else get_object_or_404(Etablissement, pk=etablissement_pk)
    cible = service or etablissement
    form = FormulaireMetier(request.POST if request.method == 'POST' else None)
    form.fields['attendu'] = forms.CharField(widget=forms.HiddenInput, initial=s.jeton(cible))
    lignes = []
    for code, (titre, defaut) in LISTES.items():
        source = 'la liste de l’établissement' if service else 'la liste Pas à Pas'
        form.fields[code + '_commun'] = forms.BooleanField(
            label=f'Reprendre {source}', required=False, initial=code not in cible.listes_saisie,
        )
        form.fields[code] = forms.CharField(
            label='Choix personnalisés', required=False, max_length=8000, widget=forms.Textarea(attrs={'rows': 4}),
            initial='\n'.join(choix(code, etablissement=etablissement, service=service)),
            help_text='Un choix par ligne, dans l’ordre voulu.',
        )

        commun = choix(code, etablissement=etablissement) if service else defaut
        lignes.append((titre, form[code + '_commun'], form[code], commun))

    def sauver(attendu, **donnees):
        s.reserver(cible, attendu)
        listes = {}
        for code in LISTES:
            if donnees[code + '_commun']:
                continue
            valeurs = [ligne.strip() for ligne in donnees[code].splitlines() if ligne.strip()]
            if len(valeurs) > 50 or any(len(v) > 160 for v in valeurs):
                raise forms.ValidationError('Utilisez au plus 50 choix de 160 caractères par liste.')
            if len({v.casefold() for v in valeurs}) != len(valeurs):
                raise forms.ValidationError('Chaque choix doit être unique dans sa liste.')
            listes[code] = valeurs
        avant = cible.listes_saisie
        cible.listes_saisie = listes
        cible.save(update_fields=['listes_saisie'])
        s.journal(request.user, service, 'listes_saisie', avant, listes, etablissement=None if service else etablissement)

    nom = 'service' if service else 'etablissement'
    return formulaire(request, form, 'Choix proposés à la saisie', sauver,
                      reverse(f'acteurs:{nom}', args=[cible.pk]) + '#listes-saisie',
                      service=service, etablissement=None if service else etablissement,
                      attention_listes=not service, lignes_listes=lignes)
