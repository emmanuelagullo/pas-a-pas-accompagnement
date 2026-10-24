"""Désignation explicite d'un contact dans la composition, sans nouvelle entrée de menu."""
import csv
from urllib.parse import urlencode
from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe
from . import bd6, contacts_menage, suivi
from .models import Menage, Personne
from .vues_bd6 import parametres_retour, retour, traiter
from .vues_famille import ConsultationForm
from .forms_hebergement import date_champ
from .exports import cellule_csv


class DesignationForm(forms.Form):
    contact = forms.ModelChoiceField(Personne.objects.all(), required=False, widget=forms.HiddenInput)
    debut = date_champ('Depuis quelle date cette désignation est-elle vraie ?')
    source = forms.CharField(label='Source de la désignation', max_length=160,
        help_text='Par exemple : choix exprimé lors d’un entretien fictif. Ne vaut ni mandat professionnel ni représentation légale.')
    motif = forms.CharField(label='Motif de correction ou d’ajout dans le passé', max_length=240, required=False)
    attendu = forms.CharField(widget=forms.HiddenInput)


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(contacts_menage.DROITS_LECTURE, raise_exception=True)
def histoire(request, pk, action=None, fait_pk=None):
    menage = get_object_or_404(Menage, pk=pk)
    params = parametres_retour(request)
    query = urlencode({**params, 'date': request.GET.get('date', '')[:20]})
    base = reverse('dossiers:contact_menage', args=[pk]) + '?' + query
    attendu = bd6.jeton(menage)
    faits = menage.contacts_designes.select_related('contact', 'auteur')
    if action:
        suivi.exiger(request.user, 'add_contactmenage')
        correction = get_object_or_404(faits, pk=fait_pk) if fait_pk else None
        if correction:
            suivi.exiger(request.user, 'change_contactmenage')
        route = 'dossiers:contact_corriger' if correction else 'dossiers:contact_nouveau'
        args = [pk, correction.pk] if correction else [pk]
        personne = None
        identifiant = request.GET.get('personne')
        if identifiant:
            from .vues_suivi import _uuid_valide
            if not _uuid_valide(identifiant):
                from django.http import Http404
                raise Http404
        if identifiant:
            personne = get_object_or_404(Personne, pk=identifiant)
        elif correction and not request.GET.get('choisir') and request.GET.get('aucun') != '1':
            personne = correction.contact
        aucun = request.GET.get('aucun') == '1' or (correction and correction.contact_id is None and not request.GET.get('choisir'))
        if request.method == 'GET' and (request.GET.get('choisir') or not personne and not aucun):
            recherche = request.GET.get('recherche_contact', '')[:160].strip()
            personnes = Personne.objects.all()
            for mot in recherche.split():
                personnes = personnes.filter(Q(designation__icontains=mot) | Q(prenom__icontains=mot))
            page = Paginator(personnes.order_by('designation', 'prenom', 'pk'), 25).get_page(request.GET.get('page_contact'))
            for p in page:
                p.url_choix = reverse(route, args=args) + '?' + query + '&' + urlencode({'personne': p.pk})
            return render(request, 'dossiers/choisir_contact.html', {'objet': menage, 'page_obj': page,
                'recherche_contact': recherche, 'params_contact': {**params, 'date': request.GET.get('date', '')},
                'url_aucun': reverse(route, args=args) + '?' + query + '&aucun=1', 'retour': base})
        form = DesignationForm(request.POST if request.method == 'POST' else None, initial={
            'contact': personne, 'debut': correction.debut if correction else timezone.localdate(),
            'source': correction.source if correction else '', 'attendu': attendu})
        form.fields['motif'].required = bool(correction)
        # Le choix a été fait explicitement dans la recherche, y compris le
        # retrait ; un POST forgé ne peut remplacer sa cible silencieusement.
        if form.is_bound and form.is_valid() and form.cleaned_data['contact'] != personne:
            form.add_error(None, 'Le contact ne correspond pas au choix confirmé. Revenez à la recherche.')
        if form.is_bound and not personne and not aucun:
            form.add_error(None, 'Choisissez explicitement une personne ou le retrait de la désignation.')
        return traiter(request, form, 'Corriger la désignation du contact' if correction else 'Confirmer le contact du ménage',
            lambda **d: contacts_menage.designer(request.user, menage, correction=correction.pk if correction else None, **d),
            base, menage, explication=f'Contact choisi : {personne or "aucun contact désigné"}. Cette désignation ne crée aucune appartenance, prestation ou responsabilité juridique.',
            versions=[], choix_contact=reverse(route, args=args) + '?' + query + '&choisir=1')
    consultation = ConsultationForm(request.GET if request.GET.get('date') else None, initial={'date': timezone.localdate()})
    jour = consultation.cleaned_data['date'] if consultation.is_bound and consultation.is_valid() else timezone.localdate()
    courant = contacts_menage.a_date([menage], jour).first() if not consultation.errors else None
    if request.GET.get('format') == 'csv' and not consultation.errors:
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="contact-menage.csv"'
        w = csv.writer(response, delimiter=';')
        w.writerow(['date_reference', 'menage_id', 'menage', 'contact_id', 'contact', 'debut_designation', 'source'])
        w.writerow([jour.isoformat(), menage.pk, cellule_csv(menage), courant.contact_id if courant and courant.contact_id else '',
            cellule_csv(courant.contact if courant and courant.contact_id else ''), courant.debut.isoformat() if courant else '', cellule_csv(courant.source if courant else '')])
        return response
    return render(request, 'dossiers/contact_menage.html', {'objet': menage, 'faits': faits, 'designation': courant,
        'date_situation': jour, 'consultation': consultation, 'params_contact': params,
        'query_contact': query, 'retour': retour('menage', pk, params),
        'revisions': menage.revisioncontactmenage_set.select_related('auteur')})
