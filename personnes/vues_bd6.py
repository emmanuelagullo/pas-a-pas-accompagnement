from . import textes_riches as tr
"""Formulaires BD6 ; mêmes validations avec ou sans JavaScript."""
from urllib.parse import urlencode
from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from . import bd6, dossier, suivi, ouverture_prise
from .models import Personne, Menage, Accompagnement, SituationPersonnelle, SituationSociale, CommentaireDossier
from .forms_suivi import AccompagnementForm
from .forms_hebergement import date_champ


class EtatForm(forms.Form):
    attendu = forms.CharField(widget=forms.HiddenInput)


class PrevisionForm(EtatForm):
    fin_prevue = date_champ('Nouvelle fin prévue exclue')
    motif = forms.CharField(label='Motif', max_length=240)


class PremierePriseForm(AccompagnementForm):
    attendu = forms.CharField(widget=forms.HiddenInput)
    rattachement = forms.ChoiceField(label='Rattachement de la prise', choices=[
        ('existant', 'Utiliser un ménage de cette personne'), ('nouveau', 'Créer un ménage avec cette personne')],
        widget=forms.RadioSelect, help_text='La création ne sera faite qu’à la confirmation de ce formulaire.')
    menage = forms.ModelChoiceField(Menage.objects.none(), label='Ménage existant', required=False)
    libelle_menage = forms.CharField(label='Nom du nouveau ménage', max_length=160, required=False,
        help_text='Seulement pour créer un ménage. Ce nom ne désigne ni un chef de famille ni un représentant légal.')

    def __init__(self, *args, acteur, personne, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['beneficiaires'].queryset = Personne.objects.filter(pk=personne.pk)
        self.fields['menage'].queryset = ouverture_prise.menages_personne(personne)
        if not acteur.has_perms(['personnes.add_menage', 'personnes.add_appartenance']):
            self.fields['rattachement'].choices = [('existant', 'Utiliser un ménage de cette personne')]
        if self.is_bound:
            nouveau = self.data.get('rattachement') == 'nouveau'
            self.fields['menage'].disabled = nouveau
            self.fields['libelle_menage'].disabled = not nouveau

    def clean(self):
        d = super().clean()
        if d.get('rattachement') == 'existant' and not d.get('menage'):
            self.add_error('menage', 'Choisissez le ménage de rattachement.')
        elif d.get('rattachement') == 'nouveau' and not d.get('libelle_menage'):
            self.add_error('libelle_menage', 'Nommez le ménage dont vous confirmez la création.')
        return d


class CommentaireForm(EtatForm):
    texte = tr.ChampTexte(label='Commentaire libre', max_length=4000, required=False,
        help_text='Informations utiles au dossier. Les versions précédentes restent consultables.')
    motif = forms.CharField(label='Motif de la modification', max_length=240, required=False,
        help_text='Obligatoire après la première version, y compris pour effacer le texte.')


class SituationForm(EtatForm):
    debut = date_champ('Depuis quelle date cette situation est-elle vraie ?')
    valeur = forms.ChoiceField(label='Situation')
    source = forms.CharField(label='Comment le savez-vous ?', max_length=160,
        help_text='Par exemple : entretien avec la personne le 12/10, courrier CAF, échange avec un partenaire. Aucun document à joindre.')
    motif = forms.CharField(label='Motif de correction ou d’insertion antérieure', max_length=240, required=False)

    def __init__(self, *args, dimension, correction=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['valeur'].choices = SituationSociale.VALEURS[dimension]
        self.fields['debut'].disabled = correction
        self.fields['motif'].required = correction
        if correction:
            self.fields['debut'].help_text = 'Date de l’information corrigée : elle reste inchangée.'
            self.fields['motif'].label = 'Pourquoi la saisie précédente était-elle erronée ?'
        else:
            self.fields['debut'].help_text = 'La situation précédente reste dans l’historique jusqu’à cette date.'
            self.fields['motif'].label = 'Explication de l’ajout dans le passé (si nécessaire)'
            self.fields['motif'].help_text = 'À remplir seulement si une situation plus récente est déjà enregistrée pour cette rubrique.'


def objet_dossier(request, nature, pk):
    suivi.exiger(request.user, 'view_personne')
    if nature == 'menage':
        suivi.exiger(request.user, 'view_menage')
    elif nature != 'personne':
        from django.http import Http404
        raise Http404
    return get_object_or_404(Menage if nature == 'menage' else Personne, pk=pk)


def parametres_retour(request):
    from .vues_dossiers import parametres
    return {**parametres(request), **{k: request.GET.get(k, '')[:40] for k in
        ('prise', 'sejour', 'repas', 'origine_menage', 'origine_sejour', 'origine_repas', 'date_service')}}


def retour(nature, pk, params=None, prise=None):
    nom = 'dossiers:prise' if prise else 'dossiers:detail'
    args = [nature, pk, prise.pk] if prise else [nature, pk]
    return reverse(nom, args=args) + ('?' + urlencode(params) if params else '')


def traiter(request, form, titre, action, url, objet, **contexte):
    statut = 200
    if request.method == 'POST' and form.is_valid():
        try:
            resultat = action(**form.cleaned_data)
        except (ValidationError, OperationalError) as erreur:
            if isinstance(erreur, ValidationError) and hasattr(erreur, 'error_dict'):
                for champ, messages in erreur.message_dict.items():
                    form.add_error(champ if champ in form.fields else None, messages)
            else:
                form.add_error(None, ' '.join(erreur.messages) if isinstance(erreur, ValidationError) else 'Écriture non confirmée. Rechargez avant de réessayer.')
            statut = 409
        else:
            return redirect(url(resultat) if callable(url) else url)
    return render(request, 'dossiers/form_bd6.html', {'form': form, 'titre': titre, 'objet': objet,
        'retour': url if isinstance(url, str) else contexte.pop('annuler', ''), **contexte}, status=statut)


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(dossier.DROITS, raise_exception=True)
def nouvelle(request, nature, pk):
    objet = objet_dossier(request, nature, pk)
    suivi.exiger(request.user, 'add_accompagnement')
    jour = timezone.localdate()
    initial = {'debut': jour, 'attendu': ouverture_prise.jeton(objet),
        'beneficiaires': [pk] if nature == 'personne' else list(objet.appartenances.filter(debut__lte=jour).filter(Q(fin__isnull=True) | Q(fin__gt=jour)).values_list('personne_id', flat=True))}
    if nature == 'personne':
        menages = list(ouverture_prise.menages_personne(objet))
        initial.update(rattachement='existant' if menages else 'nouveau',
            libelle_menage=str(objet), menage=menages[0] if len(menages) == 1 else None)
        form = PremierePriseForm(request.POST if request.method == 'POST' else None,
            initial=initial, acteur=request.user, personne=objet)
    else:
        form = AccompagnementForm(request.POST if request.method == 'POST' else None, initial=initial)
        form.fields['attendu'] = forms.CharField(widget=forms.HiddenInput, initial=initial['attendu'])
        form.fields['beneficiaires'].queryset = Personne.objects.filter(appartenances__menage=objet).distinct()
    def action(**d):
        nouveau = d.pop('rattachement', 'existant') == 'nouveau'
        menage = d.pop('menage', objet if nature == 'menage' else None)
        return ouverture_prise.ouvrir(request.user, objet, menage=menage, creer_menage=nouveau, **d)
    return traiter(request, form, 'Nouvelle prise en charge', action,
        lambda a: retour(nature, pk, parametres_retour(request), prise=a), objet, annuler=retour(nature, pk, parametres_retour(request)),
        explication='Choisissez les bénéficiaires et la prévision. Aucune prestation n’est créée automatiquement.')


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(dossier.DROITS, raise_exception=True)
def corriger_prevision(request, nature, pk, prise_pk):
    objet = objet_dossier(request, nature, pk)
    a = get_object_or_404(objet.accompagnements, pk=prise_pk)
    suivi.exiger(request.user, 'corriger_prevision_accompagnement', 'view_evolutionpriseencharge')
    form = PrevisionForm(request.POST if request.method == 'POST' else None,
        initial={'attendu': bd6.jeton(a), 'fin_prevue': a.fin_prevue})
    form.fields['fin_prevue'].required = False
    form.fields['fin_prevue'].help_text = 'Laissez vide pour retirer une prévision saisie par erreur. La clôture effective et les prestations restent inchangées.'
    return traiter(request, form, 'Corriger une erreur de fin prévue',
        lambda **d: bd6.corriger_prevision(request.user, a, **d),
        retour(nature, pk, parametres_retour(request), prise=a), objet,
        explication='Ce formulaire rectifie une erreur. Pour une nouvelle décision accordant plus de temps, utilisez Prolonger.')


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(dossier.DROITS, raise_exception=True)
def clore(request, nature, pk, prise_pk):
    objet = objet_dossier(request, nature, pk)
    a = get_object_or_404(objet.accompagnements, pk=prise_pk)
    suivi.exiger(request.user, 'change_accompagnement')
    from .forms_suivi import ClotureForm
    form = ClotureForm(request.POST if request.method == 'POST' else None, initial={'fin': timezone.localdate()})
    form.fields['attendu'] = forms.CharField(widget=forms.HiddenInput, initial=bd6.jeton(a))
    return traiter(request, form, 'Clôturer la prise en charge', lambda **d: bd6.clore_prise(request.user, a, **d),
        retour(nature, pk, parametres_retour(request), prise=a), objet,
        explication='Indiquez le premier jour hors prise en charge. Les séjours doivent être clos au préalable ; aucun accord ni fait réalisé n’est modifié automatiquement.')


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(dossier.DROITS, raise_exception=True)
def prolonger(request, nature, pk, prise_pk):
    objet = objet_dossier(request, nature, pk)
    a = get_object_or_404(objet.accompagnements, pk=prise_pk)
    suivi.exiger(request.user, 'prolonger_accompagnement', 'view_evolutionpriseencharge')
    form = PrevisionForm(request.POST if request.method == 'POST' else None, initial={'attendu': bd6.jeton(a), 'fin_prevue': a.fin_prevue})
    return traiter(request, form, 'Prolonger la prise en charge', lambda **d: bd6.prolonger(request.user, a, **d),
        retour(nature, pk, parametres_retour(request), prise=a), objet, explication='Seule la fin prévue change. Les accords et séjours gardent leurs dates.')


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(('personnes.view_commentairedossier', 'personnes.add_commentairedossier'), raise_exception=True)
def commentaire(request, nature, pk, prise_pk=None):
    objet = objet_dossier(request, nature, pk)
    a = None
    if prise_pk:
        suivi.exiger(request.user, 'view_accompagnement')
        a = get_object_or_404(objet.accompagnements, pk=prise_pk)
    cible = a or objet
    # Réserver l’état lu avant le contenu : une écriture entre les deux rendra
    # le formulaire périmé, jamais un ancien texte accompagné d’un jeton neuf.
    attendu = bd6.jeton(cible)
    versions = CommentaireDossier.objects.filter(**bd6.cible_commentaire(cible)).select_related('auteur')
    premiere = versions.first()
    form = CommentaireForm(request.POST if request.method == 'POST' else None,
        initial={'attendu': attendu, 'texte': tr.lire_objet(premiere, 'texte') if premiere else ''})
    return traiter(request, form, 'Commentaire de la prise en charge' if a else 'Commentaire du dossier',
        lambda **d: bd6.commenter(request.user, cible, **d), retour(nature, pk, parametres_retour(request), prise=a), objet, versions=versions)


def navigation_histoire(request, personne):
    pk = personne.pk
    params = parametres_retour(request)
    origine = {k: request.GET.get(k, '')[:40] for k in ('depuis_nature', 'depuis_pk', 'depuis_prise')}
    retour_social = retour('personne', pk, params)
    from .vues_suivi import _uuid_valide
    if origine['depuis_nature'] == 'menage' and _uuid_valide(origine['depuis_pk']) and request.user.has_perm('personnes.view_menage'):
        menage = Menage.objects.filter(pk=origine['depuis_pk']).first()
        prise_origine = Accompagnement.objects.filter(pk=origine['depuis_prise'], menage=menage, beneficiaires=personne).first() if _uuid_valide(origine['depuis_prise']) and request.user.has_perms(dossier.DROITS) else None
        if menage and (menage.appartenances.filter(personne=personne).exists() or prise_origine):
            retour_social = retour('menage', menage.pk, params, prise=prise_origine)
    elif origine['depuis_nature'] == 'personne' and origine['depuis_pk'] == str(pk) and _uuid_valide(origine['depuis_prise']) and request.user.has_perms(dossier.DROITS):
        prise_origine = personne.accompagnements.filter(pk=origine['depuis_prise']).first()
        if prise_origine:
            retour_social = retour('personne', pk, params, prise=prise_origine)
    query_sociale = urlencode({**params, **origine})
    return params, origine, retour_social, query_sociale


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(('personnes.view_personne', 'personnes.view_situationpersonnelle', 'personnes.view_revisionsituationpersonnelle'), raise_exception=True)
def social(request, pk, dimension=None, fait_pk=None):
    personne = get_object_or_404(Personne, pk=pk)
    params, origine, retour_social, query_sociale = navigation_histoire(request, personne)
    attendu = bd6.jeton(personne)
    faits = personne.situations_personnelles.select_related('auteur').order_by('-debut', '-pk')
    if dimension is None:
        date = timezone.localdate()
        consultation = forms.Form(request.GET if 'date' in request.GET else None)
        consultation.fields['date'] = date_champ('Situation à la date du')
        consultation.fields['date'].initial = date
        if 'date' in request.GET and consultation.is_valid():
            date = consultation.cleaned_data['date']
        return render(request, 'dossiers/social_personne.html', {'objet': personne, 'etat_social': bd6.etat(request.user, [personne], date),
            'anciens': SituationSociale.objects.filter(beneficiaire=personne).select_related('accompagnement') if request.user.has_perms([*dossier.DROITS, 'personnes.view_situationsociale']) else [],
            'faits': faits, 'date_situation': date, 'consultation': consultation, 'dimensions': SituationSociale.DIMENSIONS,
            'revisions': personne.revisionsituationpersonnelle_set.select_related('auteur', 'situation'),
            'parametres_sociaux': {**params, **origine}, 'query_sociale': query_sociale, 'retour': retour_social})
    suivi.exiger(request.user, 'add_situationpersonnelle')
    if dimension not in dict(SituationSociale.DIMENSIONS):
        from django.http import Http404
        raise Http404
    fait = get_object_or_404(faits, pk=fait_pk, dimension=dimension) if fait_pk else None
    if fait:
        suivi.exiger(request.user, 'change_situationpersonnelle')
    initial = {'attendu': attendu, 'debut': fait.debut if fait else timezone.localdate(),
        'valeur': fait.valeur if fait else None, 'source': fait.source if fait else ''}
    form = SituationForm(request.POST if request.method == 'POST' else None, dimension=dimension, correction=bool(fait), initial=initial)
    return traiter(request, form, ('Corriger une erreur — ' if fait else 'Enregistrer un changement — ') + dict(SituationSociale.DIMENSIONS)[dimension],
        lambda **d: bd6.renseigner(request.user, personne, dimension, correction=fait.pk if fait else None, **d),
        reverse('dossiers:social', args=[pk]) + '?' + query_sociale, personne,
        explication=('Vous corrigez une erreur de saisie dans une information déjà enregistrée. Choisissez la bonne valeur et expliquez l’erreur. Sa date reste inchangée ; la correction est conservée dans le journal.' if fait else
            'Vous enregistrez une situation nouvelle ou encore inconnue du dossier. Indiquez depuis quand elle est vraie. Exemple : reprise d’un emploi le 1er octobre. Si une information déjà saisie était fausse, revenez en arrière et choisissez « Corriger une erreur » sur cette information.'))


class MembreForm(EtatForm):
    debut = date_champ('Début de l’appartenance inclus')
    designation = forms.CharField(label='Nom ou désignation', max_length=160, required=False)
    prenom = forms.CharField(label='Prénom', max_length=100, required=False)


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required(('personnes.view_personne', 'personnes.view_menage', 'personnes.add_appartenance'), raise_exception=True)
def membre(request, pk):
    menage = get_object_or_404(Menage, pk=pk)
    token = request.GET.get('contexte_composition', '')
    try:
        contexte = signing.loads(token, salt='bd6-composition', max_age=86400)
        if contexte.get('menage') != str(pk):
            raise signing.BadSignature
        params = contexte['params']
    except (signing.BadSignature, TypeError, ValueError, AttributeError, KeyError):
        params = parametres_retour(request)
        token = signing.dumps({'menage': str(pk), 'params': params}, salt='bd6-composition', compress=True)
    retour_menage = retour('menage', pk, params)
    q = request.GET.get('q', '')[:160].strip()
    identifiant = request.GET.get('personne', '')
    nouvelle = request.GET.get('nouvelle') == '1'
    personne = get_object_or_404(Personne, pk=identifiant) if identifiant else None
    if nouvelle:
        suivi.exiger(request.user, 'add_personne')
    if personne or nouvelle:
        form = MembreForm(request.POST if request.method == 'POST' else None,
            initial={'attendu': bd6.jeton(menage), 'debut': timezone.localdate(), 'designation': q})
        if personne:
            del form.fields['designation']; del form.fields['prenom']
        else:
            form.fields['designation'].required = True
        return traiter(request, form, 'Ajouter au ménage — ' + (str(personne) if personne else 'nouvelle personne'),
            lambda **d: bd6.ajouter_membre(request.user, menage, personne=personne, **d), retour_menage, menage,
            explication='Confirmez l’identité et la date d’appartenance. Les bénéficiaires des prises en charge existantes ne sont pas modifiés.')
    personnes = Personne.objects.all()
    for mot in q.split():
        personnes = personnes.filter(Q(designation__icontains=mot) | Q(prenom__icontains=mot))
    page = Paginator(personnes.order_by('designation', 'prenom', 'pk'), 25).get_page(request.GET.get('page'))
    contexte = {'objet': menage, 'page_obj': page, 'recherche': q, 'contexte_composition': token, 'retour': retour_menage}
    return render(request, 'dossiers/membres_resultats.html' if request.GET.get('fragment') == '1' else 'dossiers/membre.html', contexte)
