"""Coordonnées personnelles datées et recherche géographique explicite."""
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

from . import bd6, coordonnees, suivi
from .models import Personne, CoordonneesPersonnelles
from .vues_bd6 import navigation_histoire, traiter
from .forms_hebergement import date_champ
from .exports import cellule_csv


class CoordonneesForm(FormulaireModeleMetier):
    attendu = forms.CharField(widget=forms.HiddenInput)
    debut = date_champ('Depuis quelle date cette situation est-elle vraie ?')
    motif = forms.CharField(label='Motif de correction ou d’ajout dans le passé', max_length=240, required=False)

    class Meta:
        model = CoordonneesPersonnelles
        fields = ['debut', *coordonnees.CHAMPS, 'source']
        help_texts = {
            'usage_adresse':'Qualification déclarée : une dernière adresse fixe n’est pas nécessairement l’adresse actuelle ou le lieu d’hébergement. Les anciennes données restent non qualifiées.',
            'rue': 'Adresse déclarée par la personne. Ne désigne ni son hébergement effectif, ni une domiciliation administrative vérifiée.',
            'code_postal': 'Facultatif ; les codes étrangers et les zéros initiaux sont conservés.',
            'ville': 'Ville déclarée ; réutilisez un libellé cohérent pour les filtres et regroupements.',
            'pays': 'Facultatif, sans déduction depuis le code postal ou la nationalité.',
            'telephone': 'Numéro déclaré, avec indicatif et complément si utiles. Aucun appel ni message n’est envoyé.',
            'courriel': 'Adresse déclarée, sans vérification ni envoi automatique.',
            'fax': 'Canal facultatif, uniquement s’il est utile.',
            'source': 'Par exemple : entretien fictif du 12 octobre. La source ne vaut pas vérification des coordonnées.',
        }



class ConsultationForm(FormulaireMetier):
    date = date_champ('Situation à la date du')


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(coordonnees.DROITS_LECTURE, raise_exception=True)
def histoire(request, pk, action=None, fait_pk=None):
    personne = get_object_or_404(Personne, pk=pk)
    params, origine, retour, query = navigation_histoire(request, personne)
    if request.GET.get('date'):
        query += ('&' if query else '') + urlencode({'date': request.GET['date'][:20]})
    base = reverse('dossiers:coordonnees', args=[pk]) + ('?' + query if query else '')
    # Réserver la révision lue avant de charger les valeurs du formulaire.
    attendu = bd6.jeton(personne)
    faits = personne.coordonnees.select_related('auteur')
    if action is not None:
        suivi.exiger(request.user, 'add_coordonneespersonnelles')
        correction = get_object_or_404(faits, pk=fait_pk) if fait_pk else None
        if correction:
            suivi.exiger(request.user, 'change_coordonneespersonnelles')
        from .champs_saisie import valeurs_proposees
        initial, proposition = valeurs_proposees(request, faits, coordonnees.CHAMPS, correction)
        initial["attendu"] = attendu
        # Ne pas donner l'instance persistée à ModelForm : les modifications
        # validées ne doivent être écrites que par le service et son journal.
        form = CoordonneesForm(request.POST if request.method == 'POST' else None, initial=initial)
        if correction:
            form.fields['motif'].required = False
            form.fields['debut'].help_text = 'La correction peut rectifier la date, sans traverser une autre déclaration. Les périodes voisines et leur avant/après sont conservés.'
        return traiter(request, form, 'Corriger des coordonnées' if correction else 'Enregistrer des coordonnées',
            lambda **d: coordonnees.renseigner(request.user, personne, correction=correction.pk if correction else None, **d),
            base, personne, **proposition, explication='Les coordonnées sont propres à cette personne. Vérifiez toutes les valeurs proposées ; un champ vidé devient non renseigné à cette date. Le ménage, les partenaires et les lieux d’hébergement ne changent pas.')
    form = ConsultationForm(request.GET if 'date' in request.GET else None, initial={'date': timezone.localdate()})
    jour = form.cleaned_data['date'] if form.is_bound and form.is_valid() else timezone.localdate()
    declaration = coordonnees.a_date([personne], jour).first() if not form.is_bound or form.is_valid() else None
    return render(request, 'dossiers/coordonnees.html', {'objet': personne, 'faits': faits,
        'coordonnees': declaration, 'date_situation': jour, 'consultation': form, 'retour': retour,
        'query_coordonnees': query, 'parametres_coordonnees': {**params, **origine},
        'revisions': personne.revisioncoordonneespersonnelles_set.select_related('auteur', 'coordonnees')})


class RapportForm(ConsultationForm):
    usage_adresse=forms.ChoiceField(label="Nature de l’adresse",required=False,choices=[("","Toutes les natures"),("non_qualifiee","Non qualifiée"),*[(k,v) for k,v in CoordonneesPersonnelles._meta.get_field("usage_adresse").choices if k]])
    q = forms.CharField(label='Nom ou prénom', max_length=160, required=False)
    ville = forms.CharField(label='Ville exacte', max_length=160, required=False)
    pays = forms.CharField(label='Pays exact', max_length=160, required=False)
    code_postal = forms.CharField(label='Code postal exact', max_length=20, required=False)


@never_cache
@require_safe
@login_required
@permission_required(coordonnees.DROITS_LECTURE, raise_exception=True)
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
        applicables = coordonnees.a_date(population, d['date'])
        filtres = {champ + '__iexact': d[champ] for champ in ('ville', 'pays', 'code_postal','usage_adresse') if d[champ]}
        if d['usage_adresse']=='non_qualifiee':filtres['usage_adresse__iexact']=''
        if filtres:
            applicables = applicables.filter(**filtres)
            population = population.filter(pk__in=applicables.values('personne_id'))
        infos = {x.personne_id: x for x in applicables}
        comptes = Counter()
        for p in population.order_by('designation', 'prenom', 'pk'):
            fait = infos.get(p.pk)
            lignes.append({'personne': p, 'coordonnees': fait})
            comptes[(fait.ville or 'Ville non renseignée', fait.pays or 'Pays non renseigné') if fait else
                ('Aucune coordonnée applicable', '')] += 1
        bilan = sorted(comptes.items())
        query = urlencode({k: selection.get(k, '') for k in ('date', 'q', 'ville', 'pays', 'code_postal','usage_adresse')})
        if request.GET.get('format') == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="coordonnees-personnelles.csv"'
            writer = csv.writer(response, delimiter=';')
            writer.writerow(['date_reference', 'identifiant_personne', 'personne', 'debut_coordonnees',
                *coordonnees.CHAMPS, 'source'])
            for ligne in lignes:
                p, fait = ligne['personne'], ligne['coordonnees']
                writer.writerow([d['date'].isoformat(), p.pk, cellule_csv(p), fait.debut.isoformat() if fait else '',
                    *[cellule_csv(getattr(fait, c) if fait else '') for c in coordonnees.CHAMPS],
                    cellule_csv(fait.source if fait else '')])
            return response
    return render(request, 'dossiers/rapport_coordonnees.html', {'form': form,
        'page_obj': Paginator(lignes, 50).get_page(request.GET.get('page')), 'bilan': bilan,
        'nombre': len(lignes), 'query_rapport': query})
