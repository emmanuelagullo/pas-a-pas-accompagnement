"""Entrée et synthèse personne/ménage ; aucun nouvel objet métier « dossier »."""
from urllib.parse import urlencode

from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe

from . import dossier, suivi
from .forms import PersonneForm
from .models import Personne, Menage, Appartenance, Accompagnement, Sejour, AccordRepas, AccordHebergement, Affectation, Absence, InformationsAccompagnement
from .lecture_dossier import choisir


def recherche(request):
    """Appelé après connexion et vérification de l'installation par l'accueil."""
    peut_personnes = request.user.has_perm('personnes.view_personne')
    peut_menages = peut_personnes and request.user.has_perm('personnes.view_menage')
    mode = 'personne' if request.GET.get('mode') == 'personne' or not peut_menages else 'menage'
    q = request.GET.get('q', '')[:160].strip()
    objets = Personne.objects.none()
    if peut_personnes:
        objets = Menage.objects.all() if mode == 'menage' else Personne.objects.all()
        for mot in q.split():
            if mode == 'menage':
                # Une sous-requête par terme : plusieurs personnes peuvent satisfaire les termes.
                liens = Appartenance.objects.filter(Q(personne__designation__icontains=mot) | Q(personne__prenom__icontains=mot))
                objets = objets.filter(Q(libelle__icontains=mot) | Q(pk__in=liens.values('menage_id')))
            else:
                objets = objets.filter(Q(designation__icontains=mot) | Q(prenom__icontains=mot))
        if mode == 'menage':
            objets = objets.prefetch_related(Prefetch('appartenances', queryset=Appartenance.objects.select_related('personne').order_by('debut', 'pk')))
        objets = objets.order_by('libelle', 'pk') if mode == 'menage' else objets.order_by('designation', 'prenom', 'pk')
    page = Paginator(objets, 25).get_page(request.GET.get('page'))
    jour = timezone.localdate()
    for objet in page:
        if mode == 'menage':
            liens = list(objet.appartenances.all())
            objet.nombre_actuel = len({l.personne_id for l in liens if l.debut <= jour and (l.fin is None or l.fin > jour)})
            objet.correspondances = [l for l in liens if q and any(m.casefold() in str(l.personne).casefold() for m in q.split())]
        objet.url_dossier = reverse('dossiers:detail', args=[mode, objet.pk]) + '?' + urlencode({'q': q, 'mode': mode, 'page': page.number})
    creation = peut_personnes and request.user.has_perm('personnes.add_personne')
    if mode == 'menage':
        creation = peut_menages and request.user.has_perms(['personnes.add_menage', 'personnes.add_appartenance'])
    contexte = {'mode': mode, 'recherche': q, 'page_obj': page, 'peut_menages': peut_menages,
                'peut_personnes': peut_personnes, 'peut_creer': creation}
    template = 'dossiers/resultats.html' if request.GET.get('fragment') == '1' else 'accueil.html'
    return render(request, template, contexte)


class NouveauMenageForm(forms.Form):
    libelle = forms.CharField(label='Libellé du ménage', max_length=160)
    premiere_personne = forms.ChoiceField(label='Première personne', choices=[('existante', 'Choisir une personne existante'), ('nouvelle', 'Créer une personne')])
    personne = forms.ModelChoiceField(Personne.objects.all(), required=False, label='Personne existante')
    designation = forms.CharField(label='Nom ou désignation de la nouvelle personne', max_length=160, required=False)
    prenom = forms.CharField(label='Prénom de la nouvelle personne', max_length=100, required=False)
    debut = forms.DateField(label='Début de son appartenance au ménage', widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))

    def __init__(self, *args, acteur, **kwargs):
        self.acteur = acteur
        super().__init__(*args, **kwargs)
        if not acteur.has_perm('personnes.add_personne'):
            self.fields['premiere_personne'].choices = [('existante', 'Choisir une personne existante')]

    def clean(self):
        d = super().clean()
        if d.get('premiere_personne') == 'existante' and not d.get('personne'):
            self.add_error('personne', 'Choisissez la personne à rattacher.')
        if d.get('premiere_personne') == 'nouvelle':
            if not self.acteur.has_perm('personnes.add_personne'):
                self.add_error(None, 'La création de personne nécessite un droit explicite.')
            else:
                p = Personne(designation=d.get('designation', ''), prenom=d.get('prenom', ''), cree_par=self.acteur)
                try:
                    p.full_clean()
                except ValidationError as erreur:
                    self.add_error(None, ' '.join(erreur.messages))
        return d


def parametres(request):
    return {'q': request.GET.get('q', '')[:160], 'mode': 'personne' if request.GET.get('mode') == 'personne' else 'menage',
            'page': request.GET.get('page', '1')[:8]}


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
@permission_required('personnes.view_personne', raise_exception=True)
def creer(request, nature):
    if nature not in ('menage', 'personne'):
        from django.http import Http404
        raise Http404
    if nature == 'menage':
        suivi.exiger(request.user, 'view_menage', 'add_menage', 'add_appartenance')
        form = NouveauMenageForm(request.POST if request.method == 'POST' else None, acteur=request.user,
            initial={'libelle': request.GET.get('q', '')[:160], 'debut': timezone.localdate(), 'premiere_personne': 'existante'})
    else:
        suivi.exiger(request.user, 'add_personne')
        form = PersonneForm(request.POST if request.method == 'POST' else None, initial={'designation': request.GET.get('q', '')[:160]})
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            if nature == 'personne':
                objet = form.save(commit=False)
                objet.cree_par = request.user
                objet.save()
            else:
                d = form.cleaned_data
                p = d['personne']
                if d['premiere_personne'] == 'nouvelle':
                    p = Personne.objects.create(designation=d['designation'], prenom=d['prenom'], cree_par=request.user)
                objet = suivi.creer_menage(request.user, d['libelle'], [p], d['debut'])
        return redirect(reverse('dossiers:detail', args=[nature, objet.pk]) + '?' + urlencode(parametres(request)))
    return render(request, 'dossiers/creer.html', {'form': form, 'nature': nature,
        'retour': reverse('accueil') + '?' + urlencode(parametres(request))})


@never_cache
@require_safe
@login_required
@permission_required('personnes.view_personne', raise_exception=True)
def detail(request, nature, pk):
    if nature == 'menage':
        suivi.exiger(request.user, 'view_menage')
        objet = get_object_or_404(Menage, pk=pk)
        liens = list(objet.appartenances.select_related('personne').order_by('-debut', 'pk'))
        periodes = objet.accompagnements.all()
    elif nature == 'personne':
        objet = get_object_or_404(Personne, pk=pk)
        liens = list(objet.appartenances.select_related('menage').order_by('-debut', 'pk')) if request.user.has_perm('personnes.view_menage') else []
        periodes = objet.accompagnements.all()
    else:
        from django.http import Http404
        raise Http404
    jour = timezone.localdate()
    anciens = dossier.valeurs_vue(request, nature, pk)
    params = {**parametres(request), **anciens}
    for cle in ('sejour', 'repas', 'origine_menage', 'origine_sejour', 'origine_repas'):
        if cle in request.GET:
            params[cle] = request.GET[cle][:40]
    origine = next((l.menage for l in liens if nature == 'personne' and str(l.menage_id) == params.get('origine_menage')), None)
    # Un bénéficiaire peut être suivi indépendamment de ses appartenances.
    if nature == 'personne' and origine is None and request.user.has_perms(dossier.DROITS):
        origine = Menage.objects.filter(pk__in=periodes.values('menage_id')).filter(pk=params.get('origine_menage')).first() if suivi_uuid(params.get('origine_menage')) else None
    params['origine_menage'] = str(origine.pk) if origine else ''
    droits_suivi = request.user.has_perms(dossier.DROITS)
    if request.user.has_perm('personnes.view_informationsaccompagnement'):
        periodes = periodes.prefetch_related(Prefetch('informations', queryset=InformationsAccompagnement.objects.select_related('auteur'), to_attr='informations_dossier'))
    periodes = list(periodes.select_related('menage').prefetch_related('beneficiaires').order_by('-debut', 'pk')) if droits_suivi else []
    h = request.user.has_perms(['personnes.view_accordhebergement', 'personnes.view_sejour']) and droits_suivi
    r = request.user.has_perms(['personnes.view_accordrepas', 'personnes.view_repasdistribue']) and droits_suivi
    lieux = request.user.has_perms(['personnes.view_affectation', 'personnes.view_lieuhebergement'])
    sejours, accords_h, accords_r = [], [], []
    if h:
        accords = Sejour.objects.filter(accord__accompagnement__in=periodes).select_related('accord__accompagnement').prefetch_related('beneficiaires')
        seuls = AccordHebergement.objects.filter(accompagnement__in=periodes, sejours__isnull=True).prefetch_related('beneficiaires')
        if nature == 'personne':
            accords = accords.filter(beneficiaires=objet)
            seuls = seuls.filter(beneficiaires=objet)
        if lieux:
            accords = accords.prefetch_related(Prefetch('affectations', queryset=Affectation.objects.select_related('lieu').order_by('-debut', '-pk'), to_attr='lieux_dossier'))
        if request.user.has_perm('personnes.view_absence'):
            accords = accords.prefetch_related(Prefetch('absences', queryset=Absence.objects.order_by('-debut', '-pk'), to_attr='absences_dossier'))
        sejours = list(accords)
        sejours.sort(key=lambda s: (s.fin is not None, -s.debut.toordinal(), str(s.pk)))
        for s in sejours:
            s.lieu_ouvert = next((x for x in getattr(s, 'lieux_dossier', []) if x.fin is None), None)
            s.absence_ouverte = next((x for x in getattr(s, 'absences_dossier', []) if x.fin is None), None)
        accords_h = list(seuls.order_by('-debut', 'pk'))
    if r:
        accords = AccordRepas.objects.filter(accompagnement__in=periodes).select_related('accompagnement', 'annule_par').prefetch_related('beneficiaires')
        if nature == 'personne':
            accords = accords.filter(beneficiaires=objet)
        accords_r = list(accords)
        accords_r.sort(key=lambda a: (a.annule_le is not None, -a.debut.toordinal(), str(a.pk)))
    selection_h = choisir(sejours, params.get('sejour', ''))
    selection_r = choisir(accords_r, params.get('repas', ''))
    params.update(sejour=str(selection_h.pk) if selection_h else '', repas=str(selection_r.pk) if selection_r else '')
    # Chaque boîte signe le vrai parent de sa sélection, jamais le premier suivi arbitraire.
    nav_h = dossier.pour_vue(request, selection_h.accord.accompagnement, nature, pk, params) if selection_h else {}
    nav_r = dossier.pour_vue(request, selection_r.accompagnement, nature, pk, params) if selection_r else {}
    for accord in accords_h:
        accord.navigation = dossier.pour_vue(request, next(a for a in periodes if a.pk == accord.accompagnement_id), nature, pk, params)
    for a in periodes:
        a.navigation = dossier.pour_vue(request, a, nature, pk, params)
    liens_uniques = {}
    for lien in liens:
        lien.actuel = lien.debut <= jour and (lien.fin is None or lien.fin > jour)
        cible = lien.personne if nature == 'menage' else lien.menage
        cle = str(cible.pk)
        if cle not in liens_uniques:
            lien.cible = cible
            lien.url = reverse('dossiers:detail', args=['personne' if nature == 'menage' else 'menage', cible.pk]) + '?' + urlencode({**params, 'origine_menage': str(pk) if nature == 'menage' else '', **({'origine_sejour': params['sejour'], 'origine_repas': params['repas']} if nature == 'menage' else {})})
            liens_uniques[cle] = lien
    retour = reverse('accueil') + '?' + urlencode({k: params[k] for k in ('q', 'mode', 'page')})
    origine_url = reverse('dossiers:detail', args=['menage', origine.pk]) + '?' + urlencode({**params, 'sejour': params.get('origine_sejour', params['sejour']), 'repas': params.get('origine_repas', params['repas'])}) if origine else ''
    return render(request, 'dossiers/detail.html', {'objet': objet, 'nature': nature, 'liens': liens, 'liens_uniques': liens_uniques.values(),
        'navigation_personne': dossier.pour_personne(pk, params) if nature == 'personne' else {}, 'origine_url': origine_url, 'origine': origine, 'retour': retour, 'navigation_query': urlencode(params), 'recherche': params['q'], 'mode_recherche': params['mode'], 'page_recherche': params['page'], 'origine_sejour': params.get('origine_sejour', ''), 'origine_repas': params.get('origine_repas', ''),
        'periodes': periodes, 'aujourdhui': jour, 'lecture_hebergement': h, 'lecture_repas': r, 'lecture_lieux': lieux,
        'sejours_dossier': sejours, 'accords_sans_sejour': accords_h, 'accords_repas': accords_r,
        'selection_sejour': selection_h, 'selection_repas': selection_r, 'navigation_h': nav_h, 'navigation_r': nav_r})


def suivi_uuid(valeur):
    from .vues_suivi import _uuid_valide
    return _uuid_valide(valeur)


@never_cache
@require_safe
@login_required
def transferts(request):
    from django.conf import settings
    return render(request, 'dossiers/transferts.html', {'mode_pwa': getattr(settings, 'MODE_PWA', False)})


@never_cache
@require_safe
@login_required
@permission_required(dossier.DROITS, raise_exception=True)
def choisir_periode(request, nature, pk, prestation):
    """Choix explicite avant une nouvelle prestation, sans création implicite de suivi."""
    routes = {'hebergement': ('suivi:accorder_hebergement', 'add_accordhebergement'),
              'admission': ('suivi:admission_guidee', 'add_accordhebergement'),
              'repas': ('suivi:accorder_repas', 'add_accordrepas'),
              'services_repas': ('suivi:accorder_services_repas', 'add_accordrepas')}
    from django.http import Http404
    if prestation not in routes or nature not in ('menage', 'personne'):
        raise Http404
    route, droit = routes[prestation]
    suivi.exiger(request.user, droit)
    if prestation == 'admission':
        suivi.exiger(request.user, 'add_sejour', 'view_accordhebergement', 'view_sejour')
    elif prestation == 'hebergement':
        suivi.exiger(request.user, 'view_accordhebergement', 'view_sejour')
    else:
        suivi.exiger(request.user, 'view_accordrepas')
    objet = get_object_or_404(Menage if nature == 'menage' else Personne, pk=pk)
    periodes = objet.accompagnements.select_related('menage').prefetch_related('beneficiaires').order_by('-debut', 'pk')
    params = {**parametres(request), **{k: request.GET.get(k, '')[:40] for k in ('sejour', 'repas', 'origine_menage', 'origine_sejour', 'origine_repas')}}
    for a in periodes:
        a.url_action = reverse(route, args=[a.pk]) + '?' + urlencode({'contexte_dossier': dossier.pour_vue(request, a, nature, pk, params)['contexte_dossier']})
    return render(request, 'dossiers/choisir.html', {'objet': objet, 'nature': nature, 'periodes': periodes, 'prestation': prestation,
        'retour': reverse('dossiers:detail', args=[nature, pk]) + '?' + urlencode(params)})
