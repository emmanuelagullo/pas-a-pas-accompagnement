"""Créer depuis Form2, avec un rattachement explicite et les services existants."""
from urllib.parse import urlencode
from datetime import date
from django import forms
from .champs_saisie import FormulaireMetier
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.http import Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from . import admission, repas, dossier
from .models import Personne, Menage
from .vues_admission import AdmissionGuideeForm
from .forms_repas import AccordForm, ServicesForm
from .vues_dossiers import parametres


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(dossier.DROITS, raise_exception=True)
def nouveau(request, nature, pk, prestation):
    if nature not in ('menage', 'personne') or prestation not in ('hebergement', 'repas', 'services_repas'):
        raise Http404
    from . import hebergement as h
    if prestation == 'hebergement':
        h.droit(request.user, 'add_accordhebergement')
    else:
        repas.droit(request.user, 'add_accordrepas')
    objet = get_object_or_404(Menage if nature == 'menage' else Personne, pk=pk)
    periodes = objet.accompagnements.select_related('menage').prefetch_related('beneficiaires').order_by('-debut', 'pk')
    # Un retour signé Form3 borne le choix à son vrai parent.
    contexte = dossier.valeurs_vue(request, nature, pk)
    if contexte.get('ecran') == 'prise' and contexte.get('prise'):
        periodes = periodes.filter(pk=contexte['prise'])
    liste = list(periodes)
    donnees = request.POST if request.method == 'POST' else request.GET
    valeur = donnees.get('accompagnement', '')
    # Un seul choix est affiché comme tel ; plusieurs choix exigent une sélection.
    a = next((p for p in liste if str(p.pk) == valeur), None)
    if not valeur and request.method == 'GET' and len(liste) == 1:
        a = liste[0]
    params = {**parametres(request), **contexte, **{k: request.GET.get(k, '')[:40] for k in
        ('sejour', 'repas', 'origine_menage', 'origine_sejour', 'origine_repas')}}
    retour = reverse('dossiers:detail', args=[nature, pk]) + '?' + urlencode(params)
    signer = dossier.pour_prise if contexte.get('ecran') == 'prise' else dossier.pour_vue
    navigation = signer(request, a, nature, pk, params) if a else {}
    if navigation:
        retour = navigation['retour_dossier']
    jour = timezone.localdate()
    initial = {'accompagnement': a.pk if a else None}
    if a:
        date_contexte = dossier.lire(request, a).get('dossier_valeurs', {}).get('date_service')
        jour = date.fromisoformat(date_contexte) if date_contexte else jour
        debut = max(a.debut, jour)
        fin = min(a.fin_prevue, a.fin) if a.fin_prevue and a.fin else a.fin_prevue
        initial.update(debut=debut, fin=fin if fin and fin > debut else None, admission=debut, beneficiaires=[pk] if nature == 'personne' else [p.pk for p in a.beneficiaires.all()])
        if prestation == 'hebergement':
            initial['attendu'] = admission.jeton(a)
            form = AdmissionGuideeForm(request.POST if request.method == 'POST' else None,
                acteur=request.user, beneficiaires=a.beneficiaires.all(), initial=initial)
        elif prestation == 'services_repas':
            initial['attendu'] = repas.jeton_services(a)
            form = ServicesForm(request.POST if request.method == 'POST' else None, accompagnement=a, initial=initial)
        else:
            form = AccordForm(request.POST if request.method == 'POST' else None, accompagnement=a, initial=initial)
    else:
        form = FormulaireMetier(request.POST if request.method == 'POST' else None, initial=initial)
    champ = forms.ModelChoiceField(periodes, label='Prise en charge', empty_label='Choisir la prise en charge',
        help_text='Rattachement de cette prestation et bénéficiaires possibles. Aucune prise en charge ne sera créée.')
    champ.label_from_instance = lambda p: f'{p.debut:%d/%m/%Y} → {p.fin.strftime("%d/%m/%Y") if p.fin else "ouverte"} — {p.menage}'
    if len(liste) == 1:
        champ.widget = forms.HiddenInput()
    champ.widget.attrs['data-periode-dossier'] = '1'
    form.fields = {'accompagnement': champ, **form.fields}
    if 'beneficiaires' in form.fields:
        form.order_fields(['accompagnement', 'beneficiaires', 'debut', 'fin', 'duree', 'calcul_periode', 'arrivee_effectuee', 'admission', 'lieu', 'service', 'services', 'prestataire', 'attendu'])
    statut = 200
    if request.method == 'POST' and form.is_valid() and a:
        d = form.cleaned_data.copy()
        d.pop('accompagnement')
        try:
            if prestation == 'hebergement':
                accord = admission.accueillir(request.user, a, **d)
                sejours = accord.sejours.non_annules()
                if nature == 'personne':
                    sejours = sejours.filter(beneficiaires=objet)
                s = sejours.order_by('pk').first()
                if s:
                    params['sejour'] = str(s.pk)
                    params['prevision'] = ''
                else:
                    params['prevision'] = str(accord.pk)
            elif prestation == 'services_repas':
                accords = repas.accorder_services(request.user, a, **d)
                params['repas'] = str(accords[0].pk)
            else:
                accord = repas.accorder(request.user, a, **d)
                params['repas'] = str(accord.pk)
        except ValidationError as erreur:
            form.add_error(None, erreur)
            statut = 409
        except OperationalError:
            form.add_error(None, 'Écriture non confirmée. Rechargez le dossier avant de réessayer.')
            statut = 409
        else:
            messages.success(request, ('Arrivée enregistrée.' if d['arrivee_effectuee'] else 'Séjour prévu ; arrivée à confirmer.') if prestation == 'hebergement' else 'Repas accordés ; aucune distribution créée.')
            return redirect(signer(request, a, nature, pk, params)['retour_dossier'])
    return render(request, 'dossiers/nouvelle_prestation.html', {**navigation, 'objet': objet, 'nature': nature,
        'parametres_retour': params, 'form': form, 'periode': a, 'unique': len(liste) == 1, 'prestation': prestation, 'retour': retour,
        'titre': 'Nouveau séjour' if prestation == 'hebergement' else 'Nouvelle période de repas'}, status=statut)
