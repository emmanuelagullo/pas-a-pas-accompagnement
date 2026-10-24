"""Décisions BD3 : formulaires français et retour au dossier validé."""
from django import forms
from .champs_saisie import FormulaireMetier
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.http import Http404
from django.views.decorators.http import require_http_methods
from . import accords
from .forms_hebergement import date_champ
from .vues_hebergement import traiter_hebergement


class DecisionForm(FormulaireMetier):
    motif = forms.CharField(label='Motif de la décision', max_length=240, widget=forms.Textarea(attrs={'rows': 3}))
    attendu = forms.CharField(widget=forms.HiddenInput)
    confirmer = forms.BooleanField(label='Je confirme cette décision pour tous les bénéficiaires de cet accord.')


class ProlongationForm(DecisionForm):
    fin = date_champ('Nouvelle fin exclue — facultative', False)
    field_order = ['fin', 'motif', 'confirmer', 'attendu']


@require_http_methods(['GET', 'POST'])
@login_required
def decider(request, nature, pk, action):
    modele = accords.MODELES.get(nature)
    if modele is None or action not in ('prolonger', 'annuler'):
        raise Http404
    accord = get_object_or_404(modele.objects.select_related('accompagnement__menage').prefetch_related('beneficiaires'), pk=pk)
    accords.droits(request.user, accord, action)
    form = (ProlongationForm if action == 'prolonger' else DecisionForm)(
        request.POST if request.method == 'POST' else None, initial={'attendu': accords.jeton(accord)})
    # Explain the meaning of the operation in the form, not only in a tooltip.
    if action == 'prolonger':
        texte = ('Cette décision étend la même autorisation sans interruption depuis son ancienne fin. '
                 'Elle ne crée ni admission ni distribution et ne rouvre pas l’accompagnement. '
                 'Pour un accueil séparé, créez un nouvel accord. Une fin vide laisse l’accord ouvert.')
    else:
        texte = ('Annuler une saisie erronée conserve l’accord, ses dates et son historique. '
                 'Aucune annulation n’est possible si une distribution, même annulée, ou un séjour, même terminé, existe. '
                 'Une sortie réelle ne se traite pas par cette annulation.')
    form.fields['confirmer'].help_text = texte
    titre = ('Prolonger l’accord' if action == 'prolonger' else 'Annuler un accord saisi par erreur')
    titre += ' — ' + ('repas' if nature == 'repas' else 'hébergement')
    def appliquer(**donnees):
        donnees.pop('confirmer')
        return (accords.prolonger if action == 'prolonger' else accords.annuler)(request.user, accord, **donnees)
    form.fields['motif'].help_text = ('Accord du ' + accord.debut.strftime('%d/%m/%Y') +
        ' ; fin exclue : ' + (accord.fin.strftime('%d/%m/%Y') if accord.fin else 'non prévue') +
        '. Bénéficiaires : ' + ', '.join(str(p) for p in accord.beneficiaires.all()) + '.')
    return traiter_hebergement(request, form, titre, appliquer, accord.accompagnement.menage,
        accompagnement=accord.accompagnement,
        retour=reverse('suivi:accord_repas' if nature == 'repas' else 'suivi:accord_hebergement', args=[accord.pk]))
