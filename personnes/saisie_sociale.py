"""Contexte facultatif d'une opération sociale, jamais source implicite du fait.

Le scope est ouvert explicitement autour du service métier par les vues. Il est
réinitialisé même en cas d'erreur ; seuls les journaux optant pour TraceSaisie le
conservent lors de leur création, dans la transaction métier existante.
"""
from contextvars import ContextVar
from django import forms

_contexte = ContextVar('contexte_saisie_sociale', default='')


def contexte_courant():
    return _contexte.get()


def preparer(request, form):
    if request.headers.get('X-Condition-Form') != '1' and request.GET.get('saisie_sociale') != '1':
        return
    route = getattr(request.resolver_match, 'url_name', '')
    routes = {'social_nouveau', 'social_corriger', 'famille_nouvelle', 'famille_corriger',
              'coordonnees_nouvelles', 'coordonnees_corriger', 'complements_identite_nouveaux',
              'complements_identite_corriger', 'administration_nouvelle', 'administration_corriger',
              'fait_a_nouveau', 'fait_a_absence', 'fait_a_changer', 'fait_a_corriger',
              'relation_nouvelle', 'relation_changer', 'relation_corriger', 'parcours_nouveau',
              'parcours_changer', 'parcours_corriger', 'condition_retirer', 'corriger_identite', 'informations'}
    if route not in routes:
        return
    for nom in ('source', 'motif'):
        if nom in form.fields:
            form.fields[nom].required = False
            form.fields[nom].label = ('Source particulière (facultatif)' if nom == 'source' else 'Précision sur cette opération (facultatif)')
    form.fields['contexte_saisie'] = forms.CharField(label='Contexte de saisie (facultatif)', max_length=240, required=False,
        widget=forms.HiddenInput if request.headers.get('X-Condition-Form') == '1' else forms.TextInput)


def executer(form, action):
    contexte = form.cleaned_data.pop('contexte_saisie', '').strip()
    token = _contexte.set(contexte)
    try:
        return action(**form.cleaned_data)
    finally:
        _contexte.reset(token)
