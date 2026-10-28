"""Frise facultative, lecture et navigation uniquement."""
from datetime import timedelta
from urllib.parse import urlencode
from django.contrib.auth.decorators import login_required, permission_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from django.core.paginator import Paginator
from . import dossier, chronologie as c, models as m
from .vues_dossiers import parametres, suivi_uuid


@never_cache
@require_safe
@login_required
@permission_required(dossier.DROITS, raise_exception=True)
def detail(request, nature, pk):
    if nature not in ('personne', 'menage'):
        raise Http404
    objet = get_object_or_404(m.Personne if nature == 'personne' else m.Menage, pk=pk)
    params = {**parametres(request), **dossier.valeurs_vue(request, nature, pk)}
    for cle in c.CLES:
        if cle in request.GET:
            params[cle] = request.GET[cle][:80]
    prise = None
    if params.get('chrono_prise'):
        if not suivi_uuid(params['chrono_prise']):
            raise Http404
        prise = get_object_or_404(objet.accompagnements, pk=params['chrono_prise'])
    jour = timezone.localdate()
    valeurs = {**params, 'chrono_debut': params.get('chrono_debut') or (jour - timedelta(days=365)).isoformat(),
               'chrono_fin': params.get('chrono_fin') or (jour + timedelta(days=91)).isoformat()}
    if not prise and not valeurs.get('chrono_type') and 'chrono_type' not in request.GET and not request.GET.get('contexte_dossier'):
        valeurs['chrono_type'] = 'prise'
    form = c.Filtres(valeurs)
    lignes = []
    debut = fin = None
    if form.is_valid():
        params.update({k: v.isoformat() if hasattr(v, 'isoformat') else v for k, v in form.cleaned_data.items()})
        debut, fin = form.cleaned_data['chrono_debut'], form.cleaned_data['chrono_fin']
        lignes = c.construire(request.user, objet, nature, params, debut, fin)
    page = Paginator(lignes, 60).get_page(params.get('chrono_page'))
    params['chrono_page'] = str(page.number)
    for ligne in page:
        from urllib.parse import urlsplit
        parsed = urlsplit(ligne['url'])
        navigation = dossier.pour_vue_params(ligne.pop('prise'), nature, pk, {
            **params, 'chrono_ancre': ligne['id'], 'chrono_origine': '1', 'ecran': 'chronologie'})
        ligne['url'] = parsed.path + '?' + urlencode({'contexte_dossier': navigation['contexte_dossier']}) + ('#' + parsed.fragment if parsed.fragment else '')
    retour = reverse('dossiers:prise' if prise else 'dossiers:detail', args=[nature, pk] + ([prise.pk] if prise else [])) + '?' + urlencode({k: v for k, v in params.items() if k != 'contexte_dossier'})
    return render(request, 'dossiers/chronologie.html', {
        'objet': objet, 'nature': nature, 'prise': prise, 'form': form, 'page_obj': page,
        'debut': debut, 'fin': fin, 'retour': retour,
        'selection': params.get('chrono_ancre'),
        'parametres': {k: v for k, v in params.items() if k not in ('chrono_debut', 'chrono_fin', 'chrono_type', 'chrono_page', 'chrono_ancre')},
        'precedent': c.lien(nature, pk, {**params, 'chrono_page': page.previous_page_number()}) if page.has_previous() else '',
        'suivant': c.lien(nature, pk, {**params, 'chrono_page': page.next_page_number()}) if page.has_next() else '',
    })
