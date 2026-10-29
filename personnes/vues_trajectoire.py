"""Trajectoire depuis un dossier ; l'ancienne URL garde le filtre de prise."""
from urllib.parse import urlencode
from datetime import timedelta
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
    vue_debut = forms.ChoiceField(label='Situation de départ', required=False)
    vue_fin = forms.ChoiceField(label='Situation d’arrivée', required=False)
    presentation_evolution = forms.ChoiceField(label='Présentation', required=False, choices=[('changements','Informations ayant évolué'),('tout','Toutes les informations')])
    format_elements = forms.ChoiceField(label='Éléments datés', required=False, choices=[('liste', 'Liste complète'), ('personnelle', 'Frise personnelle')])
    debut = forms.DateField(label='Depuis (inclus)', required=False,
                            widget=forms.DateInput(attrs={'type': 'date'}))
    fin = forms.DateField(label='Jusqu’au (inclus)', required=False,
                          widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, personnes, prises, **kwargs):
        data = args[0].copy() if args else None
        selection = next((a for a in prises if data is not None and str(a.pk) == data.get('prise')), None)
        self.dates_vues = {'today': timezone.localdate()}
        choix = [('today', 'Aujourd’hui')]
        if not selection and prises:
            connues = [p for p in prises if p.debut <= timezone.localdate()]
            if connues:
                self.dates_vues['entree'] = min(p.debut for p in connues)
                choix.insert(0, ('entree', 'Début des prises en charge connues'))
                if all(p.fin and p.fin <= timezone.localdate() for p in connues):
                    self.dates_vues['sortie'] = max(p.fin for p in connues) - timedelta(days=1)
                    choix.insert(1, ('sortie', 'Dernier jour des prises en charge connues'))
        self.sortie_future = selection.fin_prevue if selection and not selection.fin and selection.fin_prevue and selection.fin_prevue > timezone.localdate() else None
        if selection:
            if selection.debut <= timezone.localdate():
                self.dates_vues['entree'] = selection.debut
                choix.insert(0, ('entree', 'Début de la prise en charge'))
            sortie = selection.fin
            if sortie:
                dernier = sortie - timedelta(days=1)
                if dernier <= timezone.localdate():
                    self.dates_vues['sortie'] = dernier
                    choix.insert(1, ('sortie', 'Au dernier jour' if selection.fin else 'Au dernier jour prévu'))
                else:
                    self.sortie_future = sortie
        choix.append(('date', 'À une date…'))
        if data is not None:
            for borne, defaut in [('debut', 'entree' if 'entree' in self.dates_vues else 'date'),
                                  ('fin', 'sortie' if 'sortie' in self.dates_vues else 'today')]:
                mode = 'vue_' + borne
                if mode not in data:
                    data[mode] = 'date' if data.get(borne) else defaut
                if data[mode] in self.dates_vues:
                    data[borne] = self.dates_vues[data[mode]].isoformat()
            args = (data, *args[1:])
        if data is not None and not data.get('presentation_evolution'):
            data['presentation_evolution'] = 'changements'
            args = (data, *args[1:])
        super().__init__(*args, **kwargs)
        self.order_fields(['beneficiaire', 'prise', 'vue_debut', 'debut', 'vue_fin', 'fin'])
        for borne in ('debut', 'fin'):
            self.fields['vue_' + borne].choices = choix
            if data is not None and data.get('vue_' + borne) in self.dates_vues:
                self.fields[borne].widget.attrs['disabled'] = True
            self.fields[borne].widget.attrs['max'] = timezone.localdate().isoformat()
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
    if ancienne_prise and 'presentation_evolution' not in data:
        data['presentation_evolution'] = 'tout'  # Compatibilité de l'ancienne URL spécialisée.
    if ancienne_prise and 'prise' not in data:
        data['prise'] = str(ancienne_prise.pk)
    if not data.get('prise') and 'fin' not in data and params.get('date_service'):
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
        'frise_personnelle': personnelle(lignes, date_initiale, date_finale),
        'comparaison': comparaison, 'comparaison_affichee': [l for l in comparaison if form.cleaned_data.get('presentation_evolution') == 'tout' or valeur_comparee(l, 'initial') != valeur_comparee(l, 'final')] if form.is_valid() else [],
        'libelle_debut': libelle_borne(form, 'debut', date_initiale), 'libelle_fin': libelle_borne(form, 'fin', date_finale), 'date_initiale': date_initiale, 'date_finale': date_finale,
        'retour_trajectoire': retour, 'parametres': {**{k: v for k, v in params.items() if k not in ('prise', 'beneficiaire', 'debut', 'fin', 'vue_debut', 'vue_fin')},
                       **({'contexte_dossier':contexte['contexte_dossier']} if contexte else {})},
        'selection_prise': selection, 'prise_retour':prise_retour, 'prise':prise_retour,
        'navigation_query':urlencode(params),
    })


def valeur_comparee(ligne, borne):
    lecture = ligne.get(borne + '_lecture')
    if lecture is not None:
        return (lecture.get('texte'), bool(lecture.get('conflit')),
                tuple(sorted({f.valeur for f in lecture.get('anciens', [])})))
    return ligne.get(borne)


def libelle_borne(form, borne, jour):
    if not form.is_valid() or not jour:
        return ''
    mode = form.cleaned_data.get('vue_' + borne)
    if mode == 'date':
        return jour.strftime('%d/%m/%Y')
    return dict(form.fields['vue_' + borne].choices).get(mode, '') + ' · ' + jour.strftime('%d/%m/%Y')


def personnelle(lignes, debut, fin):
    """Points à date d'effet, après le filtrage métier ; aucune continuité ajoutée.

    Premier périmètre : déclarations personnelles et séries économiques déjà
    chargées par la trajectoire. Les récits, prestations et témoins collectifs
    restent dans la liste complète ; les corrections sont dans la source.
    """
    if debut is None or fin is None:
        return []
    duree = max(1, (fin - debut).days)
    return [{**l, 'position': f'{100 * (l["date"] - debut).days / duree:.4f}'}
            for l in lignes if not l['ancien'] and l['beneficiaire'] is not None
            and l['nature'] in ('Déclaration personnelle', 'Ressources', 'Dettes')]
