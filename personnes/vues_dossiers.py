"""Entrée et synthèse personne/ménage ; aucun nouvel objet métier « dossier »."""
from urllib.parse import urlencode
from datetime import timedelta
from collections import defaultdict

from django import forms
from .champs_saisie import FormulaireMetier
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

from . import dossier, suivi, bd6
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
    from acteurs import politique as politique_acces
    from acteurs.contexte import courant
    controle_actif = politique_acces.active()
    filtre_acteurs = request.GET.get('filtre', 'tous')
    if filtre_acteurs not in ('tous','mes','service','attente'):filtre_acteurs='tous'
    if controle_actif:
        from acteurs.recherche import classer
        objets=classer(request.user,objets,mode,filtre_acteurs,courant().service_id if courant() else None)
    page = Paginator(objets, 25).get_page(request.GET.get('page'))
    jour = timezone.localdate()
    for objet in page:
        if mode == 'menage':
            liens = list(objet.appartenances.all())
            objet.nombre_actuel = len({l.personne_id for l in liens if l.debut <= jour and (l.fin is None or l.fin > jour)})
            objet.correspondances = [l for l in liens if q and any(m.casefold() in str(l.personne).casefold() for m in q.split())]
        objet.url_dossier = reverse('dossiers:detail', args=[mode, objet.pk]) + '?' + urlencode({'q': q, 'mode': mode, 'page': page.number, 'filtre':filtre_acteurs})
    creation = peut_personnes and request.user.has_perm('personnes.add_personne')
    if mode == 'menage':
        creation = peut_menages and request.user.has_perms(['personnes.add_menage', 'personnes.add_appartenance'])
    contexte = {'mode': mode, 'recherche': q, 'page_obj': page, 'peut_menages': peut_menages,
                'peut_personnes': peut_personnes, 'peut_creer': creation, 'controle_acteurs':controle_actif, 'filtre_acteurs':filtre_acteurs}
    template = 'dossiers/resultats.html' if request.GET.get('fragment') == '1' else 'accueil.html'
    return render(request, template, contexte)


class NouveauMenageForm(FormulaireMetier):
    libelle = forms.CharField(label='Libellé du ménage', max_length=160, help_text='Nom court affiché dans la recherche. Il ne désigne ni un chef de famille ni une responsabilité juridique.')
    premiere_personne = forms.ChoiceField(label='Première personne', choices=[('existante', 'Choisir une personne existante'), ('nouvelle', 'Créer une personne')])
    personne = forms.ModelChoiceField(Personne.objects.all(), required=False, label='Personne existante', help_text='À renseigner seulement si vous choisissez une personne existante. Ses autres appartenances sont conservées.')
    designation = forms.CharField(label='Nom ou désignation de la nouvelle personne', max_length=160, required=False, help_text='Obligatoire pour créer la première personne : le libellé du ménage ne remplace pas son identité.')
    prenom = forms.CharField(label='Prénom de la nouvelle personne', max_length=100, required=False, help_text='Facultatif ; ne pas inventer un prénom pour compléter le formulaire.')
    debut = forms.DateField(label='Début de son appartenance au ménage', widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}), help_text='Premier jour de cette appartenance ; aucune prestation ni période de suivi n’est ouverte par cette date.')

    def __init__(self, *args, acteur, **kwargs):
        self.acteur = acteur
        super().__init__(*args, **kwargs)
        if self.is_bound and self.data.get('premiere_personne') == 'nouvelle':
            self.fields['personne'].disabled = True
        if not acteur.has_perm('personnes.add_personne'):
            self.fields['premiere_personne'].choices = [('existante', 'Choisir une personne existante')]

    def clean(self):
        d = super().clean()
        if d.get('premiere_personne') == 'existante' and not d.get('personne'):
            self.add_error('personne', 'Choisissez la personne à rattacher.')
        if d.get('premiere_personne') == 'nouvelle':
            if not self.acteur.has_perm('personnes.add_personne'):
                self.add_error(None, 'La création de personne nécessite un droit explicite.')
            elif not d.get('designation'):
                if 'designation' not in self.errors:
                    self.add_error('designation', 'Indiquez le nom ou la désignation de la nouvelle personne.')
            else:
                p = Personne(designation=d['designation'], prenom=d.get('prenom', ''), cree_par=self.acteur)
                try:
                    p.full_clean()
                except ValidationError as erreur:
                    if hasattr(erreur, 'error_dict'):
                        for champ, messages in erreur.message_dict.items():
                            self.add_error(champ if champ in self.fields else None,
                                messages if champ in self.fields else [f'Nouvelle personne : {message}' for message in messages])
                    else:
                        self.add_error(None, erreur)

        return d


def parametres(request):
    return {'q': request.GET.get('q', '')[:160], 'mode': 'personne' if request.GET.get('mode') == 'personne' else 'menage',
            'page': request.GET.get('page', '1')[:8], 'filtre':request.GET.get('filtre','tous')[:12], 'retour_exploration':request.GET.get('retour_exploration','')[:20000]}


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
def detail(request, nature, pk, prise_pk=None):
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
    prise = get_object_or_404(periodes, pk=prise_pk) if prise_pk and request.user.has_perms(dossier.DROITS) else None
    if prise_pk and prise is None:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    if prise:
        periodes = periodes.filter(pk=prise.pk)
    jour = timezone.localdate()
    anciens = dossier.valeurs_vue(request, nature, pk)
    params = {**parametres(request), **anciens}
    for cle in ('sejour', 'repas', 'origine_menage', 'origine_sejour', 'origine_repas', 'prise', 'date_service', 'prevision', *dossier.CLES_SOCIALES):
        if cle in request.GET:
            params[cle] = request.GET[cle][:40]
    from . import condition_sociale
    condition_vue, condition_jour = condition_sociale.selection(request, prise, params)
    if 'vue_sociale' in request.GET:
        params['origines_sociales'] = '1' if request.GET.get('origines_sociales') == '1' else ''
    params.update(vue_sociale=condition_vue, date_sociale=condition_jour.isoformat(),
                  presentation_sociale=request.GET.get('presentation_sociale') or params.get('presentation_sociale') or 'integrale')
    origine = next((l.menage for l in liens if nature == 'personne' and str(l.menage_id) == params.get('origine_menage')), None)
    # Un bénéficiaire peut être suivi indépendamment de ses appartenances.
    if nature == 'personne' and origine is None and request.user.has_perms(dossier.DROITS):
        origine = Menage.objects.filter(pk__in=periodes.values('menage_id')).filter(pk=params.get('origine_menage')).first() if suivi_uuid(params.get('origine_menage')) else None
    params['origine_menage'] = str(origine.pk) if origine else ''
    droits_suivi = request.user.has_perms(dossier.DROITS)
    if request.user.has_perm('personnes.view_informationsaccompagnement'):
        periodes = periodes.prefetch_related(Prefetch('informations', queryset=InformationsAccompagnement.objects.select_related('auteur'), to_attr='informations_dossier'))
    periodes = list(periodes.select_related('menage').prefetch_related('beneficiaires').order_by('-debut', 'pk')) if droits_suivi else []
    if prise:
        prise = next(a for a in periodes if a.pk == prise.pk)
    h = request.user.has_perms(['personnes.view_accordhebergement', 'personnes.view_sejour']) and droits_suivi
    r = request.user.has_perms(['personnes.view_accordrepas', 'personnes.view_repasdistribue']) and droits_suivi
    lieux = request.user.has_perms(['personnes.view_affectation', 'personnes.view_lieuhebergement'])
    arrivees_annulees=[]
    sejours, accords_h, accords_r, prevus = [], [], [], []
    if h:
        accords = Sejour.objects.non_annules().filter(accord__accompagnement__in=periodes).select_related('accord__accompagnement').prefetch_related('beneficiaires')
        seuls = AccordHebergement.objects.filter(accompagnement__in=periodes).prefetch_related('beneficiaires', Prefetch('sejours',queryset=Sejour.objects.non_annules().prefetch_related('beneficiaires'),to_attr='sejours_non_annules'))
        if nature == 'personne':
            accords = accords.filter(beneficiaires=objet)
            seuls = seuls.filter(beneficiaires=objet)
        if lieux:
            accords = accords.prefetch_related(Prefetch('affectations', queryset=Affectation.objects.select_related('lieu', 'lieu__organisme').order_by('-debut', '-pk'), to_attr='lieux_dossier'))
        if request.user.has_perm('personnes.view_absence'):
            accords = accords.prefetch_related(Prefetch('absences', queryset=Absence.objects.order_by('-debut', '-pk'), to_attr='absences_dossier'))
        sejours = list(accords)
        sejours.sort(key=lambda s: (s.fin is not None, -s.debut.toordinal(), str(s.pk)))
        for s in sejours:
            s.lieu_ouvert = next((x for x in getattr(s, 'lieux_dossier', []) if x.fin is None), None)
            s.absence_ouverte = next((x for x in getattr(s, 'absences_dossier', []) if x.fin is None), None)
        for accord in seuls.order_by('-debut', 'pk'):
            realises = accord.sejours_non_annules
            arrives = {p.pk for sejour in realises for p in sejour.beneficiaires.all()}
            accord.personnes_attendues = [p for p in accord.beneficiaires.all() if p.pk not in arrives and (nature == 'menage' or p.pk == objet.pk)]
            if accord.personnes_attendues and not accord.annule_le:
                prevus.append(accord)
            if not realises:
                accords_h.append(accord)
    if h and request.user.has_perm('personnes.view_annulationarrivee'):
        arrivees_annulees=Sejour.objects.filter(annule_le__isnull=False,origine_collective__isnull=True,accord__accompagnement__in=periodes).select_related('annule_par')
        if nature=='personne':arrivees_annulees=arrivees_annulees.filter(beneficiaires=objet)
    if r:
        accords = AccordRepas.objects.filter(accompagnement__in=periodes).select_related('accompagnement', 'annule_par').prefetch_related('beneficiaires')
        if nature == 'personne':
            accords = accords.filter(beneficiaires=objet)
        accords_r = list(accords)
        accords_r.sort(key=lambda a: (a.annule_le is not None, -a.debut.toordinal(), str(a.pk)))
    selection_h = choisir(sejours, params.get('sejour', ''))
    selection_r = choisir(accords_r, params.get('repas', ''))
    params.update(sejour=str(selection_h.pk) if selection_h else '', repas=str(selection_r.pk) if selection_r else '')
    params['prevision'] = next((str(x.pk) for x in prevus if str(x.pk) == params.get('prevision')), '')
    params['ecran'] = 'prise' if prise else 'dossier'
    if prise:
        params['prise'] = str(prise.pk)
        params['accompagnement'] = str(prise.pk)
    signer = dossier.pour_prise if prise else dossier.pour_vue
    # Chaque boîte signe le vrai parent de sa sélection, jamais le premier suivi arbitraire.
    nav_h = signer(request, selection_h.accord.accompagnement, nature, pk, params) if selection_h else {}
    nav_r = signer(request, selection_r.accompagnement, nature, pk, params) if selection_r else {}
    for accord in {x.pk: x for x in accords_h + prevus}.values():
        accord.navigation = signer(request, next(a for a in periodes if a.pk == accord.accompagnement_id), nature, pk, params)
    sejours_par_prise, repas_par_prise = defaultdict(list), defaultdict(list)
    for s in sejours:
        sejours_par_prise[s.accord.accompagnement_id].append(s)
    for r_accord in accords_r:
        repas_par_prise[r_accord.accompagnement_id].append(r_accord)
    for a in periodes:
        a.navigation = signer(request, a, nature, pk, params)
        a.url_prise = reverse('dossiers:prise', args=[nature, pk, a.pk]) + '?' + urlencode({k: v for k, v in params.items() if prise or k not in dossier.CLES_SOCIALES})
        a.url_prolonger = reverse('dossiers:prolonger_prise', args=[nature, pk, a.pk]) + '?' + urlencode(params)
        a.resume_prestations = bd6.resume_prestations(a, sejours_par_prise[a.pk], repas_par_prise[a.pk], jour, lieux)
        attendus = [x for x in prevus if x.accompagnement_id == a.pk]
        if attendus:
            libelle = 'Héberg. prévu — arrivée à confirmer' if any(x.fin is None or x.fin > jour for x in attendus) else 'Héberg. — arrivée non enregistrée'
            a.resume_prestations = (a.resume_prestations + ' · ' if a.resume_prestations != 'Aucune prestation consultable' else '') + libelle
    selection_prise = choisir(periodes, params.get('prise', ''))
    if not prise and selection_prise and request.GET.get('action') in ('ouvrir', 'prolonger', 'pdf'):
        action = request.GET['action']
        if params.get('prise') and str(selection_prise.pk) != params['prise']:
            from django.http import Http404
            raise Http404
        return redirect(selection_prise.url_prise if action == 'ouvrir' else selection_prise.url_prolonger if action == 'prolonger' else reverse('suivi:resume', args=[selection_prise.pk]) + '?' + urlencode({'contexte_dossier': selection_prise.navigation['contexte_dossier']}))
    liens_uniques = {}
    for lien in liens:
        lien.actuel = lien.debut <= jour and (lien.fin is None or lien.fin > jour)
        cible = lien.personne if nature == 'menage' else lien.menage
        cle = str(cible.pk)
        if cle not in liens_uniques:
            lien.cible = cible
            lien.url = reverse('dossiers:detail', args=['personne' if nature == 'menage' else 'menage', cible.pk]) + '?' + urlencode({**params, 'origine_menage': str(pk) if nature == 'menage' else '', **({'origine_sejour': params['sejour'], 'origine_repas': params['repas']} if nature == 'menage' else {})})
            liens_uniques[cle] = lien
    for s in sejours:
        s.selection_url = reverse('dossiers:prise', args=[nature, pk, prise.pk]) if prise else reverse('dossiers:detail', args=[nature, pk])
        s.selection_url = s.selection_url + '?' + urlencode({**params, 'sejour': str(s.pk)}) + '#hebergement'
    for accord in accords_r:
        accord.selection_url = reverse('dossiers:prise', args=[nature, pk, prise.pk]) if prise else reverse('dossiers:detail', args=[nature, pk])
        accord.selection_url = accord.selection_url + '?' + urlencode({**params, 'repas': str(accord.pk)}) + '#repas'
    courantes = [a for a in periodes if a.debut <= jour and (a.fin is None or a.fin > jour)]
    actuelle = courantes[0] if len(courantes) == 1 else None
    informations_actuelles = getattr(actuelle, 'informations_dossier', [])
    notes_actuelles = []
    if actuelle and request.user.has_perm('personnes.view_notepartagee'):
        from .models import NotePartagee
        notes_actuelles = NotePartagee.objects.filter(accompagnement=actuelle).select_related('auteur').order_by('-cree_le', '-pk')[:3]
    retour = reverse('accueil') + '?' + urlencode({k: params[k] for k in ('q', 'mode', 'page')})
    origine_url = reverse('dossiers:detail', args=['menage', origine.pk]) + '?' + urlencode({**params, 'vue_sociale': 'date' if condition_vue in ('entree', 'fin') else condition_vue, 'sejour': params.get('origine_sejour', params['sejour']), 'repas': params.get('origine_repas', params['repas'])}) if origine else ''
    personnes_sociales = list(prise.beneficiaires.all()) if prise else [objet] if nature == 'personne' else list({l.personne_id: l.personne for l in liens if l.debut <= condition_jour and (l.fin is None or l.fin > condition_jour)}.values())
    condition_personnes, condition_projets = condition_sociale.presentation(
        request, personnes_sociales, condition_jour, objet, nature, prise, params)
    date_sociale = prise.fin if prise and prise.fin else jour
    # La clôture est exclue : restituer le dernier jour de la prise.
    if prise and prise.fin:
        from datetime import timedelta
        date_sociale -= timedelta(days=1)
    from . import interventions
    lecture_interventions = request.user.has_perms(interventions.DROITS_LECTURE)
    interventions_courantes = interventions.presentation(request.user, prise, condition_jour) if prise and lecture_interventions else []
    from . import parcours
    demande_origine = prise.demande_accueil if prise and request.user.has_perms(parcours.droits('demandes')) and hasattr(prise,'demande_accueil') else None
    from .exploration_releve import retour_verifie
    retour_exploration=retour_verifie(request.user,params.get('retour_exploration'))
    commentaire_cible = prise or objet
    from . import contacts_menage
    contact_designe = contacts_menage.a_date([objet], condition_jour).first() if nature == 'menage' and request.user.has_perms(contacts_menage.DROITS_LECTURE) else None
    commentaires = commentaire_cible.commentaires_dossier.select_related('auteur') if request.user.has_perm('personnes.view_commentairedossier') else []
    return render(request, 'dossiers/prise.html' if prise else 'dossiers/detail.html', {
        'condition_personnes': condition_personnes, 'condition_projets': condition_projets,
        'condition_lecture': bd6.etat(request.user, personnes_sociales, condition_jour),
        'condition_documents': condition_sociale.documents(request.user, prise or objet),
        'condition_contextes': condition_sociale.contextes(request.user, personnes_sociales, objet),
        'condition_documents_url': reverse('dossiers:pieces', args=['accompagnement' if prise else nature, prise.pk if prise else pk]) + '?' + urlencode({'contexte_dossier': prise.navigation['contexte_dossier']} if prise else params),
        'condition_vue': condition_vue, 'condition_jour': condition_jour,
        'condition_dernier_jour': prise.fin - timedelta(days=1) if prise and prise.fin else None,
        'condition_integrale': params.get('presentation_sociale') != 'synthese',
        'condition_origines': params.get('origines_sociales') == '1',
        'condition_composition': [l for l in liens if l.debut <= condition_jour and (l.fin is None or l.fin > condition_jour)],
        'prise': prise, 'demande_origine':demande_origine, 'lecture_interventions': lecture_interventions, 'interventions_courantes': interventions_courantes,
        'parametres_navigation': {k: v for k, v in params.items() if k not in ('prise', 'ecran', 'accompagnement', *dossier.CLES_SOCIALES)}, 'selection_prise': selection_prise, 'commentaires': commentaires, 'commentaire': commentaires[0] if commentaires else None,
        'url_trajectoire': reverse('dossiers:trajectoire', args=[nature, pk]) + '?' + urlencode({**{k:v for k,v in params.items() if k not in ('prise', 'ecran')}, **({'prise':str(prise.pk), 'retour_prise':str(prise.pk)} if prise else {})}),
        'date_sociale': date_sociale,
        'retour_form2': reverse('dossiers:detail', args=[nature, pk]) + '?' + urlencode({**params, 'ecran': 'dossier', 'vue_sociale': 'date' if condition_vue in ('entree', 'fin') else condition_vue}),
        'arrivees_annulees':arrivees_annulees,
        'evolutions': prise.evolutions_prevision.select_related('auteur') if prise and request.user.has_perm('personnes.view_evolutionpriseencharge') else [],
        'objet': objet, 'nature': nature, 'liens': liens, 'liens_uniques': liens_uniques.values(), 'contact_designe': contact_designe,
        'retour_exploration':retour_exploration,'navigation_personne': dossier.pour_personne(pk, params) if nature == 'personne' else {}, 'origine_url': origine_url, 'origine': origine, 'retour': retour, 'navigation_query': urlencode(params), 'recherche': params['q'], 'mode_recherche': params['mode'], 'page_recherche': params['page'], 'origine_sejour': params.get('origine_sejour', ''), 'origine_repas': params.get('origine_repas', ''),
        'periode_actuelle': actuelle, 'information_actuelle': informations_actuelles[0] if informations_actuelles else None,
        'notes_actuelles': notes_actuelles, 'periodes': periodes, 'aujourdhui': jour, 'lecture_hebergement': h, 'lecture_repas': r, 'lecture_lieux': lieux,
        'accords_annules_sans_sejour': [x for x in accords_h if x.annule_le], 'hebergements_prevus': prevus, 'selection_prevision': params['prevision'], 'sejours_dossier': sejours, 'accords_sans_sejour': accords_h, 'accords_repas': accords_r,
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
        suivi.exiger(request.user, 'view_accordhebergement', 'view_sejour')
    elif prestation == 'hebergement':
        suivi.exiger(request.user, 'view_accordhebergement', 'view_sejour')
    else:
        suivi.exiger(request.user, 'view_accordrepas')
    objet = get_object_or_404(Menage if nature == 'menage' else Personne, pk=pk)
    periodes = objet.accompagnements.select_related('menage').prefetch_related('beneficiaires').order_by('-debut', 'pk')
    params = {**parametres(request), **dossier.valeurs_vue(request, nature, pk), **{k: request.GET.get(k, '')[:40] for k in ('sejour', 'repas', 'origine_menage', 'origine_sejour', 'origine_repas')}}
    if params.get('ecran') == 'prise' and suivi_uuid(params.get('prise')):
        periodes = periodes.filter(pk=params['prise'])
    for a in periodes:
        a.url_action = reverse(route, args=[a.pk]) + '?' + urlencode({'contexte_dossier': (dossier.pour_prise if params.get('ecran') == 'prise' else dossier.pour_vue)(request, a, nature, pk, params)['contexte_dossier']})
    if params.get('ecran') == 'prise' and len(periodes) == 1:
        return redirect(periodes[0].url_action)
    return render(request, 'dossiers/choisir.html', {'objet': objet, 'nature': nature, 'periodes': periodes, 'prestation': prestation,
        'retour': reverse('dossiers:detail', args=[nature, pk]) + '?' + urlencode(params)})
