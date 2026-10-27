"""Contrôles HTML métier : présentation typée, validation Django inchangée.

Aucun autoremplissage depuis le profil du navigateur : ces formulaires décrivent
une tierce personne. Les valeurs, inconnues et codes internationaux sont conservés.
"""
from django import forms
from django.db.models import Q
from django.utils.html import format_html, format_html_join


class TelephoneInput(forms.TextInput):
    input_type = 'tel'


class PropositionInput(forms.TextInput):
    def __init__(self, *args, propositions=(), **kwargs):
        self.propositions = propositions
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        attrs = dict(attrs or {})
        identifiant = attrs.get('id', 'id_' + name) + '_propositions'
        attrs['list'] = identifiant
        return format_html('{}<datalist id="{}">{}</datalist>',
            super().render(name, value, attrs, renderer), identifiant,
            format_html_join('', '<option value="{}"></option>', ((v,) for v in self.propositions)))


def adapter(form):
    """Idempotent, sans requête, y compris pour des champs ajoutés dynamiquement."""
    for nom, champ in form.fields.items():
        w = champ.widget
        if w.is_hidden or isinstance(w, (forms.Select, forms.CheckboxInput, forms.CheckboxSelectMultiple,
                forms.RadioSelect, forms.FileInput, forms.MultiWidget)):
            continue
        w.attrs.setdefault('autocomplete', 'off')
        if isinstance(champ, forms.DateField) and not isinstance(champ, forms.DateTimeField):
            if type(w) in (forms.TextInput, forms.DateInput):
                champ.widget = forms.DateInput(format='%Y-%m-%d', attrs={**w.attrs, 'type':'date'})
        elif isinstance(champ, forms.EmailField) or nom in ('courriel', 'email'):
            if isinstance(w, forms.TextInput):
                champ.widget = forms.EmailInput(attrs={**w.attrs, 'inputmode':'email', 'autocapitalize':'none', 'spellcheck':'false'})
        elif nom in ('telephone', 'fax', 'telephone_professionnel') and isinstance(w, forms.TextInput):
            champ.widget = TelephoneInput(attrs={**w.attrs, 'inputmode':'tel', 'spellcheck':'false'})
        elif isinstance(champ, forms.URLField):
            w.attrs.update(inputmode="url", autocapitalize="none", spellcheck="false")
        elif nom == 'rue' and type(w) is forms.TextInput:
            champ.widget = forms.Textarea(attrs={**w.attrs, 'rows':2})
        elif isinstance(champ, forms.DecimalField):
            champ.localize = True
            champ.widget = forms.TextInput(attrs={**w.attrs, 'inputmode':'decimal'})
        elif isinstance(champ, forms.IntegerField):
            w.attrs.setdefault('inputmode', 'numeric')
        elif nom in ('q', 'recherche') and type(w) is forms.TextInput:
            w.input_type = 'search'
        elif nom in ('motif', 'source') and type(w) is forms.TextInput:
            champ.widget = forms.Textarea(attrs={**w.attrs, 'rows':2})
        elif isinstance(w, forms.Textarea):
            w.attrs.setdefault('rows', 4)
        elif nom in ('code_postal', 'numero_ss', 'numero_caf', 'numero_allocataire', 'identifiant', 'reference', 'reference_decision'):
            w.attrs.setdefault('spellcheck', 'false')
    return form


class FormulaireMetier(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        adapter(self)
        from .periodes_saisie import preparer
        preparer(self)
        from acteurs.saisie import preparer as proposer_responsable
        proposer_responsable(self)

    def clean(self):
        from .periodes_saisie import nettoyer
        from acteurs.saisie import nettoyer as retirer_responsable
        return retirer_responsable(nettoyer(self, super().clean()))


class FormulaireModeleMetier(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        adapter(self)
        from .periodes_saisie import preparer
        preparer(self)
        from acteurs.saisie import preparer as proposer_responsable
        proposer_responsable(self)

    def clean(self):
        from .periodes_saisie import nettoyer
        from acteurs.saisie import nettoyer as retirer_responsable
        return retirer_responsable(nettoyer(self, super().clean()))


def valeurs_proposees(request, faits, champs, correction=None):
    """Même personne/identité, à la date choisie ; aucune copie entre dossiers."""
    from django.utils import timezone
    jour=timezone.localdate()
    if request.GET.get('date'):
        try:jour=forms.DateField().clean(request.GET['date'])
        except forms.ValidationError:jour=None  # Ne proposer aucune donnée à une date invalide.
    fait=correction or (faits.filter(debut__lte=jour).filter(
        Q(fin__isnull=True) | Q(fin__gt=jour)).first()
        if jour and request.GET.get('vierge')!='1' else None)
    initial={c:getattr(fait,c) for c in champs} if fait else {}
    initial.update(debut=correction.debut if correction else jour or request.GET.get('date',''), source=correction.source if correction else '')
    params=request.GET.copy();params['vierge']='1'
    return initial, {'proposition_depuis':fait.debut if fait and not correction else None,
        'url_formulaire_vide':'?'+params.urlencode() if not correction and fait else ''}
