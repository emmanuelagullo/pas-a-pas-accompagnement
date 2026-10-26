"""Confirmation serveur de la période corrigée dans l'espace de saisie commun."""
from datetime import date
from django import forms
from django.core import signing
from django.db.models import Q
from django.shortcuts import get_object_or_404
from . import models as m, dossier_complet, parcours, retraits_chronologiques as retraits

SEL = 'condition-correction-portee-v1'


def preparer(request, form, objet):
    if request.headers.get('X-Condition-Form') != '1' and request.GET.get('portee') != '1':
        return None
    match = request.resolver_match
    if not match:
        return None
    route, kw = match.url_name, match.kwargs
    model = None
    faits = None
    code = {'famille_corriger': 'famille', 'coordonnees_corriger': 'coordonnees',
            'complements_identite_corriger': 'complements', 'administration_corriger': 'administration'}.get(route)
    if route == 'social_corriger':
        code = 'ressources-globales' if kw['dimension'] == 'ressources' else kw['dimension']
    if code:
        serie = retraits.configuration(code)
        model = serie.modele
        faits = retraits.selection(serie, objet)
    elif route == 'fait_a_corriger':
        model = dossier_complet.RUBRIQUES[kw['code']].modele
        faits = model.objects.filter(personne=objet, annule_le__isnull=True)
    elif route == 'relation_corriger':
        model = m.RelationPersonnelle
        faits = model.objects.filter(Q(personne_a=objet) | Q(personne_b=objet), annule_le__isnull=True)
    elif route == 'parcours_corriger':
        model = parcours.RUBRIQUES[kw['code']].version
        faits = model.objects.filter(element_id=kw['pk'])
    if faits is None:
        return None
    fait = get_object_or_404(faits, pk=kw.get('fait_pk') or kw.get('version_pk'))
    debut, fin = fait.debut, fait.fin
    # Une correction de date peut aussi déplacer la borne de la période voisine.
    # Montrer l'union des périodes avant/après, puis demander une confirmation
    # renouvelée si l'utilisateur modifie cette portée.
    for nom in ('debut', 'fin'):
        champ = form.fields.get(nom)
        if not champ or champ.disabled:
            continue
        brut = form.data.get(form.add_prefix(nom)) if form.is_bound else form.initial.get(nom)
        try:
            valeur = forms.DateField(required=False).clean(brut)
        except forms.ValidationError:
            continue
        if nom == 'debut' and valeur:
            debut = min(debut, valeur)
        elif nom == 'fin':
            fin = max(fin, valeur) if fin and valeur else None
    payload = [model._meta.label_lower, str(fait.pk), str(objet.pk), debut.isoformat(), fin.isoformat() if fin else None]
    token = signing.dumps(payload, salt=SEL)
    form.fields['condition_preuve'] = forms.CharField(widget=forms.HiddenInput, initial=token)
    form.fields['condition_confirmation'] = forms.BooleanField(label='Je confirme la correction sur la période indiquée et ses répercussions sur les vues partagées')
    if form.is_bound and not form.data.get(form.add_prefix('condition_preuve')):
        form.data = form.data.copy()
        form.data[form.add_prefix('condition_preuve')] = token
    personnes = list(fait.element.beneficiaires.all()) if route == 'parcours_corriger' else [objet]
    if route == 'relation_corriger':
        personnes = [fait.personne_a, fait.personne_b]
    entrees = None
    from . import dossier
    if request.user.has_perms(dossier.DROITS):
        q = m.Accompagnement.objects.filter(beneficiaires__in=personnes).filter(Q(fin__isnull=True) | Q(fin__gt=debut))
        if route == 'parcours_corriger' and isinstance(objet, m.Menage):
            q = q.filter(menage=objet)
        if fin:
            q = q.filter(debut__lt=fin)
        q = q.select_related('menage').distinct().order_by('debut', 'pk')
        entrees = {'nombre': q.count(), 'entrees': list(q[:10])}
    selection = request.GET.get('date')
    dates_changees = debut != fait.debut or fin != fait.fin
    autres = False
    if entrees and request.GET.get('contexte_prise'):
        try:
            pk_prise = forms.UUIDField().clean(request.GET['contexte_prise'])
            autres = q.exclude(pk=pk_prise).exists()
        except forms.ValidationError:
            autres = True
    if selection == fait.debut.isoformat() and not dates_changees and not autres:
        form.fields['condition_confirmation'] = forms.BooleanField(required=False, widget=forms.HiddenInput, initial=True)
    return {'payload': payload, 'token': token, 'debut': debut, 'fin': fin,
            'entrees': entrees, 'groupe': route not in ('social_corriger', 'relation_corriger')}


def verifier(form, portee):
    """Retirer les champs d'interface avant d'appeler le service métier typé."""
    preuve = form.cleaned_data.pop('condition_preuve')
    form.cleaned_data.pop('condition_confirmation')
    try:
        confirme = signing.loads(preuve, salt=SEL, max_age=86400)
    except (signing.BadSignature, TypeError):
        confirme = None
    if confirme == portee['payload']:
        return True
    form.add_error(None, 'La période concernée a changé. Vérifiez la nouvelle portée, puis confirmez de nouveau.')
    form.data = form.data.copy()
    form.data[form.add_prefix('condition_preuve')] = portee['token']
    form.data[form.add_prefix('condition_confirmation')] = ''
    return False
