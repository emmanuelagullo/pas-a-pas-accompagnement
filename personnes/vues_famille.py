"""Consultation, saisie et exploitation des déclarations familiales datées."""
import csv
from collections import Counter
from urllib.parse import urlencode

from django import forms
from .champs_saisie import FormulaireMetier, FormulaireModeleMetier
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe

from . import bd6, famille, suivi
from .models import Personne, DeclarationFamiliale
from .vues_bd6 import navigation_histoire, traiter
from .forms_hebergement import date_champ
from .exports import cellule_csv


class DeclarationForm(FormulaireModeleMetier):
    attendu = forms.CharField(widget=forms.HiddenInput)
    debut = date_champ('Depuis quelle date cette situation est-elle vraie ?')
    motif = forms.CharField(label='Motif de correction ou d’ajout dans le passé', max_length=240, required=False)

    class Meta:
        model = DeclarationFamiliale
        fields = ['debut', *famille.CHAMPS, 'source']
        help_texts = {
            'situation_familiale': 'Situation déclarée, par exemple célibataire ou en couple. Elle ne se déduit pas du ménage.',
            'rapports_parentaux': 'Par exemple en contact ou perdus de vue. Ce renseignement ne désigne pas un représentant légal.',
            'fratrie': 'Conservez le sens déclaré, par exemple « deux sœurs ». Aucun nombre de frères et sœurs n’est déduit du ménage.',
            'enfants_a_charge': 'Déclaration concernant cette personne, même si les enfants ne sont pas nommés. Vide : inconnu ; 0 : aucun déclaré.',
            'enfants_non_a_charge': 'Ces nombres ne créent aucune identité et ne modifient pas la composition du ménage.',
            'grossesse': 'Déclaration individuelle à cette date ; ne pas déduire une grossesse d’un effectif de ménage.',
            'source': 'Par exemple : entretien fictif du 12 octobre. Date du fait et date de saisie restent distinctes.',
        }


class ConsultationForm(FormulaireMetier):
    date = date_champ('Situation à la date du')


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(famille.DROITS_LECTURE, raise_exception=True)
def histoire(request, pk, action=None, fait_pk=None):
    personne = get_object_or_404(Personne, pk=pk)
    params, origine, retour, query = navigation_histoire(request, personne)
    if request.GET.get('date'):
        query += ('&' if query else '') + urlencode({'date': request.GET['date'][:20]})
    base = reverse('dossiers:famille', args=[pk]) + ('?' + query if query else '')
    # Réserver la révision lue avant de charger les valeurs du formulaire.
    attendu = bd6.jeton(personne)
    faits = personne.declarations_familiales.select_related('auteur')
    if action is not None:
        suivi.exiger(request.user, 'add_declarationfamiliale')
        correction = get_object_or_404(faits, pk=fait_pk) if fait_pk else None
        if correction:
            suivi.exiger(request.user, 'change_declarationfamiliale')
        from .champs_saisie import valeurs_proposees
        initial, proposition = valeurs_proposees(request, faits, famille.CHAMPS, correction)
        initial["attendu"] = attendu
        # Ne pas donner l'instance persistée à ModelForm : les modifications
        # validées ne doivent être écrites que par le service et son journal.
        form = DeclarationForm(request.POST if request.method == 'POST' else None, initial=initial)
        if correction:
            form.fields['motif'].required = True
            form.fields['debut'].help_text = 'La correction peut rectifier la date, sans traverser une autre déclaration. Les périodes voisines et leur avant/après sont conservés.'
        return traiter(request, form, 'Corriger une déclaration familiale' if correction else 'Enregistrer une situation familiale',
            lambda **d: famille.renseigner(request.user, personne, correction=correction.pk if correction else None, **d),
            base, personne, **proposition, explication='La situation est propre à cette personne. Les valeurs proposées reprennent la dernière déclaration ; vérifiez-les. Une valeur vide signifie non renseignée, pas zéro ou non. Le ménage et les prestations ne changent pas.')
    form = ConsultationForm(request.GET if 'date' in request.GET else None, initial={'date': timezone.localdate()})
    jour = form.cleaned_data['date'] if form.is_bound and form.is_valid() else timezone.localdate()
    declaration = famille.a_date([personne], jour).first() if not form.is_bound or form.is_valid() else None
    return render(request, 'dossiers/famille.html', {'objet': personne, 'faits': faits,
        'declaration': declaration, 'date_situation': jour, 'consultation': form, 'retour': retour,
        'query_famille': query, 'parametres_famille': {**params, **origine},
        'revisions': personne.revisiondeclarationfamiliale_set.select_related('auteur', 'declaration')})


class RapportForm(ConsultationForm):
    q = forms.CharField(label='Nom ou prénom', max_length=160, required=False)
    situation = forms.CharField(label='Situation familiale exacte', max_length=160, required=False,
        help_text='Valeur déclarée complète, sans distinction de majuscules. Vide : toutes les valeurs.')
    renseignement = forms.ChoiceField(label='Déclaration', choices=[('', 'Toutes les personnes'),
        ('connue', 'Avec une déclaration applicable'), ('inconnue', 'Sans déclaration applicable')], required=False)


@never_cache
@require_safe
@login_required
@permission_required(famille.DROITS_LECTURE, raise_exception=True)
def rapport(request):
    selection = request.GET.copy()
    if not selection:
        selection['date'] = timezone.localdate().isoformat()
    form = RapportForm(selection)
    lignes, bilan, query = [], [], ''
    if form.is_valid():
        d = form.cleaned_data
        population = Personne.objects.all()
        for mot in d['q'].split():
            population = population.filter(Q(designation__icontains=mot) | Q(prenom__icontains=mot))
        applicables = famille.a_date(population, d['date'])
        if d['situation']:
            applicables = applicables.filter(situation_familiale__iexact=d['situation'])
            population = population.filter(pk__in=applicables.values('personne_id'))
        if d['renseignement']:
            filtre = Q(pk__in=applicables.values('personne_id'))
            population = population.filter(filtre if d['renseignement'] == 'connue' else ~filtre)
        declarations = {x.personne_id: x for x in applicables}
        comptes = Counter()
        for p in population.order_by('designation', 'prenom', 'pk'):
            fait = declarations.get(p.pk)
            lignes.append({'personne': p, 'declaration': fait})
            comptes[fait.situation_familiale or 'Situation non renseignée' if fait else 'Aucune déclaration applicable'] += 1
        bilan = sorted(comptes.items())
        query = urlencode({k: selection.get(k, '') for k in ('date', 'q', 'situation', 'renseignement')})
        if request.GET.get('format') == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="declarations-familiales.csv"'
            writer = csv.writer(response, delimiter=';')
            writer.writerow(['date_reference', 'identifiant_personne', 'personne', 'debut_declaration',
                *famille.CHAMPS, 'source'])
            for ligne in lignes:
                p, fait = ligne['personne'], ligne['declaration']
                writer.writerow([d['date'].isoformat(), p.pk, cellule_csv(p), fait.debut.isoformat() if fait else '',
                    *[cellule_csv(('Oui' if getattr(fait, c) else 'Non') if c == 'grossesse' and fait and fait.grossesse is not None
                        else getattr(fait, c) if fait else None) for c in famille.CHAMPS], cellule_csv(fait.source if fait else '')])
            return response
    return render(request, 'dossiers/rapport_famille.html', {'form': form,
        'page_obj': Paginator(lignes, 50).get_page(request.GET.get('page')), 'bilan': bilan,
        'nombre': len(lignes), 'query_rapport': query})
