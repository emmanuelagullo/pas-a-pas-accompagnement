"""Trajectoire depuis un dossier ; l'ancienne URL garde le filtre de prise."""
from urllib.parse import urlencode
from django import forms
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from .champs_saisie import FormulaireMetier
from .models import Accompagnement, Appartenance, Menage, Personne
from . import dossier, social, trajectoire


class Filtres(FormulaireMetier):
    beneficiaire = forms.ChoiceField(label='Personne', required=False)
    prise = forms.ChoiceField(label='Prise en charge', required=False,
        help_text='Filtre les faits liés à cette prise ; l’histoire personnelle reste indépendante des prises en charge.')
    debut = forms.DateField(label='Depuis (inclus)', required=False,
                            widget=forms.DateInput(attrs={'type': 'date'}))
    fin = forms.DateField(label='Jusqu’au (inclus)', required=False,
                          widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, personnes, prises, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['beneficiaire'].choices = [('', 'Toutes les personnes du dossier')] + [(str(p.pk), str(p)) for p in personnes]
        self.fields['prise'].choices = [('', 'Toutes les prises en charge')] + [
            (str(a.pk), f'{a.debut:%d/%m/%Y} — {a.menage}') for a in prises]

    def clean(self):
        d = super().clean()
        if d.get('debut') and d.get('fin') and d['fin'] < d['debut']:
            self.add_error('fin', 'La fin ne peut pas précéder le début.')
        for champ in ('debut', 'fin'):
            if d.get(champ) and d[champ] > timezone.localdate():
                self.add_error(champ, 'Choisissez une date non future pour consulter les faits connus.')
        return d


@never_cache
@require_GET
@login_required
def detail(request, pk):
    social.droit(request.user, 'view_situationsociale')
    a = get_object_or_404(Accompagnement.objects.select_related('menage'), pk=pk)
    contexte = dossier.lire(request, a)
    vue = contexte.get('dossier_valeurs', {}).get('vue', {})
    nature = vue.get('nature', 'menage')
    objet = get_object_or_404(Personne, pk=vue['pk']) if nature == 'personne' else a.menage
    return afficher(request, nature, objet, a, contexte)


@never_cache
@require_GET
@login_required
def dossier_detail(request, nature, pk):
    social.exiger(request.user, 'view_personne')
    if nature == 'personne':
        objet = get_object_or_404(Personne, pk=pk)
    elif nature == 'menage':
        social.exiger(request.user, 'view_menage')
        objet = get_object_or_404(Menage, pk=pk)
    else:
        raise Http404
    return afficher(request, nature, objet)


def afficher(request, nature, objet, ancienne_prise=None, contexte=None):
    prises = list(objet.accompagnements.select_related('menage').prefetch_related('beneficiaires').order_by('debut', 'pk')) if request.user.has_perms(dossier.DROITS) else []
    liens = list(Appartenance.objects.filter(menage=objet).select_related('personne')) if nature == 'menage' else []
    personnes = [objet] if nature == 'personne' else sorted(
        {p.pk: p for p in [l.personne for l in liens] + [p for a in prises for p in a.beneficiaires.all()]}.values(), key=str)
    params = {**dossier.valeurs_vue(request, nature, objet.pk),
        **{k: request.GET[k][:160] for k in ('q', 'mode', 'page', 'date_service', 'origine_menage', 'origine_sejour', 'origine_repas', 'retour_prise') if k in request.GET}}
    if contexte:
        params = {**params, **contexte.get('dossier_valeurs', {}).get('vue', {})}
    params.pop('nature', None); params.pop('pk', None)
    data = request.GET.copy()
    if ancienne_prise and 'prise' not in data:
        data['prise'] = str(ancienne_prise.pk)
    if 'fin' not in data and params.get('date_service'):
        data['fin'] = params['date_service']
    form = Filtres(data, personnes=personnes, prises=prises)
    lignes, comparaison = [], []
    selection = None
    date_initiale = date_finale = None
    def dans_dossier(p, jour):
        if nature == 'personne':
            return True
        return any(l.personne_id == p.pk and l.debut <= jour and (l.fin is None or jour < l.fin) for l in liens) or any(
            a.debut <= jour and (a.fin is None or jour < a.fin) and any(b.pk == p.pk for b in a.beneficiaires.all()) for a in prises)
    if form.is_valid():
        d = form.cleaned_data
        selection = next((a for a in prises if str(a.pk) == d['prise']), None)
        beneficiaire = next((p for p in personnes if str(p.pk) == d['beneficiaire']), None)
        # Une vue personne exclut toujours les bilans collectifs, même sans filtre explicite.
        if nature == 'personne':
            beneficiaire = objet
        retenues = [selection] if selection else prises
        selection_personnes = [beneficiaire] if beneficiaire else (list(selection.beneficiaires.all()) if selection else personnes)
        if beneficiaire and selection and not any(p.pk == beneficiaire.pk for p in selection.beneficiaires.all()):
            form.add_error('beneficiaire', 'Cette personne ne bénéficie pas de la prise en charge sélectionnée.')
            return render(request, 'social/_trajectoire_contenu.html' if request.headers.get('X-Condition-Evolution') == '1' else 'social/trajectoire.html', {'evolution_integree': request.headers.get('X-Condition-Evolution') == '1', 'objet':objet, 'nature':nature, 'form':form,
                'retour_trajectoire':reverse('dossiers:detail', args=[nature,objet.pk]) + '?' + urlencode(params), 'parametres':params})
        params['date_service'] = (d['fin'] or timezone.localdate()).isoformat()
        lignes = trajectoire.construire(None, request.user, beneficiaire, d['debut'], d['fin'],
            prises=retenues, personnes=selection_personnes, dans_dossier=dans_dossier)
        dates = [l['date'] for l in lignes]
        date_finale = d['fin'] or timezone.localdate()
        date_initiale = d['debut'] or min([date_finale] + dates + [a.debut for a in retenues])
        comparaison = trajectoire.comparer(request.user, selection_personnes, date_initiale, date_finale, dans_dossier=dans_dossier)
        for entree in comparaison:
            for borne in ('initial_lecture', 'final_lecture'):
                for fait in (entree.get(borne) or {}).get('anciens', []):
                    fait.url_provenance = reverse('suivi:social', args=[fait.accompagnement_id]) + '?' + urlencode({
                        'date': (date_initiale if borne == 'initial_lecture' else date_finale).isoformat(),
                        'contexte_dossier': dossier.pour_vue(request, fait.accompagnement, nature, objet.pk, params)['contexte_dossier']})
        for ligne in lignes:
            if ligne['url'] and ligne.get('prise'):
                ligne['url'] += '?' + urlencode({'date':ligne['date'].isoformat(),
                    'contexte_dossier':dossier.pour_vue(request, ligne['prise'], nature, objet.pk, params)['contexte_dossier']})
            elif ligne['url']:
                p = ligne['beneficiaire']
                ligne['url'] += '?' + urlencode({**params, 'date': ligne['date'].isoformat(),
                    'depuis_nature': nature, 'depuis_pk': str(objet.pk),
                    'depuis_prise': str(selection.pk) if selection else ''})
    if ancienne_prise and contexte and form.is_valid() and request.GET.get('fin'):
        # Conserver la destination historique (y compris sans vue BD), en ne
        # changeant que la date explicitement consultée. Le jeton reste signé.
        valeurs = {**contexte['dossier_valeurs'], 'date_service': date_finale.isoformat()}
        token = signing.dumps(valeurs, salt=dossier.SEL, compress=True)
        contexte = {'contexte_dossier':token, 'dossier_valeurs':valeurs,
                    'retour_dossier':dossier.retour(ancienne_prise, valeurs, token)}
    prise_retour = next((a for a in prises if str(a.pk) == params.get('retour_prise')), None)
    retour = (contexte or {}).get('retour_dossier') or (reverse('dossiers:prise', args=[nature, objet.pk, prise_retour.pk]) + '?' + urlencode(params) if prise_retour else '') or reverse('dossiers:detail', args=[nature, objet.pk]) + '?' + urlencode(params)
    return render(request, 'social/_trajectoire_contenu.html' if request.headers.get('X-Condition-Evolution') == '1' else 'social/trajectoire.html', {
        'evolution_integree': request.headers.get('X-Condition-Evolution') == '1',
        'objet': objet, 'nature': nature, 'form': form, 'lignes': lignes,
        'anciennes_lignes': [l for l in lignes if l['ancien']],
        'comparaison': comparaison, 'date_initiale': date_initiale, 'date_finale': date_finale,
        'retour_trajectoire': retour, 'parametres': {**{k: v for k, v in params.items() if k not in ('prise', 'beneficiaire', 'debut', 'fin')},
                       **({'contexte_dossier':contexte['contexte_dossier']} if contexte else {})},
        'selection_prise': selection, 'prise_retour':prise_retour, 'prise':prise_retour,
        'navigation_query':urlencode(params),
    })
